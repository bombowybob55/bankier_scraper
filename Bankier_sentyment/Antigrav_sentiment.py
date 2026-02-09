import asyncio
import re
import random
import time
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin
import pandas as pd
from tabulate import tabulate
import httpx
from selectolax.parser import HTMLParser
from fake_useragent import UserAgent

print("🚀 ANALIZATOR SENTYMENTU WIG20 i mWIG40 (ASYNC/HTTPX)")
print("=" * 120)

# ============================================================================
# SETTINGS & CONFIG
# ============================================================================

# Path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
REPORT_DIR = os.path.join(PROJECT_ROOT, "Reports", "Sentiment")

BANKIER_BASE_URL = "https://www.bankier.pl"
MAX_CONCURRENT_REQUESTS = 5  # Limit concurrency to be polite
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10.0

# Adjusted based on PRD: scrap posts for context - increased to get more replies
MAX_PAGES_PER_THREAD = 5  # Increased from 2 to capture more replies
MAX_POSTS_PER_THREAD = 100  # Increased from 40 to capture more discussion
MAX_THREAD_TEXT_CHARS = 20000  # Increased to allow more context

COMPANY_FILE = os.path.join(PROJECT_ROOT, "spolki_wig20_mwig40.md")
DATE_LIMIT_DAYS = 5
DATE_LIMIT = datetime.now() - timedelta(days=DATE_LIMIT_DAYS)

# ============================================================================
# KROK 1: LOAD COMPANIES
# ============================================================================

def load_companies_from_md(filename):
    """Loads company list from markdown file."""
    companies = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)
        
        for name, url in matches:
            if 'forum' in url and 'bankier' in url:
                companies[name] = url
        
        return companies
    except FileNotFoundError:
        print(f"❌ Plik {filename} nie znaleziony!")
        return {}

# ============================================================================
# KROK 2: ASYNC HTTP HELPERS
# ============================================================================

try:
    ua = UserAgent()
except Exception:
    # Fallback if fake_useragent fails to load data
    class MockUA:
        random = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ua = MockUA()

def get_random_headers():
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl,en-US;q=0.7,en;q=0.3",
        "Referer": "https://www.bankier.pl/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

async def fetch_page(client, url):
    """Fetches a page asynchronously with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            headers = get_random_headers()
            response = await client.get(url, headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 503:
                # Exponential backoff for 503
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
                continue
            else:
                # Other errors
                return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1 + random.random())
            else:
                return None
    return None

# ============================================================================
# KROK 3: PARSING & SCAPING LOGIC (Selectolax)
# ============================================================================

def parse_thread_date(date_str):
    """Parses thread date string."""
    try:
        if not date_str:
            return None
        date_str = date_str.strip()
        now = datetime.now()

        # "dziś 14:30"
        if "dziś" in date_str.lower() or "dzisiaj" in date_str.lower():
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
            if time_match:
                return now.replace(hour=int(time_match.group(1)), minute=int(time_match.group(2)), second=0, microsecond=0)
            return now
        
        # "wczoraj 09:15"
        if "wczoraj" in date_str.lower():
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
            yesterday = now - timedelta(days=1)
            if time_match:
                return yesterday.replace(hour=int(time_match.group(1)), minute=int(time_match.group(2)), second=0, microsecond=0)
            return yesterday
        
        # "2024-01-20 14:00"
        if '-' in date_str and ':' in date_str:
            match = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})', date_str)
            if match:
                return datetime.strptime(f"{match.group(1)} {match.group(2)}:{match.group(3)}", '%Y-%m-%d %H:%M')
        
        return None
    except:
        return None

def extract_posts_from_html(html):
    """Extracts post contents from a thread page."""
    if not html:
        return []
    
    tree = HTMLParser(html)
    # Selectors for post content
    selectors = [
        "div.post-content", "div.postContent", "div.post__content",
        "div.message", "div.post-body"
    ]
    
    texts = []
    for sel in selectors:
        for node in tree.css(sel):
            text = node.text(separator=" ", strip=True)
            if len(text) > 15: # filtering noise
                texts.append(text)
    
    # Deduplicate preserving order
    unique = []
    seen = set()
    for t in texts:
        t_clean = re.sub(r"\s+", " ", t).strip()
        if t_clean and t_clean not in seen:
            seen.add(t_clean)
            unique.append(t_clean)
    
    return unique

async def process_thread(client, thread, sem):
    """
    Fetches posts from a thread including all replies across multiple pages.
    Returns concatenated text of the thread.
    """
    async with sem: # respect global concurrency limit
        url = thread['url']
        initial_html = await fetch_page(client, url)
        
        if not initial_html:
            return thread['title'] # Return at least title if scrape fails
        
        posts = extract_posts_from_html(initial_html)
        
        # Enhanced pagination logic to fetch multiple pages of replies
        if len(posts) < MAX_POSTS_PER_THREAD and MAX_PAGES_PER_THREAD > 1:
            try:
                tree = HTMLParser(initial_html)
                # Look for pagination links
                pagination_links = [
                    urljoin(BANKIER_BASE_URL, node.attributes.get('href'))
                    for node in tree.css("nav.pagination a[href]")
                ]
                
                # Filter and sort pagination links to get sequential pages
                valid_pages = []
                for link in pagination_links:
                    if link and link != url:
                        # Try to extract page number from URL
                        page_match = re.search(r',(\d+)\.html', link)
                        if page_match:
                            page_num = int(page_match.group(1))
                            valid_pages.append((page_num, link))
                
                # Sort by page number and take up to MAX_PAGES_PER_THREAD
                valid_pages.sort(key=lambda x: x[0])
                pages_to_fetch = [link for _, link in valid_pages[:MAX_PAGES_PER_THREAD - 1]]
                
                # Fetch additional pages to get more replies
                for page_url in pages_to_fetch:
                    if len(posts) >= MAX_POSTS_PER_THREAD:
                        break
                    page_html = await fetch_page(client, page_url)
                    if page_html:
                        new_posts = extract_posts_from_html(page_html)
                        posts.extend(new_posts)
                        # Small delay between page fetches to be polite
                        await asyncio.sleep(0.3)
            except Exception as e:
                # Continue with what we have if pagination fails
                pass
        
        combined_text = (thread['title'] + " " + " ".join(posts)).strip()
        return combined_text[:MAX_THREAD_TEXT_CHARS]

async def process_company(client, name, url, sem):
    """
    Scrapes a company's main forum page, finds recent threads,
    and then asynchronously scrapes thread contents.
    """
    async with sem:
        html = await fetch_page(client, url)
    
    if not html:
        return None

    tree = HTMLParser(html)
    threads_to_scrape = []
    
    # Select threads list
    # Usually table.threadsList tr
    rows = tree.css("table.threadsList tbody tr")
    if not rows:
        rows = tree.css("table#threadsList tbody tr")
    
    for row in rows:
        title_node = row.css_first("td.threadTitle a")
        date_node = row.css_first("td.createDate")
        
        if not title_node or not date_node:
            continue
            
        date_str = date_node.text(strip=True)
        thread_date = parse_thread_date(date_str)
        
        if thread_date and thread_date >= DATE_LIMIT:
            title = title_node.text(strip=True)
            href = title_node.attributes.get('href')
            full_url = urljoin(BANKIER_BASE_URL, href)
            
            threads_to_scrape.append({
                'title': title,
                'url': full_url,
                'date': thread_date
            })
            
    if not threads_to_scrape:
        return {
            'Spółka': name,
            'Wątki': 0,
            'Pozyt.': 0, 'Negat.': 0, 'Neutr.': 0,
            'Pozyt.%': "0.0%", 'Negat.%': "0.0%",
            'Sentyment': "➡️ NEUTR"
        }

    # Now fetch details for each valid thread concurrently
    # We create tasks for thread details
    tasks = [process_thread(client, t, sem) for t in threads_to_scrape]
    thread_texts = await asyncio.gather(*tasks)
    
    # Analyze sentiment
    sentiments = [analyze_sentiment(text)[0] for text in thread_texts]
    
    positive_count = sentiments.count('POZYTYWNY')
    negative_count = sentiments.count('NEGATYWNY')
    neutral_count = sentiments.count('NEUTRALNY')
    total = len(sentiments)
    
    pos_pct = (positive_count / total * 100) if total > 0 else 0
    neg_pct = (negative_count / total * 100) if total > 0 else 0
    
    if positive_count > negative_count * 1.5:
        overall = "📈 BULLISH"
    elif negative_count > positive_count * 1.5:
        overall = "📉 BEARISH"
    elif positive_count > negative_count:
        overall = "😊 +POZYT"
    elif negative_count > positive_count:
        overall = "😐 -NEGAT"
    else:
        overall = "➡️ NEUTR"
        
    return {
        'Spółka': name,
        'Wątki': total,
        'Pozyt.': positive_count,
        'Negat.': negative_count,
        'Neutr.': neutral_count,
        'Pozyt.%': f"{pos_pct:.1f}%",
        'Negat.%': f"{neg_pct:.1f}%",
        'Sentyment': overall
    }

# ============================================================================
# KROK 4: IMPROVED SENTIMENT ANALYSIS
# ============================================================================

def analyze_sentiment(text):
    """
    Analyzes sentiment using an improved keyword-based approach.
    """
    if not text:
        return 'NEUTRALNY', 0
        
    text_lower = text.lower()
    
    # Enhanced keywords (Polish)
    positive_keywords = {
        'wzrost', 'zysk', 'dobr', 'super', 'świetn', 'pozytywn', 'sukces', 'rekord',
        'kupuj', 'kupić', 'kupuję', 'hold', 'trzyma', 'rosnąć', 'rośnie', 'górę', 'cel',
        'plus', 'zyskown', 'mocn', 'bullish', 'bull', 'rally', 'boom', 'brać', 'długi',
        'pięknie', 'fajnie', 'solidn', 'zbiera', 'wystrzał', 'wzór', 'rekomenduj',
        'okazja', 'tanio', 'warte', 'silny', 'dynamiczny', 'perspektywy', 'wzorem',
        'rakieta', 'odpał', 'pompa', 'to the moon', 'dokupuję', 'long', 'L'
    }
    
    negative_keywords = {
        'spadek', 'strat', 'kiepsk', 'słab', 'negatywn', 'kryzys', 'problem',
        'sprzeda', 'sprzedaj', 'sprzedam', 'sell', 'ucieka', 'dół', 'minus', 'short',
        'tracę', 'gubi', 'bearish', 'bear', 'crash', 'dno', 'taniec', 'płacz',
        'najgorszy', 'dziadostwo', 'gniot', 'współczuj', 'zawiedziony', 'dramat',
        'zmarnowany', 'zawalisz', 'blada', 'panika', 'zagrożenie', 'ryzyko', 'strach',
        'bankructwo', 'utopiony', 'sypać', 'sypie', 'krach', 'S', 'wała'
    }
    
    # Simple scoring
    pos_score = sum(1 for word in positive_keywords if word in text_lower)
    neg_score = sum(1 for word in negative_keywords if word in text_lower)
    
    # Adjust for relative frequency (optional refinement, here simple count)
    
    if pos_score > neg_score:
        return 'POZYTYWNY', pos_score - neg_score
    elif neg_score > pos_score:
        return 'NEGATYWNY', neg_score - pos_score
    else:
        return 'NEUTRALNY', 0

# ============================================================================
# MAIN
# ============================================================================

async def main():
    start_time = time.time()
    
    companies = load_companies_from_md(COMPANY_FILE)
    if not companies:
        print("❌ Brak spółek do analizy.")
        return

    print(f"✅ Załadowano {len(companies)} spółek.")
    print(f"📅 Analiza od: {DATE_LIMIT.strftime('%Y-%m-%d')}")
    print(f"⏳ Czas na kawę, startuję asynchroniczne pobieranie...")
    
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for name, url in companies.items():
            tasks.append(process_company(client, name, url, sem))
        
        # Run all company tasks
        results = await asyncio.gather(*tasks)
    
    # Filter out Nones
    results = [r for r in results if r]
    
    duration = time.time() - start_time
    print(f"\n✅ Zakończono w {duration:.2f} sekund!")
    
    # ============================================================================
    # REPORTING
    # ============================================================================
    
    if results:
        df = pd.DataFrame(results)
        df_sorted = df.sort_values('Spółka').reset_index(drop=True)
        df_sorted.index = df_sorted.index + 1
        
        print("\n📊 SENTYMENT " + DATE_LIMIT.strftime('%Y-%m-%d') + " - TERAZ\n")
        print(tabulate(df_sorted, headers='keys', tablefmt='grid', showindex=True))
        
        # Stats
        bullish = len([x for x in df['Sentyment'] if 'BULLISH' in x or 'POZYT' in x])
        bearish = len([x for x in df['Sentyment'] if 'BEARISH' in x or 'NEGAT' in x])
        neutral = len([x for x in df['Sentyment'] if 'NEUTR' in x])
        
        print(f"\n📈 PODSUMOWANIE:")
        print(f"  🟢 BULLISH/POZYTYWNE: {bullish}")
        print(f"  🔴 BEARISH/NEGATYWNE: {bearish}")
        print(f"  ⚪ NEUTRALNE: {neutral}")

        # Save to file in Reports/Sentiment directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f'sentiment_report_{timestamp}.txt'
        
        # Ensure directory exists
        os.makedirs(REPORT_DIR, exist_ok=True)
        report_path = os.path.join(REPORT_DIR, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 120 + "\n")
            f.write("RAPORT SENTYMENTU ASYNC (HTTPX/SELECTOLAX)\n")
            f.write("=" * 120 + "\n\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Okres: {DATE_LIMIT_DAYS} dni\n")
            f.write(f"Czas wykonania: {duration:.2f}s\n\n")
            f.write(tabulate(df_sorted, headers='keys', tablefmt='grid', showindex=True))
            f.write("\n\n")
            f.write(f"BULLISH: {bullish} | BEARISH: {bearish} | NEUTRAL: {neutral}\n")
        
        print(f"\n💾 Zapisano raport: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())

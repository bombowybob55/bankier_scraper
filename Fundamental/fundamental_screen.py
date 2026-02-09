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

print("🎯 ANALIZATOR FUNDAMENTALNY WIG20 i mWIG40 (ASYNC/HTTPX)")
print("=" * 120)

# ============================================================================
# SETTINGS & CONFIG
# ============================================================================

# Path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
REPORT_DIR = os.path.join(PROJECT_ROOT, "Reports", "Fundamental")

BANKIER_BASE_URL = "https://www.bankier.pl"
MAX_CONCURRENT_REQUESTS = 5  # Limit concurrency to be polite
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10.0

# Scraping parameters - increased to capture more discussion
MAX_PAGES_PER_THREAD = 5
MAX_POSTS_PER_THREAD = 100
MAX_THREAD_TEXT_CHARS = 20000

COMPANY_FILE = os.path.join(PROJECT_ROOT, "spolki_wig20_mwig40.md")
DATE_LIMIT_DAYS = 14  # Analyze last 2 weeks
DATE_LIMIT = datetime.now() - timedelta(days=DATE_LIMIT_DAYS)

# ============================================================================
# FUNDAMENTAL KEYWORDS WITH CATEGORY WEIGHTS
# ============================================================================

# Each category has a weight that contributes to final score
FUNDAMENTAL_CATEGORIES = {
    'EARNINGS': {
        'weight': 0.25,
        'positive_keywords': [
            'wzrost przychodów', 'wzrost zysku', 'zysk netto', 'rekordowy wynik',
            'wynik finansowy', 'wynik powyżej', 'wzrost EBITDA', 'rentowność',
            'marża', 'zyskowność', 'lepszy wynik', 'przewyższył', 'pobiła rekord',
            'przychody wzrosły', 'zysk wzrósł', 'dodatni wynik', 'zysk operacyjny'
        ],
        'negative_keywords': [
            'spadek przychodów', 'spadek zysków', 'strata netto', 'strata operacyjna',
            'gorszy wynik', 'spadek marży', 'niższa rentowność', 'wynik poniżej',
            'odpis', 'utrata wartości', 'pogorszenie wyniku'
        ]
    },
    'OUTLOOK': {
        'weight': 0.20,
        'positive_keywords': [
            'prognoza wzrostu', 'perspektywy rozwoju', 'optymistyczna prognoza',
            'pozytywne prognozy', 'guidance wzrost', 'cel wzrost', 'szacuje wzrost',
            'przewiduje wzrost', 'spodziewa się wzrostu', 'plan rozwoju',
            'strategia wzrostu', 'ambitne cele', 'pozytywne outlook'
        ],
        'negative_keywords': [
            'obniżona prognoza', 'gorsze perspektywy', 'negatywne prognozy',
            'obniżony guidance', 'niższy cel', 'oczekuje spadku', 'przewiduje spadek',
            'pesymistyczne prognozy', 'gorsze outlook'
        ]
    },
    'STRATEGY': {
        'weight': 0.20,
        'positive_keywords': [
            'nowa strategia', 'realizacja strategii', 'transformacja', 'reorganizacja',
            'ekspansja', 'rozwój', 'innowacja', 'digitalizacja', 'automatyzacja',
            'pozyskał', 'wprowadza', 'launch', 'premiera', 'nowy produkt',
            'nowa usługa', 'zmiany organizacyjne', 'nowy model biznesowy'
        ],
        'negative_keywords': [
            'porażka strategii', 'problem z realizacją', 'opóźnienie projektu',
            'nieudana ekspansja', 'wycofał się', 'zamknął', 'likwidacja',
            'restrukturyzacja przymusowa'
        ]
    },
    'CONTRACTS': {
        'weight': 0.15,
        'positive_keywords': [
            'nowy kontrakt', 'podpisał umowę', 'wygrał przetarg', 'zawarł umowę',
            'pozyskał zlecenie', 'nowe zamówienie', 'największy kontrakt',
            'umowa wieloletnia', 'wartość kontraktu', 'strategiczny kontrakt',
            'kontrakt eksportowy', 'rozszerzenie współpracy', 'przedłużenie umowy'
        ],
        'negative_keywords': [
            'utrata kontraktu', 'rozwiązanie umowy', 'anulowanie kontraktu',
            'przegrał przetarg', 'kontrakt zagrożony', 'spór o kontrakt'
        ]
    },
    'MARKET_POSITION': {
        'weight': 0.10,
        'positive_keywords': [
            'lider rynku', 'wzrost udziału', 'pozycja rynkowa', 'dominujący',
            'przewaga konkurencyjna', 'zwiększył udział', 'silna pozycja',
            'konkurencyjność', 'rozpoznawalność marki', 'brand value'
        ],
        'negative_keywords': [
            'utrata udziału', 'spadek pozycji', 'konkurencja silniejsza',
            'osłabienie pozycji', 'presja konkurencyjna'
        ]
    },
    'RISKS': {
        'weight': 0.10,
        'positive_keywords': [],  # Risks are inherently negative
        'negative_keywords': [
            'problem', 'kryzys', 'zagrożenie', 'ryzyko', 'śledztwo',
            'postępowanie', 'pozew', 'kara', 'sankcja', 'skandal',
            'afera', 'konflikt', 'spór', 'ostrzeżenie', 'rating obniżony',
            'podwyższone ryzyko', 'zagrożony', 'problemy finansowe',
            'problemy operacyjne', 'zawieszenie', 'blokada'
        ]
    }
}

# ============================================================================
# LOAD COMPANIES
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
# ASYNC HTTP HELPERS
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
                return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1 + random.random())
            else:
                return None
    return None

# ============================================================================
# PARSING & SCRAPING LOGIC
# ============================================================================

def parse_thread_date(date_str):
    """Parses thread date string."""
    try:
        if not date_str:
            return None
        date_str = date_str.strip()
        now = datetime.now()

        if "dziś" in date_str.lower() or "dzisiaj" in date_str.lower():
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
            if time_match:
                return now.replace(hour=int(time_match.group(1)), minute=int(time_match.group(2)), second=0, microsecond=0)
            return now
        
        if "wczoraj" in date_str.lower():
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
            yesterday = now - timedelta(days=1)
            if time_match:
                return yesterday.replace(hour=int(time_match.group(1)), minute=int(time_match.group(2)), second=0, microsecond=0)
            return yesterday
        
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
    selectors = [
        "div.post-content", "div.postContent", "div.post__content",
        "div.message", "div.post-body"
    ]
    
    texts = []
    for sel in selectors:
        for node in tree.css(sel):
            text = node.text(separator=" ", strip=True)
            if len(text) > 15:
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
    async with sem:
        url = thread['url']
        initial_html = await fetch_page(client, url)
        
        if not initial_html:
            return thread['title']
        
        posts = extract_posts_from_html(initial_html)
        
        # Enhanced pagination logic to fetch multiple pages of replies
        if len(posts) < MAX_POSTS_PER_THREAD and MAX_PAGES_PER_THREAD > 1:
            try:
                tree = HTMLParser(initial_html)
                pagination_links = [
                    urljoin(BANKIER_BASE_URL, node.attributes.get('href'))
                    for node in tree.css("nav.pagination a[href]")
                ]
                
                # Filter and sort pagination links to get sequential pages
                valid_pages = []
                for link in pagination_links:
                    if link and link != url:
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
                        await asyncio.sleep(0.3)
            except Exception:
                pass
        
        combined_text = (thread['title'] + " " + " ".join(posts)).strip()
        return combined_text[:MAX_THREAD_TEXT_CHARS]

# ============================================================================
# FUNDAMENTAL ANALYSIS
# ============================================================================

def analyze_fundamentals(text):
    """
    Analyzes text for fundamental keywords across all categories.
    Returns dict with category scores and total score.
    """
    if not text:
        return {'total_score': 0, 'categories': {}, 'highlights': []}
    
    text_lower = text.lower()
    category_scores = {}
    highlights = []
    
    for category_name, category_data in FUNDAMENTAL_CATEGORIES.items():
        positive_score = 0
        negative_score = 0
        
        # Count positive keywords
        for keyword in category_data['positive_keywords']:
            if keyword in text_lower:
                positive_score += 1
                if len(highlights) < 3:  # Collect top 3 highlights
                    highlights.append(f"+{category_name}: {keyword}")
        
        # Count negative keywords
        for keyword in category_data['negative_keywords']:
            if keyword in text_lower:
                negative_score += 1
                if len(highlights) < 3:
                    highlights.append(f"-{category_name}: {keyword}")
        
        # Net score for this category
        net_score = positive_score - negative_score
        weighted_score = net_score * category_data['weight']
        
        category_scores[category_name] = {
            'net_score': net_score,
            'weighted_score': weighted_score,
            'positive_count': positive_score,
            'negative_count': negative_score
        }
    
    # Calculate total weighted score
    total_score = sum(cat['weighted_score'] for cat in category_scores.values())
    
    return {
        'total_score': total_score,
        'categories': category_scores,
        'highlights': highlights
    }

def get_fundamental_rating(score):
    """Convert score to fundamental rating."""
    if score >= 3.0:
        return "🚀 VERY BULLISH"
    elif score >= 1.5:
        return "📈 BULLISH"
    elif score >= 0.5:
        return "😊 SLIGHTLY BULLISH"
    elif score > -0.5:
        return "➡️ NEUTRAL"
    elif score > -1.5:
        return "😐 SLIGHTLY BEARISH"
    elif score > -3.0:
        return "📉 BEARISH"
    else:
        return "💥 VERY BEARISH"

async def process_company(client, name, url, sem):
    """
    Scrapes a company's forum, analyzes fundamental discussions,
    and returns fundamental analysis results.
    """
    async with sem:
        html = await fetch_page(client, url)
    
    if not html:
        return None

    tree = HTMLParser(html)
    threads_to_scrape = []
    
    # Select threads list
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
            'Wynik': 0,
            'Rating': "➡️ NEUTRAL",
            'Wątki': 0,
            'Highlights': "Brak dyskusji"
        }

    # Fetch all thread texts concurrently
    tasks = [process_thread(client, t, sem) for t in threads_to_scrape]
    thread_texts = await asyncio.gather(*tasks)
    
    # Combine all thread texts for comprehensive analysis
    combined_text = " ".join(thread_texts)
    
    # Analyze fundamentals
    analysis = analyze_fundamentals(combined_text)
    
    # Prepare highlights summary
    highlights_str = "; ".join(analysis['highlights'][:3]) if analysis['highlights'] else "Brak wykrytych sygnałów"
    
    return {
        'Spółka': name,
        'Wynik': round(analysis['total_score'], 2),
        'Rating': get_fundamental_rating(analysis['total_score']),
        'Wątki': len(threads_to_scrape),
        'Highlights': highlights_str
    }

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
    print(f"⏳ Startuję asynchroniczne pobieranie...\n")
    
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for name, url in companies.items():
            tasks.append(process_company(client, name, url, sem))
        
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
        
        # Sort from most bullish to most bearish
        df_sorted = df.sort_values('Wynik', ascending=False).reset_index(drop=True)
        df_sorted.index = df_sorted.index + 1
        
        print("\n📊 RANKING FUNDAMENTALNY - " + DATE_LIMIT.strftime('%Y-%m-%d') + " - TERAZ\n")
        print(tabulate(df_sorted, headers='keys', tablefmt='grid', showindex=True))
        
        # Stats
        very_bullish = len([x for x in df['Rating'] if 'VERY BULLISH' in x])
        bullish = len([x for x in df['Rating'] if 'BULLISH' in x and 'VERY' not in x and 'SLIGHTLY' not in x])
        slightly_bullish = len([x for x in df['Rating'] if 'SLIGHTLY BULLISH' in x])
        neutral = len([x for x in df['Rating'] if 'NEUTRAL' in x])
        slightly_bearish = len([x for x in df['Rating'] if 'SLIGHTLY BEARISH' in x])
        bearish = len([x for x in df['Rating'] if 'BEARISH' in x and 'VERY' not in x and 'SLIGHTLY' not in x])
        very_bearish = len([x for x in df['Rating'] if 'VERY BEARISH' in x])
        
        print(f"\n📈 PODSUMOWANIE:")
        print(f"  🚀 VERY BULLISH: {very_bullish}")
        print(f"  📈 BULLISH: {bullish}")
        print(f"  😊 SLIGHTLY BULLISH: {slightly_bullish}")
        print(f"  ➡️  NEUTRAL: {neutral}")
        print(f"  😐 SLIGHTLY BEARISH: {slightly_bearish}")
        print(f"  📉 BEARISH: {bearish}")
        print(f"  💥 VERY BEARISH: {very_bearish}")

        # Save to file in Reports/Fundamental directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f'fundamental_ranking_{timestamp}.txt'
        
        # Ensure directory exists
        os.makedirs(REPORT_DIR, exist_ok=True)
        report_path = os.path.join(REPORT_DIR, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 120 + "\n")
            f.write("RANKING FUNDAMENTALNY (ASYNC/HTTPX)\n")
            f.write("=" * 120 + "\n\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Okres: {DATE_LIMIT_DAYS} dni\n")
            f.write(f"Czas wykonania: {duration:.2f}s\n\n")
            f.write(tabulate(df_sorted, headers='keys', tablefmt='grid', showindex=True))
            f.write("\n\n")
            f.write(f"VERY BULLISH: {very_bullish} | BULLISH: {bullish} | SLIGHTLY BULLISH: {slightly_bullish}\n")
            f.write(f"NEUTRAL: {neutral}\n")
            f.write(f"SLIGHTLY BEARISH: {slightly_bearish} | BEARISH: {bearish} | VERY BEARISH: {very_bearish}\n")
        
        print(f"\n💾 Zapisano raport: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())

import pandas as pd
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from tabulate import tabulate
from urllib.parse import urljoin

print("🚀 ANALIZATOR SENTYMENTU WIG20 i mWIG40")
print("=" * 120)

# ============================================================================
# USTAWIENIA (KONTEKST Z WĄTKÓW)
# ============================================================================

BANKIER_BASE_URL = "https://www.bankier.pl"

# Żeby analiza miała szerszy kontekst: wchodzimy do każdego wątku i czytamy posty.
# Limity są po to, aby skrypt nie trwał godzinami na bardzo długich wątkach.
MAX_PAGES_PER_THREAD = 2          # np. 1. strona + ostatnia (jeśli wykryjemy paginację)
MAX_POSTS_PER_THREAD = 40         # ile postów max pobieramy z wątku (łącznie ze stron)
MAX_THREAD_TEXT_CHARS = 6000      # ile znaków max przekazujemy do analizy na wątek
THREAD_PAGE_SLEEP_SEC = 1.0       # krótka pauza po wejściu w wątek/stronę

# ============================================================================
# KROK 1: ZAŁADUJ PLIK MD
# ============================================================================

def load_companies_from_md(filename):
    """Ładuje listę spółek z pliku markdown"""
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

companies = load_companies_from_md('spolki_wig20_mwig40.md')
print(f"\n✅ Załadowano {len(companies)} spółek z pliku markdown\n")

# ============================================================================
# KROK 2: FUNKCJE POMOCNICZE
# ============================================================================

def parse_thread_date(date_str):
    """Parsuje datę wątku"""
    try:
        date_str = date_str.strip()
        
        if "dziś" in date_str.lower() or "dzisiaj" in date_str.lower():
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            return datetime.now()
        
        if "wczoraj" in date_str.lower():
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
            yesterday = datetime.now() - timedelta(days=1)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return yesterday
        
        if '-' in date_str and ':' in date_str:
            match = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})', date_str)
            if match:
                return datetime.strptime(f"{match.group(1)} {match.group(2)}:{match.group(3)}", '%Y-%m-%d %H:%M')
        
        if '.' in date_str and ':' in date_str:
            match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})\s+(\d{1,2}):(\d{2})', date_str)
            if match:
                day, month, year, hour, minute = match.groups()
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
        
        return None
    except:
        return None

def analyze_sentiment(title):
    """Analiza sentymentu na podstawie słów kluczowych"""
    positive_keywords = [
        'wzrost', 'zysk', 'dobr', 'super', 'świetn', 'pozytywn', 'sukces', 'rekord',
        'kupuj', 'kupić', 'kupuję', 'hold', 'trzyma', 'rosnąć', 'rośnie', 'górę', 'cel',
        'plus', 'zyskown', 'mocn', 'bullish', 'bull', 'rally', 'boom', 'brać', 'długi',
        'pięknie', 'fajnie', 'solidn', 'zbiera', 'wystrzał', 'wzór', 'rekomenduj',
        'okazja', 'tanio', 'warte', 'silny', 'dynamiczny', 'perspektywy', 'wzorem'
    ]
    
    negative_keywords = [
        'spadek', 'strat', 'kiepsk', 'słab', 'negatywn', 'kryzys', 'problem',
        'sprzeda', 'sprzedaj', 'sprzedam', 'sell', 'ucieka', 'dół', 'minus', 'short',
        'tracę', 'gubi', 'bearish', 'bear', 'crash', 'dno', 'taniec', 'płacz',
        'najgorszy', 'dziadostwo', 'gniot', 'współczuj', 'zawiedziony', 'dramat',
        'zmarnowany', 'zawalisz', 'blada', 'panika', 'zagrożenie', 'ryzyko', 'strach'
    ]
    
    title_lower = (title or "").lower()
    positive_score = sum(1 for keyword in positive_keywords if keyword in title_lower)
    negative_score = sum(1 for keyword in negative_keywords if keyword in title_lower)
    
    if positive_score > negative_score:
        return 'POZYTYWNY', positive_score - negative_score
    elif negative_score > positive_score:
        return 'NEGATYWNY', negative_score - positive_score
    else:
        return 'NEUTRALNY', 0

def make_absolute_bankier_url(href: str) -> str:
    """Zamienia link względny z forum na absolutny URL."""
    if not href:
        return ""
    return urljoin(BANKIER_BASE_URL, href)

def extract_post_texts_from_thread_soup(thread_soup: BeautifulSoup) -> list[str]:
    """
    Ekstrahuje treści postów (OP + odpowiedzi) z HTML wątku.
    Bankier miewa różne markupy — próbujemy kilku selektorów.
    """
    selectors = [
        "div.post-content",
        "div.postContent",
        "div.post__content",
        "div.message",
        "div.messageContent",
        "div.post-body",
        "div.postBody",
    ]

    texts: list[str] = []
    for sel in selectors:
        for el in thread_soup.select(sel):
            txt = el.get_text(separator=" ", strip=True)
            if not txt:
                continue
            # odfiltruj ultrakrótkie śmieci UI
            if len(txt) < 15:
                continue
            texts.append(txt)

    # deduplikacja z zachowaniem kolejności
    unique: list[str] = []
    seen = set()
    for t in texts:
        key = re.sub(r"\s+", " ", t).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(key)

    return unique

def extract_representative_thread_pages(thread_soup: BeautifulSoup, current_url: str, max_pages: int) -> list[str]:
    """
    Próbuje wykryć paginację i zwrócić listę stron wątku do pobrania.
    Strategia: zawsze bieżąca strona, plus (jeśli się da) "ostatnia"/najwyższy numer strony.
    """
    if max_pages <= 1:
        return [current_url]

    candidates: list[str] = []

    # typowe kontenery paginacji
    for a in thread_soup.select("nav.pagination a[href], ul.pagination a[href], div.pagination a[href]"):
        href = a.get("href")
        if href:
            candidates.append(make_absolute_bankier_url(href))

    # linki rel
    for a in thread_soup.select("a[rel='last'][href], a[rel='next'][href], a[rel='prev'][href]"):
        candidates.append(make_absolute_bankier_url(a.get("href")))

    # dedupe
    uniq: list[str] = []
    for u in candidates:
        if u and u not in uniq:
            uniq.append(u)

    if not uniq:
        return [current_url]

    # wybór stron: obecna + ostatnia + (opcjonalnie) inne
    selected = [current_url]
    last = uniq[-1]
    if last not in selected:
        selected.append(last)

    for u in uniq:
        if len(selected) >= max_pages:
            break
        if u not in selected:
            selected.append(u)

    return selected[:max_pages]

def scrape_thread_posts(driver, thread_url: str) -> list[str]:
    """Wchodzi w wątek i zbiera treści postów (OP + odpowiedzi)."""
    posts: list[str] = []
    if not thread_url:
        return posts

    try:
        driver.get(thread_url)
        time.sleep(THREAD_PAGE_SLEEP_SEC)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        page_urls = extract_representative_thread_pages(soup, thread_url, MAX_PAGES_PER_THREAD)

        for page_url in page_urls:
            if page_url != thread_url:
                driver.get(page_url)
                time.sleep(THREAD_PAGE_SLEEP_SEC)
                soup = BeautifulSoup(driver.page_source, "html.parser")

            for txt in extract_post_texts_from_thread_soup(soup):
                if txt not in posts:
                    posts.append(txt)
                if len(posts) >= MAX_POSTS_PER_THREAD:
                    return posts

        return posts
    except:
        return posts

def scrape_company_sentiment(driver, company_name, url, date_limit):
    """Scrapuje sentyment dla jednej spółki"""
    print(f"  {company_name:25} ...", end=" ", flush=True)
    
    try:
        driver.get(url)
        time.sleep(2)
        
        try:
            cookie_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            )
            cookie_button.click()
            time.sleep(1)
        except:
            pass
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        thread_table = soup.find('table', class_='threadsList')
        if not thread_table:
            thread_table = soup.find('table', id='threadsList')
        
        if not thread_table:
            print("❌ Brak tabeli")
            return None
        
        tbody = thread_table.find('tbody')
        all_tr = tbody.find_all('tr') if tbody else thread_table.find_all('tr')
        
        threads_data = []
        
        for tr in all_tr:
            try:
                title_td = tr.find('td', class_='threadTitle')
                if not title_td:
                    continue
                
                date_td = tr.find('td', class_='createDate')
                if not date_td:
                    continue
                
                date_str = date_td.text.strip()
                thread_date = parse_thread_date(date_str)
                
                if thread_date and thread_date >= date_limit:
                    title_link = title_td.find('a')
                    title = title_link.text.strip() if title_link else title_td.text.strip()
                    thread_href = title_link.get('href') if title_link else ""
                    threads_data.append({'tytul': title, 'url': make_absolute_bankier_url(thread_href), 'data': date_str})
                elif not thread_date:
                    # jeśli data nieparsowalna - bierzemy, ale też zapisujemy URL
                    title_link = title_td.find('a')
                    title = title_link.text.strip() if title_link else title_td.text.strip()
                    thread_href = title_link.get('href') if title_link else ""
                    threads_data.append({'tytul': title, 'url': make_absolute_bankier_url(thread_href), 'data': date_str})
            except:
                continue
        
        if not threads_data:
            print("❌ Brak wątków")
            return None
        
        # Dla szerszego kontekstu: wchodzimy do każdego wątku i analizujemy tekst postów.
        sentiments = []
        for item in threads_data:
            thread_posts = scrape_thread_posts(driver, item.get('url', ''))
            thread_text = (item.get('tytul', '') + " " + " ".join(thread_posts)).strip()
            if len(thread_text) > MAX_THREAD_TEXT_CHARS:
                thread_text = thread_text[:MAX_THREAD_TEXT_CHARS]

            sentiment, score = analyze_sentiment(thread_text)
            sentiments.append(sentiment)
        
        positive_count = sentiments.count('POZYTYWNY')
        negative_count = sentiments.count('NEGATYWNY')
        neutral_count = sentiments.count('NEUTRALNY')
        total = len(sentiments)
        
        positive_pct = (positive_count / total * 100) if total > 0 else 0
        negative_pct = (negative_count / total * 100) if total > 0 else 0
        
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
        
        print(f"✅ {overall}")
        
        return {
            'Spółka': company_name,
            'Wątki': total,
            'Pozyt.': positive_count,
            'Negat.': negative_count,
            'Neutr.': neutral_count,
            'Pozyt.%': f"{positive_pct:.1f}%",
            'Negat.%': f"{negative_pct:.1f}%",
            'Sentyment': overall
        }
        
    except Exception as e:
        print(f"❌")
        return None

# ============================================================================
# KROK 3: KONFIGURACJA SELENIUM
# ============================================================================

print("⚙️ Inicjalizuję przeglądarkę...\n")

chrome_options = Options()
chrome_options.binary_location = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(options=chrome_options)

# ============================================================================
# KROK 4: SCRAPUJ SENTYMENT DLA KAŻDEJ SPÓŁKI
# ============================================================================

date_limit = datetime.now() - timedelta(days=14)
print(f"📅 Analizuję wątki od: {date_limit.strftime('%Y-%m-%d')}")
print(f"📅 Do dnia: {datetime.now().strftime('%Y-%m-%d')}\n")
print("🔄 Przetwarzanie spółek:\n")

results = []
for company_name, url in companies.items():
    result = scrape_company_sentiment(driver, company_name, url, date_limit)
    if result:
        results.append(result)
    time.sleep(1)

driver.quit()

# ============================================================================
# KROK 5: WYŚWIETL TABELĘ W TERMINALU
# ============================================================================

print("\n" + "=" * 120)

if results:
    df = pd.DataFrame(results)
    
    print("\n📊 SENTYMENT SPÓŁEK WIG20 i mWIG40 (ostatnie 14 dni)\n")
    
    df_sorted = df.sort_values('Spółka').reset_index(drop=True)
    df_sorted.index = df_sorted.index + 1
    
    print(tabulate(df_sorted, headers='keys', tablefmt='grid', showindex=True))
    
    # STATYSTYKA
    bullish = len([x for x in df['Sentyment'] if 'BULLISH' in x or 'POZYT' in x])
    bearish = len([x for x in df['Sentyment'] if 'BEARISH' in x or 'NEGAT' in x])
    neutral = len([x for x in df['Sentyment'] if 'NEUTR' in x])
    
    print(f"\n📈 PODSUMOWANIE:")
    print(f"  🟢 BULLISH/POZYTYWNE: {bullish}")
    print(f"  🔴 BEARISH/NEGATYWNE: {bearish}")
    print(f"  ⚪ NEUTRALNE: {neutral}")
    
    # ============================================================================
    # KROK 6: ZAPISZ RAPORT TXT
    # ============================================================================
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f'sentiment_report_wig20_mwig40_{timestamp}.txt'
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write("=" * 120 + "\n")
        f.write("RAPORT SENTYMENTU WIG20 i mWIG40\n")
        f.write("=" * 120 + "\n\n")
        f.write(f"Data raportu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Okres analizy: ostatnie 14 dni\n")
        f.write(f"Liczba analizowanych spółek: {len(results)}\n")
        f.write(f"Liczba przeanalizowanych wątków: {df['Wątki'].sum()}\n\n")
        
        f.write("=" * 120 + "\n")
        f.write("TABELA WYNIKÓW\n")
        f.write("=" * 120 + "\n\n")
        f.write(tabulate(df_sorted, headers='keys', tablefmt='grid', showindex=True))
        
        f.write("\n\n" + "=" * 120 + "\n")
        f.write("PODSUMOWANIE STATYSTYK\n")
        f.write("=" * 120 + "\n\n")
        f.write(f"Spółek z sentmentem BULLISH/POZYTYWNYM: {bullish}\n")
        f.write(f"Spółek z sentmentem BEARISH/NEGATYWNYM: {bearish}\n")
        f.write(f"Spółek z sentmentem NEUTRALNYM: {neutral}\n\n")
        
        f.write("=" * 120 + "\n")
        f.write("TOP 5 NAJPOZYTYWNIEJSZYCH SPÓŁEK\n")
        f.write("=" * 120 + "\n\n")
        
        top_positive = df.nlargest(5, 'Pozyt.')
        for idx, row in top_positive.iterrows():
            f.write(f"{row['Spółka']:30} | Pozyt: {row['Pozyt.']} | Negat: {row['Negat.']} | {row['Sentyment']}\n")

        f.write("\n" + "=" * 120 + "\n")
        f.write("TOP 5 NAJNEGATYWNIEJSZYCH SPÓŁEK\n")
        f.write("=" * 120 + "\n\n")

        top_negative = df.nlargest(5, 'Negat.')
        for idx, row in top_negative.iterrows():
            f.write(f"{row['Spółka']:30} | Negat: {row['Negat.']} | Pozyt: {row['Pozyt.']} | {row['Sentyment']}\n")

        f.write("\n" + "=" * 120 + "\n")
        f.write("KONIEC RAPORTU\n")
        f.write("=" * 120 + "\n")

    print(f"\n💾 Zapisano raport: {report_filename}")
else:
    print("❌ Brak wyników do wyświetlenia.")

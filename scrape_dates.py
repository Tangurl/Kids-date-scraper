import asyncio
import csv
import re
import sys
import time
import aiohttp
from bs4 import BeautifulSoup

# Thai month name to month number (1-12)
THAI_MONTHS = {
    'มกราคม': 1, 'ม.ค.': 1,
    'กุมภาพันธ์': 2, 'ก.พ.': 2,
    'มีนาคม': 3, 'มี.ค.': 3,
    'เมษายน': 4, 'เม.ย.': 4,
    'พฤษภาคม': 5, 'พ.ค.': 5,
    'มิถุนายน': 6, 'มิ.ย.': 6,
    'กรกฎาคม': 7, 'ก.ค.': 7,
    'สิงหาคม': 8, 'ส.ค.': 8,
    'กันยายน': 9, 'ก.ย.': 9,
    'ตุลาคม': 10, 'ต.ค.': 10,
    'พฤศจิกายน': 11, 'พ.ย.': 11,
    'ธันวาคม': 12, 'ธ.ค.': 12
}

def parse_thai_date(text: str) -> str:
    """
    Parses a Thai date string (e.g., 'โพสต์เมื่อวันที่ : 1 มีนาคม 2568' or '21 กรกฎาคม 2565')
    and returns a standardized ISO date format (YYYY-MM-DD) suitable for sorting in Excel/Spreadsheets.
    Converts B.E. (พ.ศ.) years to A.D. (ค.ศ.) years automatically.
    """
    if not text:
        return ''
    
    match = re.search(r'(\d{1,2})\s+([^\s\d]+)\s+(\d{4})', text)
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        year = int(match.group(3))
        
        month = THAI_MONTHS.get(month_str)
        if month:
            # Convert B.E. (พ.ศ.) to A.D. (ค.ศ.)
            if year > 2400:
                year -= 543
            return f'{year:04d}-{month:02d}-{day:02d}'
            
    return text.strip()

async def fetch_date(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, idx: int, path: str, retries: int = 2) -> tuple:
    """
    Fetches article URL, streams chunk-by-chunk and stops as soon as date is loaded (~1MB cutoff),
    scrapes the date from .content-body > span:nth-child(3), and formats as YYYY-MM-DD.
    Non-article URLs return an empty string.
    """
    # Only /contents/ paths have dates - skip all other paths instantly
    if not path or path == '/' or not path.startswith('/contents/'):
        return idx, ''
        
    url = f"https://kids.thaipbs.or.th{path}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    timeout = aiohttp.ClientTimeout(total=12, connect=5)
    
    async with semaphore:
        for attempt in range(retries):
            try:
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = b''
                        # Stream response and break early once date string is downloaded
                        async for chunk in resp.content.iter_chunked(64000):
                            data += chunk
                            if len(data) > 300000:
                                html_partial = data.decode('utf-8', errors='ignore')
                                if 'โพสต์เมื่อวันที่' in html_partial or len(data) > 1500000:
                                    break
                                    
                        html = data.decode('utf-8', errors='ignore')
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Primary selector: .content-body > span:nth-child(3)
                        el = soup.select_one('.content-body > span:nth-child(3)')
                        raw_text = el.get_text(strip=True) if el else ''
                        
                        # Fallback 1: Any span inside .content-body containing date keywords
                        if not raw_text:
                            for span in soup.select('.content-body span'):
                                t = span.get_text(strip=True)
                                if 'โพสต์' in t or 'วันที่' in t:
                                    raw_text = t
                                    break
                        
                        # Fallback 2: Regex search across partial HTML text for 'โพสต์เมื่อวันที่ : <date>'
                        if not raw_text:
                            m = re.search(r'โพสต์เมื่อวันที่\s*:\s*([^<\n]+)', html)
                            if m:
                                raw_text = m.group(1).strip()
                                
                        parsed = parse_thai_date(raw_text)
                        if parsed:
                            return idx, parsed
            except Exception:
                await asyncio.sleep(0.3)
    return idx, ''

def save_csv(csv_path: str, header: list, data_rows: list, results_map: dict):
    updated_rows = [header]
    for idx, row in enumerate(data_rows):
        date_val = results_map.get(idx, '')
        new_row = list(row)
        while len(new_row) < 4:
            new_row.append('')
        if len(new_row) < 5:
            new_row.append(date_val)
        else:
            new_row[4] = date_val
        updated_rows.append(new_row)

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(updated_rows)

async def process_csv(csv_path: str):
    start_time = time.time()
    print(f"Reading CSV from: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
    if not rows:
        print("CSV is empty!")
        return

    header = list(rows[0])
    if len(header) < 5:
        header.append('Date')
    else:
        header[4] = 'Date'
        
    data_rows = rows[1:]
    total = len(data_rows)
    article_count = sum(1 for r in data_rows if r[1].startswith('/contents/'))
    print(f"Total CSV rows: {total} (Article URLs to scrape: {article_count})")
    
    # Load any previously saved dates to resume seamlessly
    results_map = {}
    for idx, r in enumerate(data_rows):
        if len(r) > 4 and r[4]:
            results_map[idx] = r[4]

    # Scrape 10 URLs at once in parallel
    semaphore = asyncio.Semaphore(10)
    connector = aiohttp.TCPConnector(limit=15, ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Only fetch rows that don't already have dates
        tasks = [fetch_date(session, semaphore, idx, row[1]) for idx, row in enumerate(data_rows) if idx not in results_map]
        
        completed = 0
        total_tasks = len(tasks)
        print(f"Remaining article URLs to scrape: {total_tasks}")
        
        for future in asyncio.as_completed(tasks):
            idx, date_val = await future
            results_map[idx] = date_val
            completed += 1
            
            # Save progress incrementally every 15 completed requests
            if completed % 15 == 0 or completed == total_tasks:
                save_csv(csv_path, header, data_rows, results_map)
                elapsed = round(time.time() - start_time, 1)
                extracted_so_far = sum(1 for v in results_map.values() if v)
                print(f"Progress: {completed}/{total_tasks} scraped ({elapsed}s elapsed) | Total dates extracted: {extracted_so_far}/{article_count}")

    save_csv(csv_path, header, data_rows, results_map)
    total_elapsed = round(time.time() - start_time, 1)
    extracted_final = sum(1 for v in results_map.values() if v)
    print(f"\nFinished scraping in {total_elapsed}s!")
    print(f"Successfully updated CSV: {csv_path}")
    print(f"Total articles with extracted dates: {extracted_final}/{article_count}")

if __name__ == '__main__':
    csv_file = 'Thai PBS All Stats_Thai PBS Kids _ตาราง (1).csv'
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    asyncio.run(process_csv(csv_file))

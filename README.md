# Thai PBS Kids Monthly Stats - Date Scraper

An asynchronous Python tool designed to enrich Thai PBS Kids (`kids.thaipbs.or.th`) analytics reports with article publication dates. It automatically extracts Thai dates from article pages, converts Buddhist Era (พ.ศ.) years to Common Era (ค.ศ.), formats them into standardized `YYYY-MM-DD` ISO dates, and updates the CSV for seamless sorting and filtering in Excel or Google Sheets.

---

## ✨ Features

- **High-Performance Asynchronous Scraping**: Utilizes `aiohttp` and `asyncio` with semaphore throttling (10 parallel requests) for fast, reliable extraction.
- **Early-Stop Streaming**: Reads network response chunks iteratively and aborts download as soon as the article date header is found (~300KB cutoff), saving bandwidth and processing time.
- **Thai Date Parsing & B.E. to A.D. Conversion**: Converts Thai textual dates (e.g., `1 มีนาคม 2568` or `โพสต์เมื่อวันที่ : 21 กรกฎาคม 2565`) to standard `YYYY-MM-DD` dates (`2025-03-01`, `2022-07-21`).
- **Targeted Path Filtering**: Specifically targets article URLs (`/contents/...`) and skips static/non-content routes (`/`, `/programs`, `/activity`) instantly.
- **Incremental Autosave & Resumable**: Progress is saved to the CSV incrementally every 15 completed requests. If interrupted, re-running the script will pick up where it left off without re-fetching already extracted dates.
- **Excel & Spreadsheet Friendly**: Uses UTF-8 with BOM (`utf-8-sig`) encoding to ensure Thai characters render cleanly without garbled text in Microsoft Excel.

---

## 📁 Repository Structure

```text
ThaiPBSKidMonthly/
├── .gitignore                                           # Git ignore rules for Python, OS, & IDEs
├── README.md                                            # Project documentation
├── requirements.txt                                     # Python dependencies
├── scrape_dates.py                                      # Main scraper and CSV processing script
├── Thai PBS All Stats_Thai PBS Kids _ตาราง_OG.csv       # Original exported raw stats CSV
└── Thai PBS All Stats_Thai PBS Kids _ตาราง (1).csv      # Processed CSV with added Date column
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.8 or higher installed on your system.

### 2. Environment Setup

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Usage

### Run with Default CSV

By default, the script will process `Thai PBS All Stats_Thai PBS Kids _ตาราง (1).csv`:

```bash
python scrape_dates.py
```

### Run with a Custom CSV

You can pass a specific CSV file path as an argument:

```bash
python scrape_dates.py "path/to/your_stats_file.csv"
```

---

## 📊 CSV Format

### Input Schema
| Name | Page path and screen class | Views | Bounce Rate |
| :--- | :--- | :--- | :--- |
| Website ThaiPBS Kids / kids.thaipbs.or.th | `/` | ... | ... |
| "กาลเทศะ" วินัยทางสังคมที่เด็กยุคใหม่ต้องมี | `/contents/67adbd54d5756b9c760fa46b` | ... | ... |

### Output Schema (Enriched)
| Name | Page path and screen class | Views | Bounce Rate | Date |
| :--- | :--- | :--- | :--- | :--- |
| Website ThaiPBS Kids / kids.thaipbs.or.th | `/` | ... | ... | |
| "กาลเทศะ" วินัยทางสังคมที่เด็กยุคใหม่ต้องมี | `/contents/67adbd54d5756b9c760fa46b` | ... | ... | **2025-03-01** |

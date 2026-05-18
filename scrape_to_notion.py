import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_VERSION = "2022-06-28"

HEADERS_BS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def scrape_article(url: str) -> dict:
    session = requests.Session()
    session.get("https://www.viriyah.co.th/en/", headers=HEADERS_BS, timeout=15)
    response = session.get(url, headers=HEADERS_BS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    date_tag = soup.find(class_="date")
    date_str = date_tag.get_text(strip=True) if date_tag else None

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    content_area = soup.find(class_="detail") or soup.find("article") or soup.find("main")
    paragraphs = content_area.find_all("p") if content_area else soup.find_all("p")
    body = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return {"url": url, "date": date_str, "title": title, "body": body}


def parse_notion_date(raw: str | None) -> str | None:
    """Try to parse a Thai/English date string to ISO 8601 (YYYY-MM-DD)."""
    if not raw:
        return None
    from datetime import datetime

    thai_months = {
        "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
        "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
        "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
    }
    en_formats = ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%Y-%m-%d"]

    for thai_month, month_num in thai_months.items():
        if thai_month in raw:
            parts = raw.replace(thai_month, "").split()
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                day = int(parts[0])
                year_be = int(parts[-1])
                year_ce = year_be - 543
                return f"{year_ce:04d}-{month_num:02d}-{day:02d}"

    for fmt in en_formats:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def _rich_text_chunks(text: str) -> list[dict]:
    """Split text into 2000-char chunks (Notion rich_text limit per element)."""
    chunks = []
    for i in range(0, len(text), 2000):
        chunks.append({"type": "text", "text": {"content": text[i : i + 2000]}})
    return chunks


def save_to_notion(article: dict) -> str:
    iso_date = parse_notion_date(article["date"])

    properties: dict = {
        "Title": {"title": [{"type": "text", "text": {"content": article["title"]}}]},
        "Source URL": {"url": article["url"]},
        "Body": {"rich_text": _rich_text_chunks(article["body"][:2000])},
    }
    if iso_date:
        properties["Date"] = {"date": {"start": iso_date}}

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
    }

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()["url"]


def main():
    url = "https://www.viriyah.co.th/en/news/pr/news/66-1/"
    print(f"Scraping: {url}")
    article = scrape_article(url)
    print(f"Title : {article['title']}")
    print(f"Date  : {article['date']}")
    print(f"Body  : {article['body'][:200]}...")

    print("\nSaving to Notion...")
    notion_url = save_to_notion(article)
    print(f"Saved: {notion_url}")


if __name__ == "__main__":
    main()

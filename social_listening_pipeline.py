"""
Social Listening Pipeline
Scrape (BeautifulSoup) → Analyze (Groq LLM) → Store (Notion)
"""

import json
import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

HEADERS_BS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


#Scrape

def scrape_article(url: str) -> dict:
    # Viriyah sets a cookie gate on first visit — warm up with homepage first
    session = requests.Session()
    session.get("https://www.viriyah.co.th/en/", headers=HEADERS_BS, timeout=15)
    response = session.get(url, headers=HEADERS_BS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    date_tag = soup.find(class_="date")
    date = date_tag.get_text(strip=True) if date_tag else "N/A"

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    content_area = soup.find(class_="detail") or soup.find("article") or soup.find("main")
    paragraphs = content_area.find_all("p") if content_area else soup.find_all("p")
    body = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return {"url": url, "date": date, "title": title, "body": body}


#Analyze with Groq LLM

def analyze_with_groq(article: dict) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY)

    prompt = f"""Analyze the following news article and return a JSON object with exactly these fields:
- "sentiment": one of "positive", "negative", or "neutral"
- "score": a float from -1.0 (very negative) to 1.0 (very positive)
- "topics": a list of key topics mentioned (max 5)
- "summary": one sentence summary in English
- "language": "th" if Thai, "en" if English

Article title: {article['title']}
Article body:
{article['body'][:3000]}

Return only valid JSON. No extra text or markdown."""

    response = llm.invoke([HumanMessage(content=prompt)])

    raw = response.content.strip()
    # Strip markdown code fences if the model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


#Save to Notion 

def _parse_date(raw: str | None) -> str | None:
    if not raw or raw == "N/A":
        return None
    from datetime import datetime

    thai_months = {
        "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
        "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
        "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
    }
    for thai_month, month_num in thai_months.items():
        if thai_month in raw:
            parts = [p.strip() for p in raw.replace(thai_month, "").split() if p.strip()]
            if len(parts) >= 2:
                day, year_ce = int(parts[0]), int(parts[-1]) - 543
                return f"{year_ce:04d}-{month_num:02d}-{day:02d}"

    for fmt in ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _rich_text(text: str) -> list[dict]:
    chunks = []
    for i in range(0, min(len(text), 2000), 2000):
        chunks.append({"type": "text", "text": {"content": text[i : i + 2000]}})
    return chunks or [{"type": "text", "text": {"content": text[:2000]}}]


def save_to_notion(article: dict, analysis: dict) -> str:
    analysis_block = (
        f"--- AI Analysis (Groq / Llama 3.3 70B) ---\n"
        f"Sentiment : {analysis.get('sentiment', 'N/A')} (score: {analysis.get('score', 'N/A')})\n"
        f"Topics    : {', '.join(analysis.get('topics', []))}\n"
        f"Language  : {analysis.get('language', 'N/A')}\n"
        f"Summary   : {analysis.get('summary', 'N/A')}\n"
    )

    full_body = f"{analysis_block}\n\n--- Original Article ---\n{article['body']}"

    properties: dict = {
        "Title": {"title": [{"type": "text", "text": {"content": article["title"]}}]},
        "Source URL": {"url": article["url"]},
        "Body": {"rich_text": _rich_text(full_body[:2000])},
    }

    iso_date = _parse_date(article["date"])
    if iso_date:
        properties["Date"] = {"date": {"start": iso_date}}

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
    }

    resp = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()["url"]


# ── Main ──────────────────────────────────────────────────────────────────────

def run_pipeline(url: str):
    print(f"\n[1/3] Scraping: {url}")
    article = scrape_article(url)
    print(f"      Title : {article['title']}")
    print(f"      Date  : {article['date']}")
    print(f"      Body  : {article['body'][:120]}...")

    print("\n[2/3] Analyzing with Groq (Llama 3.3 70B)...")
    analysis = analyze_with_groq(article)
    print(f"      Sentiment : {analysis.get('sentiment')} ({analysis.get('score')})")
    print(f"      Topics    : {', '.join(analysis.get('topics', []))}")
    print(f"      Summary   : {analysis.get('summary')}")

    print("\n[3/3] Saving to Notion...")
    notion_url = save_to_notion(article, analysis)
    print(f"      Saved: {notion_url}")

    return article, analysis


if __name__ == "__main__":
    run_pipeline("https://www.viriyah.co.th/en/news/pr/66-37/")

"""
Social Listening Pipeline — Gemini Edition
Scrape (BeautifulSoup) → Analyze (Gemini API) → Store (Notion)

Same pipeline structure as social_listening_pipeline.py but uses google-genai
directly (same pattern as kam-backend) instead of Groq/LangChain.
"""

import base64
import json
import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.oauth2 import service_account

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GEMINI_MODEL = "gemini-2.5-flash"

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "esg-report-469503")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Decode service account JSON from env — same base64 blob the backend uses for GCS
_sa_info = json.loads(base64.b64decode(os.getenv("GCP_SERVICE_ACCOUNT_JSON_BASE64")))
_credentials = service_account.Credentials.from_service_account_info(
    _sa_info,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

_gemini_client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT_ID,
    location=GOOGLE_CLOUD_LOCATION,
    credentials=_credentials,
)

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


# ── Scrape ────────────────────────────────────────────────────────────────────

def scrape_page(url: str) -> dict:
    """
    Generic scraper for insurance news/article pages.
    Warms up on the site homepage first to bypass cookie gates (common on Thai sites).
    """
    parsed = urlparse(url)
    homepage = f"{parsed.scheme}://{parsed.netloc}"

    session = requests.Session()
    # Cookie-gate warmup — must hit homepage before article pages
    session.get(homepage, headers=HEADERS_BS, timeout=20)
    response = session.get(url, headers=HEADERS_BS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script/style noise
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Date — try common selectors across sites
    date = "N/A"
    for selector in [
        ".date", ".published", ".post-date", ".article-date",
        "time", "[class*='date']", "[class*='time']", ".news-date",
    ]:
        tag = soup.select_one(selector)
        if tag:
            date = tag.get_text(strip=True)
            break

    # Title
    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else url

    # Body — try article containers before falling back to all <p>
    content_area = (
        soup.find(class_="detail")
        or soup.find(class_="article-content")
        or soup.find(class_="article-body")
        or soup.find(class_="content-body")
        or soup.find(class_="entry-content")
        or soup.find(class_="news-content")
        or soup.find("article")
        or soup.find("main")
    )
    paragraphs = content_area.find_all("p") if content_area else soup.find_all("p")
    body = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    if not body:
        # Last resort: grab all visible text from body
        body = soup.get_text(separator="\n", strip=True)[:5000]

    return {"url": url, "date": date, "title": title, "body": body}


# ── Analyze with Gemini ───────────────────────────────────────────────────────

def analyze_with_gemini(article: dict) -> dict:
    """
    Calls Gemini via Vertex AI using the same pattern as kam-backend tasks.
    Uses the global _gemini_client authenticated with the service account.
    """
    prompt = f"""Analyze the following insurance company web page content and return a JSON object with exactly these fields:
- "sentiment": one of "positive", "negative", or "neutral"
- "score": a float from -1.0 (very negative) to 1.0 (very positive)
- "topics": a list of key topics mentioned (max 5 strings)
- "summary": one sentence summary in English
- "language": "th" if Thai, "en" if English

Page title: {article['title']}
Page content:
{article['body'][:3000]}

Return STRICT JSON only. No extra text or markdown."""

    response = _gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    raw = (response.text or "").strip()

    # Log token usage (same pattern as backend)
    usage = getattr(response, "usage_metadata", None)
    if usage:
        print(f"      [Gemini tokens] prompt={getattr(usage, 'prompt_token_count', '?')} "
              f"output={getattr(usage, 'candidates_token_count', '?')} "
              f"total={getattr(usage, 'total_token_count', '?')}")

    # Strip markdown code fences (same cleanup as backend)
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()

    return json.loads(raw)


# ── Notion helpers ────────────────────────────────────────────────────────────

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
        chunks.append({"type": "text", "text": {"content": text[i: i + 2000]}})
    return chunks or [{"type": "text", "text": {"content": text[:2000]}}]


def save_to_notion(article: dict, analysis: dict) -> str:
    analysis_block = (
        f"--- AI Analysis (Gemini / {GEMINI_MODEL}) ---\n"
        f"Sentiment : {analysis.get('sentiment', 'N/A')} (score: {analysis.get('score', 'N/A')})\n"
        f"Topics    : {', '.join(analysis.get('topics', []))}\n"
        f"Language  : {analysis.get('language', 'N/A')}\n"
        f"Summary   : {analysis.get('summary', 'N/A')}\n"
    )

    full_body = f"{analysis_block}\n\n--- Original Content ---\n{article['body']}"

    properties: dict = {
        "Title": {"title": [{"type": "text", "text": {"content": article["title"][:2000]}}]},
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


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(url: str):
    print(f"\n{'='*60}")
    print(f"[1/3] Scraping: {url}")
    article = scrape_page(url)
    print(f"      Title : {article['title'][:80]}")
    print(f"      Date  : {article['date']}")
    print(f"      Body  : {article['body'][:120]}...")

    print(f"\n[2/3] Analyzing with Gemini ({GEMINI_MODEL})...")
    analysis = analyze_with_gemini(article)
    print(f"      Sentiment : {analysis.get('sentiment')} ({analysis.get('score')})")
    print(f"      Topics    : {', '.join(analysis.get('topics', []))}")
    print(f"      Summary   : {analysis.get('summary')}")

    print("\n[3/3] Saving to Notion...")
    notion_url = save_to_notion(article, analysis)
    print(f"      Saved: {notion_url}")

    return article, analysis


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TARGET_SITES = [
        "https://www.axa.co.th/en/support/about-axa-thailand",
        "https://www.thailife.com/ThaiLifeInsuranceMedicare",
        "https://www.aia.co.th/en/health-wellness/vitality/campaigns/virgin-active-mar26",
    ]

    for url in TARGET_SITES:
        try:
            run_pipeline(url)
        except Exception as e:
            print(f"\n[ERROR] Failed for {url}: {e}")

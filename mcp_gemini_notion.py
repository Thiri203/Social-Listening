"""
Social Listening — Gemini Only
Gemini fetches the URL, reads it, and analyzes it — no BeautifulSoup.
Pipeline: Gemini (scrape + analyze) → Notion
"""

import base64
import json
import os
import re

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.oauth2 import service_account

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GEMINI_MODEL = "gemini-2.5-flash"

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "esg-report-469503")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

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

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


# ── Gemini: fetch + analyze ───────────────────────────────────────────────────

def fetch_and_analyze(url: str) -> dict:
    """
    Gemini fetches the URL via url_context tool and returns structured analysis.
    No BeautifulSoup — Gemini does all the reading and understanding.
    """
    prompt = f"""You are a web scraper and content analyst.

Fetch and read the content at this URL: {url}

Extract and analyze the page, then return a JSON object with exactly these fields:
- "title": the main page or article title
- "date": publication date in YYYY-MM-DD format, or null if not found
- "body": main content text, max 400 words
- "sentiment": one of "positive", "negative", "neutral"
- "score": float from -1.0 (very negative) to 1.0 (very positive)
- "topics": list of up to 5 key topics as strings
- "summary": one sentence summary in English
- "language": "th" if Thai, "en" if English

Return STRICT JSON only. No markdown, no extra text."""

    response = _gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(url_context=types.UrlContext())],
        ),
    )

    # Log token usage
    usage = getattr(response, "usage_metadata", None)
    if usage:
        print(f"      [tokens] prompt={getattr(usage, 'prompt_token_count', '?')} "
              f"output={getattr(usage, 'candidates_token_count', '?')}")

    # Collect text from all parts (tool responses can split across parts)
    raw = ""
    try:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                raw += part.text
    except (IndexError, AttributeError):
        raw = response.text or ""

    raw = raw.strip()
    if not raw:
        raise ValueError("Gemini returned empty response — page may be inaccessible")

    print(f"      [raw] {raw[:120]}...")

    # Strip markdown fences if model wraps JSON
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()

    return json.loads(raw)


# ── Notion ────────────────────────────────────────────────────────────────────

def _rich_text(text: str) -> list[dict]:
    return [{"type": "text", "text": {"content": text[:2000]}}]


def save_to_notion(url: str, data: dict) -> str:
    analysis_block = (
        f"--- AI Analysis (Gemini / {GEMINI_MODEL}) ---\n"
        f"Sentiment : {data.get('sentiment', 'N/A')} (score: {data.get('score', 'N/A')})\n"
        f"Topics    : {', '.join(data.get('topics', []))}\n"
        f"Language  : {data.get('language', 'N/A')}\n"
        f"Summary   : {data.get('summary', 'N/A')}\n"
        f"\n--- Content ---\n{data.get('body', '')}"
    )

    properties: dict = {
        "Title": {"title": [{"type": "text", "text": {"content": data.get("title", url)[:2000]}}]},
        "Source URL": {"url": url},
        "Body": {"rich_text": _rich_text(analysis_block)},
    }

    if data.get("date"):
        properties["Date"] = {"date": {"start": data["date"]}}

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": NOTION_DATABASE_ID}, "properties": properties},
    )
    resp.raise_for_status()
    return resp.json()["url"]


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(url: str):
    print(f"\n{'='*60}")
    print(f"[1/2] Gemini fetching + analyzing: {url}")

    data = fetch_and_analyze(url)

    print(f"      Title     : {data.get('title', 'N/A')[:80]}")
    print(f"      Sentiment : {data.get('sentiment')} ({data.get('score')})")
    print(f"      Topics    : {', '.join(data.get('topics', []))}")
    print(f"      Summary   : {data.get('summary')}")

    print("\n[2/2] Saving to Notion...")
    notion_url = save_to_notion(url, data)
    print(f"      Saved: {notion_url}")

    return data


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TARGET_SITES = [
        "https://www.axa.co.th/en",
        "https://www.thailife.com/?lang=en",
        "https://www.aia.co.th/en/health-wellness/vitality",
    ]

    for url in TARGET_SITES:
        try:
            run_pipeline(url)
        except Exception as e:
            print(f"\n[ERROR] {url}: {e}")

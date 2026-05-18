import os
import sys
import json
import requests
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

URL = "https://www.viriyah.co.th/en/news/pr/66-37/"

GRAPH_CONFIG = {
    "llm": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": "groq/llama-3.3-70b-versatile",
    },
    "verbose": True,
    "headless": True,
}

PROMPT = (
    "Extract the following fields from this news article and return as JSON:\n"
    "- title: article headline (preserve English text)\n"
    "- date: publication date\n"
    "- body: full article body text (preserve English text)\n"
    "- source_url: the page URL"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str) -> str:
    # Visit homepage first to receive the cookie gate cookie, then fetch target page
    session = requests.Session()
    session.get("https://www.viriyah.co.th/", headers=HEADERS, timeout=15)
    response = session.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def main():
    print(f"Scraping with ScrapeGraphAI + Groq (Llama 3.3): {URL}")
    print("=" * 60)

    print("Fetching HTML (handling cookie gate)...")
    html = fetch_html(URL)
    print(f"Fetched {len(html):,} characters of HTML")

    scraper = SmartScraperGraph(
        prompt=PROMPT,
        source=html,
        config=GRAPH_CONFIG,
    )

    result = scraper.run()

    output_path = "output_english_scrapegraphai.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n--- Extracted Result ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nOutput saved to {output_path}")


if __name__ == "__main__":
    main()

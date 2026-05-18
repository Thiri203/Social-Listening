import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv()

API_KEY = os.getenv("FIRECRAWL_API_KEY")
URL = "https://www.viriyah.co.th/en/news/pr/news/66-2/"


def main():
    app = FirecrawlApp(api_key=API_KEY)

    print(f"Scraping: {URL}")
    print("=" * 60)

    result = app.scrape(URL, formats=["markdown"], headers={"Cookie": "viriyah_landing=1"})

    metadata = result.metadata
    print(f"Title  : {metadata.title}")
    print(f"URL    : {metadata.url}")
    print(f"\n--- Content (Markdown) ---\n{result.markdown}")


if __name__ == "__main__":
    main()

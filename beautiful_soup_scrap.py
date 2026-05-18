import requests
from bs4 import BeautifulSoup


def scrape_news_article(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    # The site serves a cookie-gate landing page on the first visit.
    # A session preserves the cookie so the second request gets real content.
    session = requests.Session()
    session.get("https://www.viriyah.co.th/en/", headers=headers, timeout=15)

    response = session.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Date
    date_tag = soup.find(class_="date")
    date = date_tag.get_text(strip=True) if date_tag else "N/A"

    # Title
    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else "N/A"

    # Body paragraphs inside the article content area
    content_area = soup.find(class_="detail") or soup.find("article") or soup.find("main")
    if content_area:
        paragraphs = content_area.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    body = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return {"url": url, "date": date, "title": title, "body": body}


def main():
    url = "https://www.viriyah.co.th/en/news/pr/66-37/"
    print(f"Scraping: {url}")
    print("=" * 60)

    article = scrape_news_article(url)

    print(f"Date  : {article['date']}")
    print(f"Title : {article['title']}")
    print(f"\n--- Body ---\n{article['body']}")


if __name__ == "__main__":
    main()

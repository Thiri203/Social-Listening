# Social Listening POC

Proof-of-concept for scraping and monitoring news articles from Thai insurance company websites, built during the AIBrainLab internship.

**Target site:** [Viriyah Insurance](https://www.viriyah.co.th/en/) — one of Thailand's largest non-life insurance companies.

---

## Background

The goal was to evaluate tools and approaches for **Social Listening** — automatically collecting, extracting, and storing public news/PR content from company websites so the team can monitor brand mentions and announcements.

Three scraping approaches were tested, plus a pipeline to push extracted data into Notion as a note-taking/tracking destination.

---

## Tools Evaluated

### 1. BeautifulSoup (Python, `test_beautifulsoup.py`)

Traditional HTML parsing using `requests` + `beautifulsoup4`.

**How it works:**
- Opens a session and visits the homepage first to pass the site's cookie gate
- Fetches the target article page
- Parses HTML to extract date (`.date` class), title (`h1`/`h2`), and body (`.detail` / `article` / `main` content area)

**Pros:**
- Lightweight, no API key needed, fully free
- Fast and predictable for well-structured pages

**Cons:**
- Brittle — breaks if the site's HTML structure changes
- Requires manual selector tuning per site
- Cannot handle JavaScript-rendered content

---

### 2. Firecrawl (`firecrawl-py`)

Cloud-based scraping service that converts web pages to clean Markdown.

**How it works:**
- Sends the URL to the Firecrawl API
- Firecrawl renders the page (handles JS) and returns clean Markdown text
- Requires `FIRECRAWL_API_KEY`

**Pros:**
- Handles dynamic/JS-rendered sites
- Returns clean, structured Markdown — easy to feed into an LLM
- No need to write custom HTML selectors

**Cons:**
- Paid service (API key required, usage costs apply)
- Output is raw Markdown — still needs post-processing to extract structured fields (title, date, body)
- Network latency for each request

---

### 3. ScrapeGraphAI + Groq (`test_scrapegraphai.py`)

LLM-powered extraction pipeline using `scrapegraphai` with Groq (free-tier Llama 3.3 70B) as the language model.

**How it works:**
- Fetches raw HTML manually (handles Viriyah's cookie gate with `requests.Session`)
- Passes the HTML + a structured prompt to `SmartScraperGraph`
- The LLM extracts `title`, `date`, `body`, and `source_url` as JSON
- Outputs saved to `output_english_scrapegraphai.json`

**Prompt used:**
```
Extract the following fields from this news article and return as JSON:
- title: article headline (preserve English text)
- date: publication date
- body: full article body text (preserve English text)
- source_url: the page URL
```

**LLM model:** `groq/llama-3.3-70b-versatile` (free tier)

**Pros:**
- Understands content semantically — no need to know the HTML structure
- Works across different site layouts with the same prompt
- Returns clean, structured JSON
- Groq free tier is sufficient for POC

**Cons:**
- Slower than direct HTML parsing
- Requires `GROQ_API_KEY`
- Gemini free tier was tested but **does not work in Thailand** (quota limit = 0)
- Non-deterministic — LLM output may vary slightly between runs

**Sample output (`output_english_scrapegraphai.json`):**
```json
{
  "content": {
    "title": "The Viriyah Insurance states that it is unaffiliated to \"V Group\"",
    "date": "28 Aug 2023",
    "body": "The Viriyah Insurance affirms that its business...",
    "source_url": "https://www.viriyah.co.th/en/news/"
  }
}
```

---

### 4. Notion Integration (`scrape_to_notion.py`)

Pipeline that combines BeautifulSoup scraping with the Notion API to push extracted articles into a Notion database.

**How it works:**
- Scrapes an article URL using BeautifulSoup (same cookie-gate workaround)
- Parses Thai Buddhist Era dates (พ.ศ.) to ISO 8601 (CE) for Notion's date field
- Splits long body text into 2000-character chunks (Notion API limit per rich_text element)
- Creates a new page in the specified Notion database with: Title, Date, Source URL, Body

**Requires:** `NOTION_TOKEN` + `NOTION_DATABASE_ID`

---

### 5. Full Social Listening Pipeline (`social_listening_pipeline.py`)

End-to-end pipeline combining all three steps: **Scrape → Analyze (LLM) → Store (Notion)**.

**How it works:**
1. Scrapes an article with BeautifulSoup (cookie-gate workaround included)
2. Passes the article body to **Groq (Llama 3.3 70B)** via LangChain for AI analysis
3. Groq returns structured JSON: sentiment, score, topics, summary, language
4. Pushes the article + analysis result to Notion as a single page

**Sample Groq analysis output:**
```json
{
  "sentiment": "neutral",
  "score": 0.0,
  "topics": ["Viriyah Insurance", "V Group", "electric vehicles", "insurance industry", "business clarification"],
  "summary": "The Viriyah Insurance company clarifies that it has no affiliation with the V Group and focuses solely on the insurance business.",
  "language": "en"
}
```

**Requires:** `GROQ_API_KEY` + `NOTION_TOKEN` + `NOTION_DATABASE_ID`

---

## Project Structure

```
Social-Listening/
├── social_listening_pipeline.py        # Full pipeline: Scrape → Groq LLM → Notion ★
├── test_beautifulsoup.py               # BeautifulSoup scraper POC
├── test_firecrawl.py                   # Firecrawl scraper POC
├── test_scrapegraphai.py               # ScrapeGraphAI + Groq LLM scraper POC
├── scrape_to_notion.py                 # BeautifulSoup → Notion (no LLM analysis)
├── .env.example                        # Environment variable template
├── pyproject.toml                      # Python dependencies (uv)
├── output_pipeline_sample.json         # Sample full pipeline output (with LLM analysis)
├── output_english_scrapegraphai.json   # Sample ScrapeGraphAI output (English)
├── output_scrapegraphai.json           # Sample ScrapeGraphAI output (Thai)
└── output2_scrapegraphai.json          # Additional ScrapeGraphAI test run
```

---

## Setup

**Requirements:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
# Install dependencies
uv sync

# Copy and fill in your API keys
cp .env.example .env
```

**.env variables:**
```
FIRECRAWL_API_KEY=   # from firecrawl.dev
GROQ_API_KEY=        # from console.groq.com (free tier available)
NOTION_TOKEN=        # Notion integration token
NOTION_DATABASE_ID=  # Target Notion database ID
```

---

## Running the Scripts

```bash
# Full pipeline: Scrape → Groq LLM analysis → Notion (recommended)
uv run python social_listening_pipeline.py

# BeautifulSoup scraper only
uv run python test_beautifulsoup.py

# Firecrawl scraper only
uv run python test_firecrawl.py

# ScrapeGraphAI + Groq
uv run python test_scrapegraphai.py

# Scrape and push to Notion (no LLM analysis)
uv run python scrape_to_notion.py
```

---

## Tool Comparison

| | BeautifulSoup | Firecrawl | ScrapeGraphAI + Groq |
|---|---|---|---|
| **Cost** | Free | Paid (API) | Free (Groq tier) |
| **Speed** | Fast | Medium | Slow |
| **JS support** | No | Yes | No (fetches raw HTML) |
| **Output** | Custom fields | Markdown | Structured JSON |
| **Maintenance** | High (selector changes) | Low | Low |
| **Setup** | No API key | API key | API key |
| **Best for** | Known stable sites | Dynamic sites | Flexible multi-site extraction |

---

## Key Findings

- **Viriyah's cookie gate** — the site serves a cookie-check landing page on the first request. All scrapers need to visit the homepage first via `requests.Session` before fetching article pages.
- **Gemini free tier is blocked in Thailand** — tested `langchain-google-genai` with Gemini Flash Lite but the free quota is 0 from Thailand. Switched to **Groq** (Llama 3.3 70B) which works.
- **ScrapeGraphAI is the most flexible** for handling multiple sites without changing selectors, at the cost of speed.
- **Notion integration works** — Thai Buddhist Era (พ.ศ.) dates are auto-converted to CE ISO 8601 for Notion's date field.
- **Full pipeline confirmed working** — `social_listening_pipeline.py` runs end-to-end: scrapes Viriyah article, gets LLM sentiment analysis from Groq, and saves the result to Notion in one command.



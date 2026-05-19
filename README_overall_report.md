# Social Listening — Research & POC Report

Internship task under AI Brain Lab 
Task Reference:Improve Datacrawler / Social Listening App

---

## 1. Social Listening Software in the Market

Social listening tools automatically monitor online platforms — news sites, forums, social media — for mentions of a brand or topic, then analyze the content to extract sentiment and insights.

### Major Commercial Tools

| Tool | Best For | Thai Language | Pricing (approx.) |
|---|---|---|---|
| Brandwatch | Large enterprise, deep historical data | Weak | $1,000–3,000+/month |
| Talkwalker | APAC markets, multi-language | Best among commercial tools | $9,000+/year |
| Meltwater | PR teams, news + social combined | Moderate | $4,000–7,000/year |
| Sprout Social | Marketing teams managing own channels | Weak | $249/month per user |
| Brand24 | Small teams, basic monitoring | Weak | $99–299/month |
| Mention | Simple keyword tracking, easy setup | Weak | $49–179/month |

### Why a Custom Solution Makes More Sense for BVTPA

Commercial tools are designed for generic marketing use cases and come with significant limitations for this project:

- **Thai language support is weak across the board** — most tools are built for English. Sentiment accuracy drops noticeably for Thai content, especially insurance-specific terminology and Thai forum slang (e.g. Pantip).
- **Talkwalker** is the strongest for Thai/APAC but priced at enterprise level with no justification for this project scope.
- **Data stays in the vendor's dashboard** — integrating it into KAM's database requires extra API work on top of the subscription cost.
- **KAM already has Gemini integrated** — Google's models handle Thai and English well due to strong Southeast Asian training data. This means we already have better Thai sentiment capability than most commercial tools, at no extra cost.

**Conclusion:** Building a lightweight custom pipeline using open-source and free-tier tools, then feeding the output into Gemini for analysis, is more practical, more accurate for Thai content, and significantly cheaper.

---

## 2. How Social Listening Works

The core pipeline — whether commercial tool or custom build — is the same:

```
1. Scrape      →  fetch content from target websites/sources
2. Filter      →  keep only content matching target keywords
3. Analyze     →  LLM classifies sentiment, extracts topics
4. Store       →  save to database with metadata (date, source, score)
5. Alert       →  notify team or display on dashboard
```

### Thai + English Scope

Target sources for BVTPA social listening would include:

- **Thai language** — Pantip.com (major Thai forum), Thai news sites (Khaosod, Manager Online), Facebook public groups
- **English language** — Bangkok Post, The Nation, company English press pages
- **Both** — viriyah.co.th publishes news in both languages

### What the LLM Step Looks Like

After scraping, the extracted text is passed to an LLM (Gemini or Claude) with a structured prompt. No custom NLP pipeline or tokenizer needed — the LLM handles both Thai and English in the same call.

Example prompt:
```
Analyze this text. Return JSON with:
- sentiment: positive / negative / neutral
- score: -1.0 to 1.0
- topics: list of key topics mentioned
- language: th or en
- summary: one sentence in English
```

Example output:
```json
{
  "sentiment": "negative",
  "score": -0.8,
  "topics": ["claims processing", "wait time"],
  "language": "th",
  "summary": "Customer complaining about slow claims processing, waiting 3 weeks."
}
```

---

## 3. Tools Evaluated — POC Overview

Three scraping approaches were tested against [Viriyah Insurance](https://www.viriyah.co.th/en/), one of Thailand's largest non-life insurance companies, plus a Notion integration pipeline.

### Common Finding — Cookie Gate

Viriyah's site blocks direct scraper requests. It serves a blank landing page on first visit and sets a cookie (`viriyah_landing=1`) before serving real content. All scrapers required a warm-up request to the homepage via `requests.Session()` before fetching article pages.

---

### Tool 1 — BeautifulSoup

Traditional HTML parsing using `requests` + `beautifulsoup4`. Free, no API key needed.

**Approach:** fetch page HTML → parse with BeautifulSoup → extract fields using CSS selectors (`.date`, `h1`, `.detail`)

**Result:** Successfully extracted date, title, and full body text from a Viriyah news article.

| Pros | Cons |
|---|---|
| Free, lightweight, no API key | Breaks if site HTML structure changes |
| Fast and predictable on static pages | Requires manual selector writing per site |
| Easy to understand and debug | Cannot handle JavaScript-rendered pages |

---

### Tool 2 — Firecrawl

Cloud-based scraping API that renders pages and returns clean Markdown. Requires `FIRECRAWL_API_KEY`.

**Approach:** send URL to Firecrawl API → receive clean Markdown text ready for LLM input

**Result:** Returns clean structured Markdown without needing custom selectors. Handles JS rendering automatically.

| Pros | Cons |
|---|---|
| Handles JS-rendered and dynamic sites | Paid service, API key required |
| No selector writing needed | Output is Markdown — needs post-processing for structured fields |
| Clean output, ideal for LLM pipelines | Network latency per request |

---

### Tool 3 — ScrapeGraphAI + Groq

LLM-powered extraction using `scrapegraphai` with Groq (Llama 3.3 70B, free tier) as the language model backend.

**Approach:** fetch raw HTML → pass to SmartScraperGraph with a plain English prompt → LLM extracts structured JSON

**Prompt used:**
```
Extract the following fields and return as JSON:
- title, date, body, source_url
```

**Result:** Successfully extracted all fields as clean JSON. Tested on both English and Thai article pages.

**Note:** Gemini free tier was tested but has 0 quota from Thailand — switched to Groq which works on free tier.

| Pros | Cons |
|---|---|
| No CSS selectors needed — prompt-based | Slower than direct HTML parsing |
| Works across different site layouts | Requires API key (Groq) |
| Returns clean structured JSON | LLM output can vary slightly between runs |
| Same prompt works for Thai and English | Not suitable for real-time high-volume scraping |

---

### Tool 4 — Notion Integration (`scrape_to_notion.py`)

Pipeline combining BeautifulSoup scraping with the Notion API to push extracted articles into a Notion database.

**Approach:** scrape article → parse Thai Buddhist Era dates (พ.ศ.) to ISO 8601 → split body into 2000-character chunks (Notion API limit) → create page in Notion database

**Result:** Successfully pushed scraped articles into Notion with title, date, source URL, and body. Thai date conversion works correctly.

**Requires:** `NOTION_TOKEN` + `NOTION_DATABASE_ID`

---

### Tool 5 — Full Social Listening Pipeline (`social_listening_pipeline.py`) ★

End-to-end pipeline combining all three stages into a single command.

**Pipeline:**
```
BeautifulSoup (scrape) → Groq Llama 3.3 70B (LLM analysis) → Notion (store)
```

**Approach:**
1. Scrapes article with BeautifulSoup (cookie-gate workaround)
2. Passes article body to Groq via LangChain with a structured prompt
3. Groq returns JSON: `sentiment`, `score`, `topics`, `summary`, `language`
4. Pushes article + AI analysis together into a Notion database page

**Result:** Confirmed working end-to-end. Sample run on Viriyah English article:

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

## 4. Tool Comparison

| | BeautifulSoup | Firecrawl | ScrapeGraphAI + Groq |
|---|---|---|---|
| **Cost** | Free | Paid (API) | Free (Groq tier) |
| **Speed** | Fast | Medium | Slow |
| **JS support** | No | Yes | No (raw HTML) |
| **Output format** | Custom fields | Markdown | Structured JSON |
| **Maintenance** | High (selector changes) | Low | Low |
| **API key needed** | No | Yes | Yes (Groq) |
| **Best for** | Known stable static sites | Dynamic/JS-heavy sites | Flexible multi-site extraction |

---

## 5. Key Findings

- **Cookie gate pattern** — Viriyah blocks raw scraper requests. `requests.Session()` warm-up on homepage bypasses this cleanly. Likely present on other Thai corporate sites too.
- **Gemini blocked in Thailand** — free tier quota is 0 from Thailand. Groq (Llama 3.3 70B) is a viable free alternative for LLM-based extraction.
- **ScrapeGraphAI is the most flexible** for handling multiple sites without rewriting selectors, at the cost of speed.
- **Notion integration works** including Thai Buddhist Era date conversion to CE ISO 8601.
- **For Thai content** — LLM-based analysis (Groq/Claude) handles Thai text well without needing a separate Thai NLP pipeline.
- **Full pipeline confirmed working** — `social_listening_pipeline.py` scrapes, analyzes, and stores in one command. Tested on Viriyah English news article.

---

## 6. Next Steps

- Expand scraper to collect the full news listing page, not just single articles
- Test Firecrawl on JavaScript-heavy Thai sources (Pantip, Facebook public pages)
- Add scheduling (cron / GitHub Actions) to run pipeline periodically
- Evaluate MCP server approach — Firecrawl MCP + Notion MCP connected inside Cursor as a no-code pipeline

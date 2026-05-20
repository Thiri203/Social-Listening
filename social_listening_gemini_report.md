# Social Listening — POC Report

**Author:** Thiri Shin Thant (ML/Analyst Intern, AI Brain Lab)  
**Project:** KAM — Phase 3 Social Listening Module (BVTPA)

---

## Overview

This report covers the research and POC work done on social listening pipeline using web scraping and LLM analysis. The goal was to evaluate how to automatically scrape insurance company websites, analyze content using Gemini AI, and store results in Notion for review.

---

## Pipeline Architecture

### Approach 1 — BeautifulSoup + Gemini (Hybrid)
```
Scrape (BeautifulSoup + requests) → Analyze (Gemini API) → Store (Notion)
```
File: `mcp_beautifulsopu_gemini_notion.py`

### Approach 2 — Gemini Only
```
Gemini (fetches URL + analyzes in one call) → Store (Notion)
```
File: `mcp_gemini_notion.py`

---

## Gemini API Integration

Integrated using the same pattern as `kam-backend` (Vertex AI via service account):

```python
from google import genai
from google.oauth2 import service_account

_credentials = service_account.Credentials.from_service_account_info(
    sa_info,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT_ID,
    location="us-central1",
    credentials=_credentials,
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(url_context=types.UrlContext())],
    ),
)
```

**Model used:** `gemini-2.5-flash`  
**GCP Project:** `esg-report-469503`  
**Auth:** Service account JSON (base64) from `GCP_SERVICE_ACCOUNT_JSON_BASE64`

> Note: The backend uses `gemini-3-flash-preview` on project `445438248473`. That model is not enabled on the `esg-report` project. `gemini-2.5-flash` was selected from the available model list and confirmed working.

---

## Target Sites — Scraping Results

### 1. AXA Thailand — https://www.axa.co.th/en

| | Approach 1 (BeautifulSoup) | Approach 2 (Gemini Only) |
|---|---|---|
| **Status** | ✅ Success | ✅ Success |
| **Title** | Protect What Matters | AXA Insurance Thailand : Know You Can |
| **Content** | Partial (JS-rendered page, BeautifulSoup got limited text) | Full page content fetched |
| **Sentiment** | Positive | Positive (0.8) |
| **Topics** | Insurance, Risk, Sustainability | Insurance, Customer Service, Sustainability, AXA Values, Claims |
| **Saved to Notion** | ✅ Yes | ✅ Yes |

**Finding:** AXA's site is JavaScript-rendered. Gemini's url_context tool handled it better than BeautifulSoup which only captured partial content ("Loading...").

---

### 2. Thai Life Insurance — https://www.thailife.com/?lang=en

| | Approach 1 (BeautifulSoup) | Approach 2 (Gemini Only) |
|---|---|---|
| **Status** | ✅ Success | ❌ WAF Blocked |
| **Title** | Thai Life insurance | Error: Could not access the page |
| **Content** | Full page content (Thai + English) | Blocked by Web Application Firewall |
| **Sentiment** | Positive (0.9) | N/A |
| **Topics** | Insurance Products, Life Stage Financial Planning, Company Financial Performance, Customer Service, Health Solutions | N/A |
| **Saved to Notion** | ✅ Yes | ✅ Yes (with error note) |

**Finding:** Thai Life uses a Web Application Firewall (WAF) that blocks requests from cloud/bot IP ranges. Gemini's url_context fetches from Google's cloud servers → blocked. BeautifulSoup running locally uses our machine's IP which appears as a regular browser → allowed.

---

### 3. AIA Thailand — https://www.aia.co.th/en/health-wellness/vitality

| | Approach 1 (BeautifulSoup) | Approach 2 (Gemini Only) |
|---|---|---|
| **Status** | ✅ Success | ✅ Success |
| **Title** | AIA Vitality for every step of your wellness | AIA Vitality for every step of your wellness |
| **Content** | Main content extracted | Full page content fetched |
| **Sentiment** | Positive | Positive (0.9) |
| **Topics** | Health Insurance, Wellness Program, Rewards, Preventative Health, Lifestyle | Health, Wellness, Insurance, Rewards, Lifestyle |
| **Saved to Notion** | ✅ Yes | ✅ Yes |

**Finding:** AIA's site works well with both approaches. Gemini's analysis was slightly more detailed.

---

## Notion Database

All results stored in the shared **Social Listening** Notion database.

Each entry contains:
- **Title** — page/article title
- **Source URL** — original URL
- **Date** — publication date (if found)
- **Body** — AI analysis block + original content

Sample analysis block format:
```
--- AI Analysis (Gemini / gemini-2.5-flash) ---
Sentiment : positive (score: 0.8)
Topics    : Insurance, Customer Service, Sustainability, AXA Values, Claims
Language  : en
Summary   : AXA Insurance Thailand offers various insurance solutions...

--- Content ---
[original page content]
```

---

## Key Findings & Recommendations

### What Works
- **Gemini-only pipeline** is the cleanest approach — one API call does both fetching and analysis. Works well on AXA and AIA.
- **BeautifulSoup + Gemini hybrid** is the reliable fallback — handles WAF-protected sites since requests come from local machine IP.
- Both pipelines successfully push structured data into Notion.

### Limitations

| Issue | Affected Site | Root Cause | Recommendation |
|---|---|---|---|
| WAF blocking Gemini url_context | Thai Life | Requests from Google cloud IP ranges are blocked | Use BeautifulSoup hybrid for WAF-protected sites |
| JS-rendered pages | AXA (partial) | BeautifulSoup cannot execute JavaScript | Gemini url_context or Firecrawl handles this better |
| No article-level scraping yet | All | Current pipeline targets landing pages, not article listings | Build article link extractor per site in next phase |

### Recommended Production Approach
Use **Gemini-only** as primary. Automatically fall back to **BeautifulSoup + Gemini** when Gemini url_context returns an access error. This gives maximum coverage across sites with different security configurations.

---

## Files Produced

| File | Description |
|---|---|
| `mcp_gemini_notion.py` | Gemini-only pipeline: Gemini fetch+analyze → Notion |
| `mcp_beautifulsopu_gemini_notion.py` | Hybrid pipeline: BeautifulSoup scrape → Gemini analyze → Notion |
| `social_listening_pipeline.py` | Original POC: BeautifulSoup → Groq (Llama 3.3 70B) → Notion |
| `test_beautifulsoup.py` | BeautifulSoup scraper test |
| `test_firecrawl.py` | Firecrawl API scraper test |
| `test_scrapegraphai.py` | ScrapeGraphAI + Groq test |
| `scrape_to_notion.py` | BeautifulSoup → Notion (no LLM) test |
| `beautiful_soup_scrap.py` | BeautifulSoup scraper exploration |

---

## Environment Setup

```bash
# Install dependencies
uv sync

# Run Gemini-only pipeline
uv run python mcp_gemini_notion.py

# Run hybrid pipeline (fallback for WAF-protected sites)
uv run python mcp_beautifulsopu_gemini_notion.py
```

Required `.env` variables:
```
GOOGLE_API_KEY=...
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=esg-report-469503
GOOGLE_CLOUD_LOCATION=us-central1
GCP_PROJECT_ID=esg-report-469503
GCP_SERVICE_ACCOUNT_JSON_BASE64=...
NOTION_TOKEN=...
NOTION_DATABASE_ID=...
```

# ReviewPulse 📊

**Amazon Review Monitoring & Sentiment Analysis**

Track what customers are saying about products, spot trends, and get actionable insights.

## Features

- 🔍 **Review Fetching** — Pull reviews from Amazon product pages
- 📊 **Sentiment Analysis** — Positive/negative/neutral classification
- 🏷️ **Keyword Extraction** — Find common themes and complaints
- 📈 **Trend Detection** — Track sentiment over time
- 🚨 **Alerts** — Get notified about negative review spikes
- 📋 **Reports** — Export analysis to CSV/JSON

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Analyze a product
python reviewpulse.py --asin B0XXXXXX --marketplace ca

# Generate report
python reviewpulse.py --asin B0XXXXXX --report
```

## Why This Exists

Amazon blocks most scraping attempts. ReviewPulse uses:
- Rotating user agents
- Request delays
- Fallback to public review APIs
- Local caching to reduce requests

## Status

🚧 **In Development** — Built by [Sola Ray](https://solamnzigroup.github.io)

---

*Part of the [sola-workspace](https://github.com/solamnzigroup/sola-workspace) project.*

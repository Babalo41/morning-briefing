# Intelligent Content Discovery System

## Overview

The briefing now uses a **multi-agent intelligent content discovery pipeline** that supplements RSS feeds with intelligent web scraping and semantic ranking. This transforms the briefing from a simple news aggregator into a **contextually-aware learning companion** tailored to your interests and expertise.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ DATA SOURCES LAYER (30-min refresh cycle)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  • RSS Feeds (existing)     • Web Scraping (crawl4AI)            │
│  • Calendar Events          • Smart URL Extraction               │
│  • Health Supplies          • Fallback: Basic HTML scraping      │
│  • Weather API                                                   │
│                                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ MULTI-AGENT ORCHESTRATION (pipeline/agents.py)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ┌─ Agent 1: SemanticFilterAgent ─────────────────────────┐      │
│ │  Filters by relevance to your interests:              │      │
│ │  • Profile keywords (ISTQB, SINA, networking, etc)   │      │
│ │  • Glossary terms (German B1 vocab)                   │      │
│ │  • Profile-specific technical interests               │      │
│ │  Output: Items scored 0.0-1.0 by relevance           │      │
│ └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│ ┌─ Agent 2: RankingAgent ────────────────────────────────┐      │
│ │  Multi-criteria ranking:                              │      │
│ │  • 40% Recency (exponential decay, 36h half-life)    │      │
│ │  • 35% Semantic relevance (from Agent 1)             │      │
│ │  • 25% Domain specificity (tech depth matching)       │      │
│ │  Output: Final rank score per item                    │      │
│ └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│ ┌─ Agent 3: InsightAgent ────────────────────────────────┐      │
│ │  Cross-source pattern detection:                      │      │
│ │  • Clusters similar articles across sources           │      │
│ │  • Generates "Trending" insights (2+ sources)         │      │
│ │  • Tags articles with cluster ID                      │      │
│ │  Output: Insight items + cluster metadata             │      │
│ └─────────────────────────────────────────────────────────┘      │
│                                                                   │
│ ┌─ Agent 4: DomainExtractionAgent ──────────────────────┐      │
│ │  Technical domain detection:                          │      │
│ │  • ISTQB & Software Testing                          │      │
│ │  • Defense Electronics & Secure Networking           │      │
│ │  • Network & Systems Engineering                      │      │
│ │  • Professional Development                           │      │
│ │  Output: Domain tags + rank boost (20% per domain)   │      │
│ └─────────────────────────────────────────────────────────┘      │
│                                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ INTELLIGENT COMPOSITION                                          │
├─────────────────────────────────────────────────────────────────┤
│  • Sort by rank score                                            │
│  • Cap per section                                               │
│  • Enrich with glossary linking                                 │
│  • Flag insights with special styling                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│ RENDERED BRIEFING                                                │
├─────────────────────────────────────────────────────────────────┤
│  Each section now shows:                                        │
│  • Most relevant items first (semantic + recency)              │
│  • Insights: "📌 Trending: X trending across 3 sources"        │
│  • Domain-specific boosts for your interests                   │
│  • Glossary terms clickable (German B1 learning)               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. **Scraping Layer** (`pipeline/scrape.py`)

- **crawl4AI Integration**: Uses crawl4AI for intelligent semantic extraction (when available)
- **Graceful Degradation**: Falls back to basic HTML scraping if crawl4ai not installed
- **Semantic Instructions**: Each scrape source has specific extraction prompts
- **Parallel Execution**: Scrapes up to 3 URLs concurrently to stay within the 30-min pipeline window

**Example**:
```python
result = scrape.scrape_url(
    "https://github.com/topics/qa-automation",
    semantic_instructions="Extract trending QA automation projects and tools"
)
```

### 2. **Multi-Agent Orchestration** (`pipeline/agents.py`)

#### SemanticFilterAgent
Scores items 0.0-1.0 based on relevance to:
- Your technical interests (from `profile.yaml`: ISTQB, SINA box, INFODAS, networking, etc.)
- German B1 glossary terms (for language learning context)

**Formula**:
```
relevance_score = keyword_matches + glossary_matches (0.0-1.5 range, capped at 1.0)
```

#### RankingAgent
Final score combines multiple factors:
```
rank_score = (recency × 0.4) + (semantic × 0.35) + (domain × 0.25)
```

**Recency**: Exponential decay with 36-hour half-life
- Articles from 12 hours ago: ~0.8 score
- Articles from 36 hours ago: 0.5 score
- Articles from 72 hours ago: 0.25 score

#### InsightAgent
Detects trending topics:
1. Clusters articles by title similarity (>30% match)
2. Generates insights for clusters with 2+ articles
3. Example insight: "📌 Trending: VLAN networking trending across 3 sources"

#### DomainExtractionAgent
Identifies technical domains and boosts rank score:
- Each domain match: +20% rank boost
- Example: Article about "VLAN subnetting" gets 40% boost (2 domains: networking + systems)

### 3. **Configuration** (`config/scrape_sources.yaml`)

Defines:
- **scrape_sources**: URLs to supplement RSS, refresh intervals, semantic instructions
- **domain_keywords**: Technical keywords and boost factors per domain

**Key insight**: Keywords guide both scraping (what to extract) AND ranking (relevance scoring).

### 4. **Integration** (`pipeline/compose.py`)

- Creates orchestrator on each pipeline run
- Passes it to `_rss_block()` for each section
- Sections that use agents: ISTQB & Testing, Defense Electronics, Networking, Tooling, World & Knowledge
- Other sections (calendar, health, weather) unchanged

## Data Flow Example

**Input**: Today's RSS feeds (20 items) + scraped Hacker News (10 items)

**Step 1: Semantic Filter**
- "VPN security announcement" vs "Random startup news"
- Filter looks for: "vlan", "network", "security", "defense", etc.
- VPN article: relevance = 0.8 (matched 4 keywords)
- Startup article: relevance = 0.1 (matched 1 keyword)

**Step 2: Ranking**
- VPN article from 2 hours ago: rank = (0.95 recency × 0.4) + (0.8 semantic × 0.35) + (0.9 domain × 0.25) = **0.793**
- Old generic security article: rank = (0.5 recency × 0.4) + (0.3 semantic × 0.35) + (0.2 domain × 0.25) = **0.280**

**Step 3: Insights**
- If 3 sources mention "VLAN configuration fixes", generate insight

**Step 4: Domain Extraction**
- VPN article tagged: ["networking", "defense_electronics"]
- Boost: 0.793 × 1.4 = **1.11** (capped at max rank)

**Result**: VPN article appears at top of "Network & Systems Engineering" section

## Configuration Tuning

### Adjust Profile Interests
In `config/profile.yaml`:
```yaml
technical_interests:
  - ISTQB certification
  - Secure networking
  - SINA box configuration
  # Add more keywords here
```

### Add Scrape Sources
In `config/scrape_sources.yaml`:
```yaml
scrape_sources:
  - url: "https://example.com/news"
    category: "profession_field"
    name: "My News Source"
    refresh_hours: 24
    semantic_instructions: "Extract content about X and Y"
```

### Adjust Domain Weights
In `config/scrape_sources.yaml`:
```yaml
domain_keywords:
  my_interest:
    keywords: [keyword1, keyword2, ...]
    boost: 1.5  # 50% rank boost for matches
```

## Performance Characteristics

- **Pipeline Duration**: ~5-10 seconds (RSS + light scraping)
- **Memory**: ~50-100 MB (in-memory sorting/clustering)
- **Parallel Scraping**: 3 concurrent requests (configurable)
- **Cache Behavior**: Scrape sources cached per `refresh_hours`

## Fallback Behavior

### If crawl4ai unavailable:
- System logs warning: "crawl4ai not installed; web scraping disabled (RSS only)"
- Agents still run on RSS content
- Graceful degradation to RSS-only pipeline

### If scrape fails (403, 404, timeout):
- Logged but not fatal
- Section continues with RSS items only
- Orchestrator still processes available items

### If agent fails:
- Logged and skipped
- Next agent runs on unmodified items
- Final fallback: basic recency ranking

## Future Enhancements

1. **Local LLM Summarization**: Use ollama/transformers for headline generation
2. **Semantic Clustering**: Use embeddings (sentence-transformers) for smarter insights
3. **Cross-Domain Trending**: Detect when same topic appears across multiple sections
4. **User Feedback Loop**: Track which articles user reads to refine scoring
5. **Archive Analysis**: Show "similar articles from 3 months ago" insights
6. **Predictive Ranking**: ML model predicting which articles you'll actually read

## Debugging

Enable debug logging:
```bash
# In run_pipeline.py or via logging config
logging.getLogger("agents").setLevel(logging.DEBUG)
logging.getLogger("scrape").setLevel(logging.DEBUG)
```

Check pipeline logs:
```bash
tail -f logs/pipeline.log
```

Watch agent scores:
```python
# In compose.py, after orchestrator.process():
for item in items:
    print(f"{item['title']}: rank={item['_rank_score']}, domains={item['_domain_tags']}")
```

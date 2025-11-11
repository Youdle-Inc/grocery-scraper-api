# Fast Universal Grocery API - Architecture Plan

## 🎯 Goal
Build the fastest, most reliable universal grocery search API that works across all major stores without requiring paid API access.

## 🚀 Core Principles

1. **Speed First**: Target <500ms for cached results, <2s for fresh results
2. **Multi-Source Strategy**: Combine multiple data sources for reliability
3. **Smart Caching**: Aggressive caching with intelligent invalidation
4. **Parallel Execution**: Fetch from all stores simultaneously
5. **Graceful Degradation**: Fallback strategies when sources fail
6. **No External APIs Required**: Use only free/open sources

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                      │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Cache      │   │  Multi-Source│   │  Result      │
│  Layer       │   │  Fetcher     │   │  Aggregator  │
└──────────────┘   └──────────────┘   └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Direct HTML  │   │  Search      │   │  AI          │
│ Scraping     │   │  Engines     │   │  Extraction  │
└──────────────┘   └──────────────┘   └──────────────┘
```

## 🔧 Data Sources (Priority Order)

### ⚠️ Reality Check: Most Stores Don't Have Public APIs
**Key Finding**: Target, Walmart, Kroger, and most major grocery stores do NOT offer public APIs. The Redsky API mentioned in some docs is internal-only. We need to build a robust scraping infrastructure.

### Tier 1: HTML Scraping (PRIMARY METHOD)
**All stores require HTML scraping:**
- Target, Walmart, Kroger, Safeway/Albertsons
- Publix, H-E-B, Trader Joe's, Whole Foods
- ALDI, Costco, Regional chains

**Robust Scraping Strategy:**
- **Proxy Rotation**: Rotate IPs to avoid blocks
- **User-Agent Rotation**: Mimic different browsers/devices
- **Rate Limiting**: Respectful delays between requests
- **CAPTCHA Handling**: Integrate solving services if needed
- **Selector Management**: Store-specific parsers with fallbacks
- **Change Detection**: Monitor for site structure changes
- **BeautifulSoup**: Fast HTML parsing
- **AI Fallback**: Use AI extraction when selectors fail

**Performance:**
- ~500ms-1s per store (with good caching)
- Parallel execution across stores
- Total time: ~1-2s for 5 stores
- Cache aggressively to reduce scraping load

### Tier 3: Search Engine APIs (Fallback)
**Free search APIs:**
- **Serper API** (free tier: 2500 requests/month)
- **Google Custom Search** (free tier: 100 requests/day)
- **Bing Search API** (free tier available)

**Use Cases:**
- When direct scraping fails
- For stores with complex anti-bot measures
- As a backup data source

**Implementation:**
- Only use when primary sources fail
- Cache results aggressively
- Use for product discovery, not pricing

### Tier 3: AI Extraction (Fallback for Complex Pages)
**For complex pages:**
- Use OpenAI/Anthropic for structured extraction
- Only when other methods fail
- Cache results to minimize API calls

## 🏗️ Component Design

### 1. Robust HTML Scraper (`scraper/robust_scraper.py`)

```python
class RobustScraper:
    """
    Production-grade HTML scraper with:
    - Proxy rotation
    - User-agent rotation
    - Rate limiting
    - CAPTCHA handling
    - Change detection
    - Store-specific parsers
    """
    
    async def scrape_store(
        self, 
        store_id: str,
        query: str, 
        zipcode: str
    ) -> List[Dict]:
        """
        Scrape products from store with all protections
        Returns products with fallback strategies
        """
```

**Features:**
- Proxy pool management
- Request rate limiting
- User-agent rotation
- CAPTCHA detection & solving
- Selector fallback chain
- HTML change monitoring
- Error recovery

### 2. Store Scrapers (`scraper/store_scrapers/`)

**Structure:**
```
store_scrapers/
├── __init__.py
├── base.py          # Base scraper interface
├── target_scraper.py    # Target-specific scraper
├── walmart_scraper.py   # Walmart-specific scraper
├── kroger_scraper.py    # Kroger-specific scraper
└── ...
```

**Base Interface:**
```python
class BaseStoreScraper:
    async def search_products(
        self, 
        query: str, 
        zipcode: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Search products via HTML scraping"""
        raise NotImplementedError
    
    def get_selectors(self) -> Dict:
        """Return store-specific CSS selectors"""
        raise NotImplementedError
    
    def parse_product(self, html_element) -> Dict:
        """Parse product from HTML element"""
        raise NotImplementedError
```

### 3. Smart Cache (`scraper/smart_cache.py`)

**Caching Strategy:**
- **Product searches**: 15 minutes (prices change frequently)
- **Store locations**: 24 hours (rarely change)
- **Product details**: 1 hour (moderate change)
- **HTML responses**: 5 minutes (for scraping)

**Cache Keys:**
```
products:{store_id}:{query}:{zipcode}
stores:{zipcode}
product_details:{product_id}
html:{url_hash}
```

**Features:**
- Redis for distributed caching
- In-memory fallback
- Cache warming for popular queries
- Smart invalidation

### 4. Result Aggregator (`scraper/result_aggregator.py`)

**Features:**
- Deduplicate products across stores
- Merge product variants
- Rank by relevance
- Group by canonical product
- Price comparison

### 5. Query Optimizer (`scraper/query_optimizer.py`)

**Optimizations:**
- Query normalization
- Brand detection
- Category detection
- Query expansion
- Store-specific query formatting

## ⚡ Performance Optimizations

### 1. Parallel Execution
```python
# Fetch from all stores simultaneously
tasks = [
    fetch_store_products(store_id, query, zipcode)
    for store_id in store_ids
]
results = await asyncio.gather(*tasks)
```

### 2. Connection Pooling
- Reuse HTTP connections
- Keep-alive connections
- Connection limits per store

### 3. Request Batching
- Batch multiple product lookups
- Reduce API calls
- Group by store

### 4. Streaming Responses
- Return results as they arrive
- Use Server-Sent Events (SSE)
- Improve perceived performance

### 5. Precomputation
- Pre-fetch popular queries
- Cache store locations
- Warm cache on startup

## 📋 Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Multi-source fetcher framework
- [ ] Smart cache implementation
- [ ] Base store client interface
- [ ] Result aggregator
- [ ] Query optimizer

### Phase 2: Robust Scraping Infrastructure (Week 2)
- [ ] Proxy rotation system
- [ ] User-agent rotation
- [ ] Rate limiting middleware
- [ ] CAPTCHA detection/handling
- [ ] Change detection system
- [ ] Error recovery mechanisms

### Phase 3: Store-Specific Scrapers (Week 3)
- [ ] Target scraper (highest priority)
- [ ] Walmart scraper
- [ ] Kroger scraper
- [ ] Safeway/Albertsons scraper
- [ ] Store selector management
- [ ] Parser fallback chains

### Phase 4: Integration & Optimization (Week 4)
- [ ] Integrate all sources
- [ ] Performance tuning
- [ ] Caching optimization
- [ ] Error handling
- [ ] Documentation

## 🎯 Success Metrics

### Performance Targets
- **Cached responses**: <100ms (p95)
- **Fresh scraping**: <1s per store (p95)
- **HTML parsing**: <200ms per page (p95)
- **Full aggregate search**: <2-3s for 5 stores (p95)
- **Cache hit rate**: >70% (aggressive caching)

### Reliability Targets
- **Uptime**: 99.9%
- **Success rate**: >95% for popular stores
- **Data accuracy**: >90% price accuracy
- **Coverage**: Support 20+ stores

## 🔒 Error Handling

### Retry Strategy
- **API calls**: 3 retries with exponential backoff
- **HTML scraping**: 2 retries
- **Timeout**: 5s for APIs, 10s for HTML

### Fallback Chain
1. Try direct API
2. If fails, try HTML scraping
3. If fails, try search engine
4. If fails, return cached result
5. If no cache, return partial results

### Graceful Degradation
- Return partial results if some stores fail
- Mark unavailable stores in response
- Continue processing other stores
- Log errors for monitoring

## 📊 Monitoring & Observability

### Metrics to Track
- Response times by source
- Cache hit rates
- Error rates by store
- API rate limit hits
- Success rates

### Logging
- Request/response logging
- Error tracking
- Performance metrics
- Cache statistics

## 🚀 Quick Start Implementation

### Step 1: Create Base Structure
```bash
mkdir -p scraper/store_clients
touch scraper/store_clients/__init__.py
touch scraper/store_clients/base.py
touch scraper/multi_source_fetcher.py
touch scraper/smart_cache.py
```

### Step 2: Build Robust Scraping Infrastructure
- Set up proxy rotation (use free proxies or paid service)
- Implement user-agent rotation
- Add rate limiting (respectful delays)
- Build change detection system
- Test with Target first

### Step 3: Implement Store-Specific Scrapers
- Start with Target scraper (most popular)
- Use existing selector configs from config.py
- Add fallback parsing strategies
- Implement error recovery
- Add caching layer

### Step 4: Expand to Other Stores
- Add Walmart scraper
- Add Kroger scraper
- Add Safeway/Albertsons scraper
- Optimize parallel execution
- Monitor for site changes

## 💡 Key Decisions

### Why Scraping Instead of APIs?
- **Reality**: Most stores don't offer public APIs
- **Control**: Direct control over data extraction
- **Cost**: Avoid expensive third-party services
- **Coverage**: Can scrape any store website
- **Flexibility**: Adapt to site changes quickly

### Why Multi-Source?
- **Reliability**: If one source fails, others work
- **Coverage**: Some stores only available via scraping
- **Speed**: Use fastest available source
- **Accuracy**: Cross-validate results

### Why Aggressive Caching?
- **Speed**: Cached results are instant
- **Cost**: Reduce API calls and scraping
- **Reliability**: Serve cached data if sources fail
- **User Experience**: Faster responses

## 🎓 Best Practices

### Scraping Ethics & Legal
1. **Respect robots.txt**: Check and follow robots.txt files
2. **Rate limiting**: Don't overload servers (1-2 req/sec per store)
3. **Terms of Service**: Review ToS, scrape only public data
4. **User-Agent**: Use descriptive user-agent identifying your service
5. **Off-peak scraping**: Scrape during low-traffic hours when possible

### Technical Best Practices
1. **Always cache**: Cache everything aggressively (15min-1hr)
2. **Fail fast**: Don't wait for slow/timeout sources
3. **Parallelize**: Fetch from all stores simultaneously
4. **Validate**: Check data quality before returning
5. **Monitor**: Track performance, errors, and site changes
6. **Document**: Keep selector configs and parsers documented
7. **Test**: Test all stores regularly for breakage
8. **Optimize**: Continuously improve parsing accuracy
9. **Proxy rotation**: Use proxies to avoid IP blocks
10. **Error recovery**: Graceful fallbacks when scraping fails

## 📝 Next Steps

1. **Review this plan** - Make sure it aligns with goals
2. **Prioritize stores** - Start with most popular stores
3. **Implement Phase 1** - Build core infrastructure
4. **Test & iterate** - Validate approach
5. **Expand** - Add more stores and sources


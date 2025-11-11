# 🏗️ Architecture Overview

High-level architecture and design decisions for the Grocery Scraper API.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                      (main.py)                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │      Request Routing & Validation      │
        │      (Pydantic Models)                │
        └───────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  Store Discovery │                  │  Product Search  │
│  Endpoint        │                  │  Endpoints       │
└──────────────────┘                  └──────────────────┘
        │                                       │
        ▼                                       ▼
┌──────────────────────────────────────────────────────────┐
│              UniversalGrocerySearch                        │
│              (Orchestrates multi-store searches)           │
└──────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  SerperClient    │                  │  Availability     │
│  (Google Search) │                  │  Checker         │
└──────────────────┘                  └──────────────────┘
        │                                       │
        ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│  Serper API      │                  │  HTML Scraper    │
│  (External)      │                  │  AI Scraper      │
└──────────────────┘                  └──────────────────┘
```

## Component Overview

### 1. FastAPI Application (`main.py`)

**Responsibilities:**
- HTTP request handling
- Route definitions
- Request validation (Pydantic models)
- Response formatting
- Error handling
- CORS configuration

**Key Endpoints:**
- `/health` - Health check
- `/stores/{zipcode}` - Store discovery
- `/products/search` - Product search
- `/products/aggregate` - Multi-store comparison
- `/products/aggregate/stream` - Streaming results

### 2. SerperClient (`scraper/serper_client.py`)

**Responsibilities:**
- Serper API communication
- Search query construction
- Result parsing and normalization
- Store domain mapping
- Address extraction (regex patterns)
- Price extraction (regex patterns)
- Product data extraction

**Key Methods:**
- `search_products_structured()` - Search for products
- `search_stores_in_zipcode()` - Find stores by location
- `_normalize_product()` - Normalize product data
- `_extract_price()` - Extract prices from text
- `_extract_address()` - Extract addresses from text

### 3. UniversalGrocerySearch (`scraper/universal_search.py`)

**Responsibilities:**
- Orchestrating multi-store searches
- Query expansion and optimization
- Result aggregation
- Concurrent API calls
- Store selection logic

**Key Methods:**
- `search()` - Main search method
- `_search_with_serper()` - Serper-based search
- `_search_expanded_queries()` - Query expansion

### 4. AvailabilityChecker (`scraper/availability_checker.py`)

**Responsibilities:**
- Checking product availability
- HTML scraping for stock status
- AI-powered availability detection
- Batch availability checking

**Key Methods:**
- `check_availability_batch()` - Check multiple products
- `_check_with_html()` - HTML-based checking
- `_check_with_ai()` - AI-based checking

### 5. ProductValidator (`scraper/product_validator.py`)

**Responsibilities:**
- AI-powered product validation
- Filtering generic/placeholder products
- Price authenticity validation
- URL validity checking

**Key Methods:**
- `validate_products()` - Validate product list
- `_validate_with_ai()` - AI validation
- `_basic_validation()` - Basic pattern matching

### 6. AIScraper (`scraper/ai_scraper.py`)

**Responsibilities:**
- AI-powered data enrichment
- Price extraction from HTML
- Product information extraction
- Fallback for missing data

**Key Methods:**
- `extract_price()` - Extract price from HTML
- `extract_product_info()` - Extract product data

### 7. Cache (`scraper/cache.py`)

**Responsibilities:**
- Response caching
- Cache key generation
- Cache expiration management
- Redis integration (if available)

**Key Methods:**
- `get()` - Get cached value
- `set()` - Set cached value
- `delete()` - Delete cached value

## Data Flow

### Product Search Flow

```
1. User Request
   ↓
2. FastAPI Route Handler
   ↓
3. UniversalGrocerySearch.search()
   ↓
4. SerperClient.search_products_structured()
   ↓
5. Serper API (Google Search)
   ↓
6. Result Parsing & Normalization
   ↓
7. AvailabilityChecker.check_availability_batch()
   ↓
8. ProductValidator.validate_products()
   ↓
9. Response Formatting
   ↓
10. JSON Response
```

### Store Discovery Flow

```
1. User Request (/stores/{zipcode})
   ↓
2. FastAPI Route Handler
   ↓
3. SerperClient.search_stores_in_zipcode()
   ↓
4. Serper API (Google Search)
   ↓
5. Address Extraction (Regex)
   ↓
6. Store Data Normalization
   ↓
7. Response Formatting
   ↓
8. JSON Response
```

### Aggregate Products Flow

```
1. User Request (/products/aggregate)
   ↓
2. FastAPI Route Handler
   ↓
3. UniversalGrocerySearch.search() (per store)
   ↓
4. Concurrent Store Searches
   ├─→ SerperClient (Target)
   ├─→ SerperClient (Walmart)
   ├─→ SerperClient (Kroger)
   └─→ ...
   ↓
5. Product Grouping (by name similarity)
   ↓
6. Store Location Matching
   ↓
7. Availability Checking (batch)
   ↓
8. Product Validation
   ↓
9. Search Insights Generation
   ↓
10. Response Formatting
   ↓
11. JSON Response
```

## Key Design Decisions

### 1. Serper API Integration

**Why Serper?**
- Google-powered search provides comprehensive coverage
- Real-time results from actual store websites
- No need for individual store API integrations
- Fast response times

**Trade-offs:**
- Requires parsing unstructured search results
- May need HTML scraping for additional data
- Rate limits from Serper API

### 2. Multi-Store Architecture

**Why Multi-Store?**
- Users want to compare prices across stores
- Different stores have different product availability
- Location-based filtering requires store-specific searches

**Implementation:**
- Concurrent API calls for performance
- Store-specific query optimization
- Result aggregation and deduplication

### 3. AI-Powered Validation

**Why AI Validation?**
- Search results may include non-product pages
- Generic/placeholder products need filtering
- Price authenticity verification

**Implementation:**
- OpenAI/Anthropic API for validation
- Fallback to basic pattern matching
- Confidence scoring for products

### 4. Caching Strategy

**Why Cache?**
- Reduce API calls to Serper
- Improve response times
- Reduce costs

**Implementation:**
- Store locations: 24-hour cache
- Product searches: 1-hour cache
- Cache invalidation via `refresh` parameter

### 5. Streaming API

**Why Streaming?**
- Better UX for web applications
- Results appear as they're found
- No need to wait for all stores

**Implementation:**
- Server-Sent Events (SSE)
- Incremental result delivery
- Store-by-store completion events

## Error Handling

### Strategy

1. **Graceful Degradation**: If one store fails, continue with others
2. **Fallback Mechanisms**: AI scraper as fallback for missing data
3. **Error Logging**: Comprehensive logging for debugging
4. **User-Friendly Messages**: Clear error messages without sensitive data

### Error Types

- **API Errors**: Serper API failures → Retry with exponential backoff
- **Parsing Errors**: Invalid data → Skip and continue
- **Validation Errors**: Invalid input → Return 400 with details
- **Service Errors**: External service down → Return 503

## Performance Optimizations

### 1. Concurrent Requests

- Use `asyncio.gather()` for parallel store searches
- Batch availability checks
- Parallel HTML scraping

### 2. Caching

- Redis for distributed caching (if available)
- In-memory cache as fallback
- Smart cache key generation

### 3. Query Optimization

- Store-specific query construction
- Location-aware queries
- Result filtering before processing

### 4. Data Extraction

- Efficient regex patterns
- Early filtering of irrelevant results
- Minimal HTML parsing

## Security Considerations

### 1. API Keys

- Stored in environment variables
- Never committed to version control
- Server-side only

### 2. Input Validation

- Pydantic models for validation
- ZIP code format checking
- Query sanitization

### 3. Error Messages

- No sensitive data in errors
- Generic error messages for users
- Detailed logs for debugging

## Scalability

### Current Limitations

- Single server instance
- In-memory caching
- No load balancing

### Future Improvements

- Redis for distributed caching
- Horizontal scaling with load balancer
- Database for persistent storage
- Queue system for async processing

## Monitoring & Observability

### Logging

- Structured logging with levels
- Request/response logging
- Error tracking
- Performance metrics

### Metrics to Track

- Response times per endpoint
- API call success rates
- Cache hit rates
- Error rates by type

## Testing Strategy

### Unit Tests

- Individual component testing
- Mock external APIs
- Test error handling

### Integration Tests

- End-to-end API testing
- Real API calls (with test keys)
- Performance testing

### Manual Testing

- Test script (`test_localhost.sh`)
- Comprehensive test cases
- Different ZIP codes and products

## Future Enhancements

### Planned Improvements

1. **Database Integration**: Store product history
2. **Price Tracking**: Historical price data
3. **Webhook Support**: Real-time updates
4. **Advanced Filtering**: Price range, brand filters
5. **Multi-language**: International support

---

**Architecture Version**: 3.0.0  
**Last Updated**: January 2025


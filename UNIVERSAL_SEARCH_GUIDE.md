# Reverse Engineering User Search: Building an Optimal Universal Grocery Search API

## Table of Contents
1. [Understanding User Search Behavior](#understanding-user-search-behavior)
2. [Reverse Engineering Techniques](#reverse-engineering-techniques)
3. [Query Understanding & Intent Detection](#query-understanding--intent-detection)
4. [Universal Search Architecture](#universal-search-architecture)
5. [Implementation Strategy](#implementation-strategy)
6. [Advanced Techniques](#advanced-techniques)

---

## Understanding User Search Behavior

### Common User Search Patterns

#### 1. **Query Types**
```
Product Name:        "milk", "organic eggs", "whole wheat bread"
Brand + Product:     "Kellogg's cereal", "Coca Cola"
Category:            "dairy", "produce", "snacks"
Attribute-Based:     "organic", "gluten-free", "low-fat"
Quantity-Based:      "12 pack", "gallon", "family size"
Intent-Based:        "breakfast", "dinner", "snacks for kids"
```

#### 2. **Query Characteristics**
- **Short queries**: 1-3 words (most common)
- **Ambiguous terms**: "lemon" (fruit vs. detergent)
- **Synonyms**: "soda" vs "pop" vs "soft drink"
- **Misspellings**: "orgainic" → "organic"
- **Natural language**: "I need milk for my coffee"
- **Context-dependent**: "eggs" (breakfast vs. baking)

#### 3. **Search Session Patterns**
```
Single Query:        User knows exactly what they want
Exploratory:         Multiple queries refining search
Comparison:          Searching same product across stores
Category Browsing:   Starting broad, narrowing down
```

---

## Reverse Engineering Techniques

### 1. **Analyze Real User Queries**

#### Collect Search Data
```python
# Example: Log and analyze user queries
class SearchAnalytics:
    def log_query(self, query: str, user_id: str, results_count: int, clicked_items: List[str]):
        """Log user search behavior"""
        search_log = {
            "query": query.lower().strip(),
            "user_id": user_id,
            "timestamp": datetime.now(),
            "results_count": results_count,
            "clicked_items": clicked_items,
            "query_length": len(query.split()),
            "has_brand": self._detect_brand(query),
            "has_category": self._detect_category(query),
            "has_attribute": self._detect_attribute(query)
        }
        # Store in analytics DB
        return search_log
    
    def analyze_patterns(self):
        """Analyze common patterns"""
        # Most common queries
        # Query length distribution
        # Brand mentions
        # Category searches
        # Attribute searches
        pass
```

#### Extract Patterns
```python
# Common patterns to detect:
patterns = {
    "brand_product": r"(\w+)\s+(\w+)",  # "Kellogg's cereal"
    "quantity_product": r"(\d+\s*\w+)\s+(\w+)",  # "12 pack eggs"
    "attribute_product": r"(organic|gluten-free|low-fat)\s+(\w+)",
    "category_only": ["dairy", "produce", "meat", "bakery"],
    "natural_language": r"i\s+(need|want|looking for)\s+(.+)"
}
```

### 2. **Reverse Engineer Competitor APIs**

#### Browser Network Analysis
```python
# Steps to reverse engineer:
# 1. Open browser DevTools → Network tab
# 2. Filter by Fetch/XHR
# 3. Perform searches on Target.com, Walmart.com, etc.
# 4. Analyze:
#    - Request URL
#    - Request method (GET/POST)
#    - Headers (Authorization, User-Agent, etc.)
#    - Query parameters
#    - Request body (if POST)
#    - Response structure
```

#### Example: Analyzing Target Search API
```python
# Observed pattern:
# GET https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v1
# Query params:
#   - key: API key
#   - channel: WEB
#   - count: 24
#   - default_purchasability_filter: true
#   - include_sponsored: true
#   - keyword: "milk"
#   - offset: 0
#   - page: /s/milk
#   - platform: desktop
#   - pricing_store_id: 1234
#   - useragent: Mozilla/5.0...
#   - visitor_id: ...

# Response structure:
# {
#   "data": {
#     "search": {
#       "products": [...],
#       "total_results": 1234
#     }
#   }
# }
```

#### Automated API Discovery
```python
import asyncio
from playwright.async_api import async_playwright

async def reverse_engineer_search_api(store_url: str, search_query: str):
    """Automatically capture API calls during search"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        
        api_calls = []
        
        # Intercept network requests
        async def handle_request(request):
            if 'search' in request.url.lower() or 'product' in request.url.lower():
                api_calls.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': request.headers,
                    'post_data': request.post_data
                })
        
        page.on('request', handle_request)
        
        # Navigate and search
        await page.goto(store_url)
        await page.fill('input[type="search"]', search_query)
        await page.press('input[type="search"]', 'Enter')
        await page.wait_for_load_state('networkidle')
        
        await browser.close()
        return api_calls
```

### 3. **Query Intent Classification**

```python
class QueryIntentClassifier:
    """Classify user intent from query"""
    
    INTENTS = {
        "PRODUCT_SEARCH": "Looking for specific product",
        "BRAND_SEARCH": "Looking for brand",
        "CATEGORY_BROWSE": "Browsing category",
        "ATTRIBUTE_FILTER": "Filtering by attribute",
        "COMPARISON": "Comparing products",
        "RECIPE_INGREDIENT": "Finding recipe ingredients"
    }
    
    def classify(self, query: str, context: Dict = None) -> str:
        """Classify query intent"""
        query_lower = query.lower()
        
        # Brand detection
        if self._has_brand(query_lower):
            return "BRAND_SEARCH"
        
        # Category detection
        if self._is_category(query_lower):
            return "CATEGORY_BROWSE"
        
        # Attribute detection
        if self._has_attribute(query_lower):
            return "ATTRIBUTE_FILTER"
        
        # Recipe context
        if context and context.get('recipe_mode'):
            return "RECIPE_INGREDIENT"
        
        # Default to product search
        return "PRODUCT_SEARCH"
    
    def _has_brand(self, query: str) -> bool:
        brands = ['kellogg', 'coca cola', 'pepsi', 'nestle', 'kraft']
        return any(brand in query for brand in brands)
    
    def _is_category(self, query: str) -> bool:
        categories = ['dairy', 'produce', 'meat', 'bakery', 'snacks', 'beverages']
        return query in categories
    
    def _has_attribute(self, query: str) -> bool:
        attributes = ['organic', 'gluten-free', 'low-fat', 'sugar-free', 'vegan']
        return any(attr in query for attr in attributes)
```

---

## Query Understanding & Intent Detection

### 1. **Query Normalization**

```python
class QueryNormalizer:
    """Normalize and enhance queries"""
    
    def normalize(self, query: str) -> Dict:
        """Normalize query for better search"""
        normalized = {
            "original": query,
            "cleaned": self._clean(query),
            "tokens": self._tokenize(query),
            "expanded": self._expand_synonyms(query),
            "corrected": self._spell_correct(query),
            "entities": self._extract_entities(query)
        }
        return normalized
    
    def _clean(self, query: str) -> str:
        """Remove noise"""
        # Remove common words
        stop_words = ['i', 'need', 'want', 'looking for', 'for', 'the', 'a', 'an']
        tokens = query.lower().split()
        cleaned = [t for t in tokens if t not in stop_words]
        return ' '.join(cleaned)
    
    def _expand_synonyms(self, query: str) -> List[str]:
        """Expand with synonyms"""
        synonyms = {
            'soda': ['pop', 'soft drink', 'carbonated beverage'],
            'milk': ['dairy milk', 'cow milk'],
            'eggs': ['chicken eggs', 'fresh eggs'],
            'bread': ['loaf', 'baked goods']
        }
        
        expansions = [query]
        for word, syns in synonyms.items():
            if word in query.lower():
                for syn in syns:
                    expansions.append(query.lower().replace(word, syn))
        
        return expansions
    
    def _extract_entities(self, query: str) -> Dict:
        """Extract structured entities"""
        return {
            "brand": self._extract_brand(query),
            "product": self._extract_product(query),
            "quantity": self._extract_quantity(query),
            "attributes": self._extract_attributes(query),
            "category": self._extract_category(query)
        }
```

### 2. **Context-Aware Query Rewriting**

```python
class ContextAwareRewriter:
    """Rewrite queries based on context and history"""
    
    def rewrite(self, query: str, user_history: List[str] = None, 
                session_context: Dict = None) -> str:
        """Rewrite query with context"""
        
        # 1. Disambiguate ambiguous terms
        if user_history:
            query = self._disambiguate(query, user_history)
        
        # 2. Add context from session
        if session_context:
            query = self._add_context(query, session_context)
        
        # 3. Expand with related terms
        query = self._expand_related(query)
        
        return query
    
    def _disambiguate(self, query: str, history: List[str]) -> str:
        """Use history to disambiguate"""
        # Example: "lemon" in history of "detergent" → "lemon detergent"
        # vs "lemon" in history of "fruit" → "lemon fruit"
        
        if 'lemon' in query.lower():
            if any('detergent' in h.lower() for h in history):
                return query.replace('lemon', 'lemon detergent')
            elif any('fruit' in h.lower() or 'produce' in h.lower() for h in history):
                return query.replace('lemon', 'lemon fruit')
        
        return query
    
    def _add_context(self, query: str, context: Dict) -> str:
        """Add contextual information"""
        # Add location context
        if context.get('zipcode'):
            # Already handled in main API
        
        # Add time context
        if context.get('time_of_day') == 'morning':
            if 'eggs' in query.lower():
                query = f"{query} breakfast"
        
        return query
```

### 3. **Semantic Search Enhancement**

```python
# Use embeddings for semantic understanding
class SemanticSearchEnhancer:
    """Enhance search with semantic understanding"""
    
    def __init__(self):
        # Use sentence transformers or OpenAI embeddings
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def find_similar_queries(self, query: str, query_db: List[str], top_k: int = 5):
        """Find similar historical queries"""
        query_embedding = self.model.encode(query)
        db_embeddings = self.model.encode(query_db)
        
        # Cosine similarity
        similarities = cosine_similarity([query_embedding], db_embeddings)[0]
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        return [query_db[i] for i in top_indices]
    
    def expand_query_semantically(self, query: str) -> List[str]:
        """Expand query with semantically similar terms"""
        # Use embeddings to find similar product names
        # Example: "milk" → ["dairy milk", "almond milk", "soy milk"]
        pass
```

---

## Universal Search Architecture

### 1. **Multi-Stage Search Pipeline**

```python
class UniversalGrocerySearch:
    """Universal grocery search with multiple stages"""
    
    async def search(self, query: str, filters: Dict = None) -> Dict:
        """Multi-stage search pipeline"""
        
        # Stage 1: Query Understanding
        query_analysis = self._analyze_query(query)
        
        # Stage 2: Intent Classification
        intent = self._classify_intent(query, query_analysis)
        
        # Stage 3: Query Rewriting
        rewritten_queries = self._rewrite_query(query, intent, query_analysis)
        
        # Stage 4: Multi-Source Search
        results = await self._multi_source_search(rewritten_queries, filters)
        
        # Stage 5: Result Ranking & Deduplication
        ranked_results = self._rank_and_deduplicate(results, query_analysis)
        
        # Stage 6: Personalization (if user context available)
        if filters and filters.get('user_id'):
            ranked_results = self._personalize(ranked_results, filters['user_id'])
        
        return {
            "query": query,
            "intent": intent,
            "rewritten_queries": rewritten_queries,
            "results": ranked_results,
            "total": len(ranked_results)
        }
    
    async def _multi_source_search(self, queries: List[str], filters: Dict) -> List[Dict]:
        """Search across multiple sources"""
        results = []
        
        # 1. Exa API (current approach - semantic search)
        exa_results = await self._search_exa(queries, filters)
        results.extend(exa_results)
        
        # 2. Direct store APIs (if available)
        store_results = await self._search_stores(queries, filters)
        results.extend(store_results)
        
        # 3. Category-based search
        category_results = await self._search_categories(queries, filters)
        results.extend(category_results)
        
        return results
    
    def _rank_and_deduplicate(self, results: List[Dict], query_analysis: Dict) -> List[Dict]:
        """Rank and deduplicate results"""
        # 1. Deduplicate by product URL/SKU
        unique_results = self._deduplicate(results)
        
        # 2. Score by relevance
        scored_results = self._score_relevance(unique_results, query_analysis)
        
        # 3. Sort by score
        ranked = sorted(scored_results, key=lambda x: x['relevance_score'], reverse=True)
        
        return ranked
    
    def _score_relevance(self, results: List[Dict], query_analysis: Dict) -> List[Dict]:
        """Score results by relevance"""
        for result in results:
            score = 0.0
            
            # Exact name match
            if query_analysis['cleaned'] in result['name'].lower():
                score += 10.0
            
            # Brand match
            if query_analysis['entities']['brand']:
                if query_analysis['entities']['brand'] in result.get('brand', '').lower():
                    score += 5.0
            
            # Category match
            if query_analysis['entities']['category']:
                if query_analysis['entities']['category'] in result.get('category', '').lower():
                    score += 3.0
            
            # Attribute match
            for attr in query_analysis['entities']['attributes']:
                if attr in result.get('description', '').lower():
                    score += 2.0
            
            # Price availability (prefer products with prices)
            if result.get('price'):
                score += 1.0
            
            # Image availability
            if result.get('image_url'):
                score += 0.5
            
            result['relevance_score'] = score
        
        return results
```

### 2. **Query Expansion Strategy**

```python
class QueryExpander:
    """Expand queries for better coverage"""
    
    def expand(self, query: str) -> List[str]:
        """Generate query variations"""
        expansions = []
        
        # Original query
        expansions.append(query)
        
        # 1. Synonym expansion
        expansions.extend(self._synonym_expansion(query))
        
        # 2. Plural/singular variations
        expansions.extend(self._plural_variations(query))
        
        # 3. Common misspellings
        expansions.extend(self._misspelling_variations(query))
        
        # 4. Brand variations
        expansions.extend(self._brand_variations(query))
        
        # 5. Category additions
        expansions.extend(self._category_additions(query))
        
        return list(set(expansions))  # Remove duplicates
    
    def _synonym_expansion(self, query: str) -> List[str]:
        """Expand with synonyms"""
        synonym_map = {
            'soda': ['pop', 'soft drink'],
            'milk': ['dairy'],
            'bread': ['loaf'],
            'eggs': ['chicken eggs']
        }
        
        expansions = []
        for word, syns in synonym_map.items():
            if word in query.lower():
                for syn in syns:
                    expansions.append(query.lower().replace(word, syn))
        
        return expansions
```

---

## Implementation Strategy

### Phase 1: Query Analysis & Logging

```python
# Add to your existing API
@app.post("/products/search")
async def search_products(
    query: str,
    zipcode: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Enhanced search with analytics"""
    
    # Log query for analysis
    await analytics.log_search({
        "query": query,
        "user_id": user_id,
        "session_id": session_id,
        "zipcode": zipcode,
        "timestamp": datetime.now()
    })
    
    # Analyze query
    query_analysis = query_analyzer.analyze(query)
    
    # Enhanced search with query understanding
    results = await enhanced_search(query, query_analysis, zipcode)
    
    return results
```

### Phase 2: Query Understanding Integration

```python
# Create query understanding service
class QueryUnderstandingService:
    """Service for understanding user queries"""
    
    def __init__(self):
        self.normalizer = QueryNormalizer()
        self.intent_classifier = QueryIntentClassifier()
        self.expander = QueryExpander()
    
    async def understand(self, query: str, context: Dict = None) -> Dict:
        """Understand query intent and structure"""
        return {
            "original": query,
            "normalized": self.normalizer.normalize(query),
            "intent": self.intent_classifier.classify(query, context),
            "expansions": self.expander.expand(query),
            "entities": self.normalizer._extract_entities(query)
        }
```

### Phase 3: Enhanced Search with Multiple Strategies

```python
class EnhancedGrocerySearch:
    """Enhanced search with multiple strategies"""
    
    async def search(self, query: str, zipcode: str = None) -> List[Dict]:
        """Search with multiple strategies"""
        
        # Understand query
        understanding = await query_service.understand(query)
        
        # Strategy 1: Exact match (fast, high precision)
        exact_results = await self._exact_match_search(understanding, zipcode)
        
        # Strategy 2: Semantic search (Exa API - current)
        semantic_results = await self._semantic_search(understanding, zipcode)
        
        # Strategy 3: Category-based (if category detected)
        if understanding['intent'] == 'CATEGORY_BROWSE':
            category_results = await self._category_search(understanding, zipcode)
        else:
            category_results = []
        
        # Strategy 4: Attribute-based (if attributes detected)
        if understanding['entities']['attributes']:
            attribute_results = await self._attribute_search(understanding, zipcode)
        else:
            attribute_results = []
        
        # Combine and rank
        all_results = exact_results + semantic_results + category_results + attribute_results
        ranked = self._rank_results(all_results, understanding)
        
        return ranked
```

---

## Advanced Techniques

### 1. **Learning from User Behavior**

```python
class UserBehaviorLearner:
    """Learn from user search patterns"""
    
    def analyze_user_patterns(self, user_id: str) -> Dict:
        """Analyze user's search patterns"""
        user_searches = await db.get_user_searches(user_id)
        
        patterns = {
            "favorite_brands": self._extract_favorite_brands(user_searches),
            "common_categories": self._extract_categories(user_searches),
            "search_times": self._analyze_search_times(user_searches),
            "query_length": self._analyze_query_length(user_searches),
            "click_through_rate": self._calculate_ctr(user_searches)
        }
        
        return patterns
    
    def personalize_search(self, query: str, user_patterns: Dict) -> str:
        """Personalize query based on user patterns"""
        # Add user's preferred brands if not specified
        if not self._has_brand(query) and user_patterns['favorite_brands']:
            # Don't modify, but boost results with favorite brands
        
        # Add user's common categories
        if not self._has_category(query) and user_patterns['common_categories']:
            # Boost category results
        
        return query
```

### 2. **A/B Testing Query Strategies**

```python
class QueryStrategyTester:
    """Test different query strategies"""
    
    STRATEGIES = {
        "baseline": "Original query as-is",
        "expanded": "Query with synonyms",
        "rewritten": "Context-aware rewritten",
        "semantic": "Semantic embeddings"
    }
    
    async def test_strategies(self, query: str, user_id: str) -> Dict:
        """Test multiple strategies and compare"""
        results = {}
        
        for strategy_name, strategy_func in self.STRATEGIES.items():
            start_time = time.time()
            strategy_results = await strategy_func(query)
            duration = time.time() - start_time
            
            results[strategy_name] = {
                "results": strategy_results,
                "count": len(strategy_results),
                "duration": duration,
                "relevance_score": self._calculate_relevance(strategy_results, query)
            }
        
        # Log for analysis
        await analytics.log_strategy_test(query, user_id, results)
        
        return results
```

### 3. **Real-Time Query Optimization**

```python
class RealTimeQueryOptimizer:
    """Optimize queries in real-time based on results"""
    
    async def optimize(self, query: str, initial_results: List[Dict]) -> str:
        """Optimize query if results are poor"""
        
        # Check result quality
        if len(initial_results) == 0:
            # No results - try expansion
            return self._expand_query(query)
        
        if len(initial_results) < 5:
            # Few results - try broader search
            return self._broaden_query(query)
        
        # Check relevance
        avg_relevance = sum(r.get('relevance_score', 0) for r in initial_results) / len(initial_results)
        if avg_relevance < 0.5:
            # Low relevance - try rewriting
            return self._rewrite_query(query)
        
        return query  # Query is good as-is
```

---

## Implementation Roadmap

### Week 1-2: Foundation
- [ ] Implement query logging and analytics
- [ ] Build query normalizer
- [ ] Create intent classifier
- [ ] Set up analytics database

### Week 3-4: Query Understanding
- [ ] Implement query expansion
- [ ] Add synonym handling
- [ ] Build entity extraction
- [ ] Create context-aware rewriting

### Week 5-6: Enhanced Search
- [ ] Integrate multiple search strategies
- [ ] Implement result ranking
- [ ] Add deduplication
- [ ] Build A/B testing framework

### Week 7-8: Personalization
- [ ] User behavior analysis
- [ ] Personalization engine
- [ ] Real-time optimization
- [ ] Performance tuning

---

## Key Metrics to Track

```python
metrics = {
    "search_quality": {
        "zero_result_rate": "Percentage of searches with no results",
        "avg_results_per_query": "Average number of results",
        "click_through_rate": "Percentage of results clicked",
        "conversion_rate": "Searches leading to product views"
    },
    "query_understanding": {
        "intent_accuracy": "How well we classify intent",
        "entity_extraction_accuracy": "Entity detection accuracy",
        "query_expansion_effectiveness": "Impact of expansion on results"
    },
    "performance": {
        "avg_response_time": "Average API response time",
        "p95_response_time": "95th percentile response time",
        "cache_hit_rate": "Percentage of cached responses"
    }
}
```

---

## Best Practices

### 1. **Query Handling**
- ✅ Normalize queries (lowercase, trim, remove noise)
- ✅ Handle misspellings gracefully
- ✅ Support synonyms and variations
- ✅ Preserve user intent

### 2. **Result Quality**
- ✅ Rank by relevance, not just keyword match
- ✅ Deduplicate across sources
- ✅ Provide diverse results
- ✅ Include prices when available

### 3. **Performance**
- ✅ Cache common queries
- ✅ Use async processing
- ✅ Implement rate limiting
- ✅ Monitor and optimize slow queries

### 4. **User Experience**
- ✅ Fast response times (< 2 seconds)
- ✅ Clear error messages
- ✅ Support for natural language
- ✅ Context-aware results

---

## Example: Complete Universal Search Implementation

```python
class UniversalGrocerySearchAPI:
    """Complete universal grocery search implementation"""
    
    def __init__(self):
        self.query_service = QueryUnderstandingService()
        self.exa_client = ExaStructuredClient()
        self.analytics = SearchAnalytics()
        self.cache = Cache()
    
    async def universal_search(
        self,
        query: str,
        zipcode: str = None,
        user_id: str = None,
        filters: Dict = None
    ) -> Dict:
        """Universal search that handles any query type"""
        
        # 1. Understand query
        understanding = await self.query_service.understand(query, {
            "user_id": user_id,
            "zipcode": zipcode
        })
        
        # 2. Check cache
        cache_key = self._generate_cache_key(understanding, zipcode, filters)
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 3. Multi-strategy search
        results = await self._multi_strategy_search(understanding, zipcode, filters)
        
        # 4. Rank and personalize
        ranked_results = self._rank_results(results, understanding, user_id)
        
        # 5. Format response
        response = {
            "query": query,
            "understood_as": understanding,
            "results": ranked_results,
            "total": len(ranked_results),
            "search_strategy": understanding['intent']
        }
        
        # 6. Cache and return
        await self.cache.set(cache_key, response, ttl=3600)
        await self.analytics.log_search(query, user_id, len(ranked_results))
        
        return response
```

---

## Next Steps

1. **Start with Analytics**: Implement query logging to understand real user behavior
2. **Build Query Understanding**: Create the normalizer and intent classifier
3. **Enhance Current Search**: Integrate query understanding into existing Exa-based search
4. **Add Personalization**: Once you have user data, add personalization
5. **Iterate**: Use analytics to continuously improve

This approach will help you build a truly universal grocery search API that understands user intent and provides optimal results!


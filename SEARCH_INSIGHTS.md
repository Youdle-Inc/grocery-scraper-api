# Perplexity-Style Search Insights

## 🎯 New Features

Added Perplexity-like search insights to the `/products/aggregate` endpoint:

1. **Overview** - Natural language summary of search results
2. **Follow-up Queries** - Suggested related searches

## 📊 Response Structure

The aggregate endpoint now includes:

```json
{
  "query": "eggs",
  "zipcode": "60601",
  "search_timestamp": "2025-11-10T18:29:37.121176Z",
  "results": [...],
  "stores_considered": ["target", "walmart", "whole_foods", "kroger", "aldi"],
  "overview": "Found 10 products for 'eggs' across 5 stores ranging from $3.99 to $5.99 including brands like Target, Walmart in categories: Dairy & Eggs, Eggs near 60601.",
  "follow_up_queries": [
    "milk",
    "butter",
    "Target eggs",
    "organic eggs",
    "cheapest eggs",
    "best deals on eggs"
  ],
  "meta": {
    "api_version": "2.1.0",
    "cache": {"hit": false}
  }
}
```

## 🔍 Overview Generation

The overview includes:
- **Product count** - How many products were found
- **Store count** - How many stores had results
- **Price range** - Min/max prices found
- **Brands** - Top brands discovered
- **Categories** - Product categories found
- **Location** - ZIP code searched

**Example:**
```
Found 10 products for 'eggs' across 5 stores ranging from $3.99 to $5.99 including brands like Target, Walmart in categories: Dairy & Eggs, Eggs near 60601.
```

## 💡 Follow-up Query Suggestions

Generated based on:
1. **Related categories** - Products in similar categories
2. **Brand-specific** - Same product from different brands
3. **Attribute variations** - Organic, gluten-free, etc.
4. **Semantic relationships** - Related products (eggs → milk, bread → butter)
5. **Store-specific** - Same product at specific stores
6. **Price-focused** - "cheapest X", "best deals on X"

**Example:**
```json
[
  "milk",
  "butter", 
  "Target eggs",
  "organic eggs",
  "cheapest eggs",
  "best deals on eggs"
]
```

## 🚀 Usage

Just call the aggregate endpoint as normal - insights are automatically included:

```bash
curl "http://localhost:8000/products/aggregate?query=eggs&zipcode=60601"
```

The response will automatically include:
- `overview` - Summary text
- `follow_up_queries` - Array of suggested queries

## 🎨 UI Integration Ideas

**Overview Display:**
- Show at the top of results
- Highlight key stats (price range, store count)
- Use as a quick summary before showing products

**Follow-up Queries:**
- Display as clickable chips/buttons
- Allow users to quickly refine their search
- Show as "People also search for" section
- Enable one-click search refinement

## 📝 Example Response

```json
{
  "query": "milk",
  "zipcode": "60601",
  "overview": "Found 15 products for 'milk' across 5 stores ranging from $2.99 to $6.49 including brands like Target, Walmart, Horizon in categories: Dairy & Eggs, Milk near 60601.",
  "follow_up_queries": [
    "eggs",
    "butter",
    "Horizon milk",
    "organic milk",
    "cheapest milk",
    "milk at Target"
  ],
  "results": [...]
}
```

## 🔧 Technical Details

- **Service:** `SearchInsightsGenerator`
- **Location:** `scraper/search_insights.py`
- **Methods:**
  - `generate_overview()` - Creates summary text
  - `generate_follow_up_queries()` - Generates suggestions
- **Performance:** Fast, no external API calls needed
- **Caching:** Insights are cached with search results

## ✨ Benefits

✅ **Better UX** - Users understand results at a glance  
✅ **Discovery** - Helps users find related products  
✅ **Engagement** - Encourages further exploration  
✅ **Perplexity-like** - Familiar search experience  
✅ **Automatic** - No extra API calls needed  


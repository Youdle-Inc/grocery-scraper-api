# Streaming API Endpoint - Real-time Results

## 🚀 New Streaming Endpoint

**Endpoint:** `/products/aggregate/stream`

Returns results **as soon as each store completes** instead of waiting for all stores!

## How It Works

Uses **Server-Sent Events (SSE)** to stream results incrementally:
- Results arrive as each store completes (seconds, not minutes!)
- Perfect for web apps - update UI in real-time
- Shows progress as stores complete

## JavaScript Usage

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/products/aggregate/stream?query=eggs&zipcode=60601&stores=target,walmart'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'start':
      console.log('Starting search...', data.stores);
      break;
      
    case 'store_complete':
      console.log(`✅ ${data.store_name} completed!`);
      console.log(`Found ${data.count} products`);
      console.log('Progress:', `${data.progress.completed}/${data.progress.total}`);
      
      // Update your UI here!
      displayProducts(data.store_name, data.products);
      break;
      
    case 'store_error':
      console.error('Store error:', data.error);
      break;
      
    case 'done':
      console.log('🎉 All stores complete!');
      eventSource.close();
      break;
      
    case 'error':
      console.error('Error:', data.message);
      eventSource.close();
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

## React Example

```jsx
import { useEffect, useState } from 'react';

function ProductSearch({ query, zipcode, stores }) {
  const [results, setResults] = useState({});
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  
  useEffect(() => {
    const eventSource = new EventSource(
      `/products/aggregate/stream?query=${query}&zipcode=${zipcode}&stores=${stores}`
    );
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'store_complete') {
        setResults(prev => ({
          ...prev,
          [data.store_id]: data.products
        }));
        setProgress({
          completed: data.progress.completed,
          total: data.progress.total
        });
      } else if (data.type === 'done') {
        eventSource.close();
      }
    };
    
    return () => eventSource.close();
  }, [query, zipcode, stores]);
  
  return (
    <div>
      <div>Progress: {progress.completed}/{progress.total}</div>
      {Object.entries(results).map(([storeId, products]) => (
        <div key={storeId}>
          <h3>{storeId}</h3>
          {products.map(product => (
            <div key={product.product_url}>{product.name}</div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

## cURL Testing

```bash
# Test streaming endpoint
curl -N "http://localhost:8000/products/aggregate/stream?query=eggs&zipcode=60601&stores=target,walmart"

# You'll see results streaming in as each store completes!
```

## Event Types

1. **`start`** - Search started
   ```json
   {"type": "start", "query": "eggs", "zipcode": "60601", "stores": ["target", "walmart"]}
   ```

2. **`store_complete`** - Store finished searching
   ```json
   {
     "type": "store_complete",
     "store_id": "target",
     "store_name": "Target",
     "products": [...],
     "count": 10,
     "progress": {"completed": 1, "total": 2}
   }
   ```

3. **`store_error`** - Store failed
   ```json
   {
     "type": "store_error",
     "error": "Error message",
     "progress": {"completed": 1, "total": 2}
   }
   ```

4. **`done`** - All stores complete
   ```json
   {
     "type": "done",
     "total_stores": 2,
     "completed_stores": 2
   }
   ```

5. **`error`** - Fatal error
   ```json
   {"type": "error", "message": "Error message"}
   ```

## Benefits

✅ **Fast First Results** - See products in seconds, not minutes  
✅ **Real-time Updates** - UI updates as stores complete  
✅ **Progress Tracking** - Show users how many stores are done  
✅ **Better UX** - No more waiting for slow stores  
✅ **Same Data** - Same product data as regular endpoint  

## Parameters

- `query` (required) - Product to search for
- `zipcode` (required) - 5-digit ZIP code
- `stores` (optional) - Comma-separated store IDs
- `limit` (optional) - Products per store (default: 10)
- `refresh` (optional) - Bypass cache (default: false)

## Comparison

**Regular Endpoint** (`/products/aggregate`):
- Waits for ALL stores to complete
- Returns everything at once
- ~60 seconds wait time

**Streaming Endpoint** (`/products/aggregate/stream`):
- Returns results as each store completes
- First results in ~5-10 seconds
- Updates continuously

## Use Cases

- **Web Apps** - Show results immediately
- **Real-time Dashboards** - Live product updates
- **Progressive Loading** - Better perceived performance
- **Multi-store Comparison** - See best deals first


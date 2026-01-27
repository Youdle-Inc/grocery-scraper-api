# Running Grocery Scraper API Locally

## Quick Start

```bash
# Install dependencies (first time only)
pip install -r requirements.txt

# Run the API locally with auto-reload
uvicorn main:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

Make sure you have a `.env` file with required API keys:

```bash
# Required for Exa search functionality
EXA_API_KEY=your_exa_api_key_here

# Optional: Google API keys for geocoding/places
GOOGLE_MAPS_API_KEY=your_google_maps_key
GOOGLE_GEOCODING_API_KEY=your_geocoding_key
GOOGLE_PLACES_API_KEY=your_places_key

# Partner APIs (optional)
WALMART_CLIENT_ID=your_walmart_client_id
WALMART_CLIENT_SECRET=your_walmart_client_secret
KROGER_CLIENT_ID=your_kroger_client_id
KROGER_CLIENT_SECRET=your_kroger_client_secret
TARGET_API_KEY=your_target_api_key
```

## Test Endpoints

### Check if API is running
```bash
curl http://localhost:8000/
```

### Test store availability for Memphis (38125)
```bash
curl "http://localhost:8000/products/aggregate?query=milk&zipcode=38125&limit=5"
```

### Check which stores are available in Memphis
```bash
curl "http://localhost:8000/products/aggregate?query=test&zipcode=38125&limit=1" | jq '.meta.stores_available'
```

Expected output should include `cash_saver`:
```json
[
  "walmart",
  "target",
  "aldi",
  "kroger",
  "marianos",
  "costco",
  "whole_foods",
  "sams_club",
  "trader_joes",
  "safeway",
  "albertsons",
  "publix",
  "heb",
  "giant_eagle",
  "meijer",
  "hy_vee",
  "sprouts",
  "cash_saver"
]
```

## Development Mode

The `--reload` flag enables auto-reload when you make code changes:

```bash
uvicorn main:app --reload --port 8000
```

Changes to Python files will automatically restart the server.

## Stopping the Server

Press `Ctrl+C` in the terminal running uvicorn.

Or if running in background:
```bash
# Find the process
lsof -ti:8000

# Kill it
lsof -ti:8000 | xargs kill -9
```

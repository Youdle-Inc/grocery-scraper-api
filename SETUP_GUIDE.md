# 🚀 Setup Guide

Complete guide to setting up and running the Grocery Scraper API locally.

## Prerequisites

- **Python 3.8+** (Python 3.9+ recommended)
- **pip** (Python package manager)
- **Git** (for cloning the repository)
- **API Keys**:
  - Serper API key (required)
  - OpenAI API key (optional, for AI features)
  - Anthropic API key (optional, alternative to OpenAI)

## Step 1: Clone the Repository

```bash
git clone https://github.com/Youdle-Inc/grocery-scraper-api.git
cd grocery-scraper-api
```

## Step 2: Create Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

## Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...
```

## Step 4: Get API Keys

### Serper API Key (Required)

1. Go to [serper.dev](https://serper.dev)
2. Sign up for an account
3. Navigate to the API dashboard
4. Copy your API key

### OpenAI API Key (Optional)

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (you won't be able to see it again!)

### Anthropic API Key (Optional)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key

## Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```bash
touch .env  # On macOS/Linux
# or
type nul > .env  # On Windows
```

Add your API keys to `.env`:

```bash
# Required: Serper API Key (Google Search API)
SERPER_API_KEY=your_serper_api_key_here

# Optional: OpenAI API Key (for AI product validation and enrichment)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Anthropic API Key (alternative to OpenAI)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Environment setting
ENVIRONMENT=development
```

**Important:**
- Never commit `.env` to version control
- The `.env` file is already in `.gitignore`
- Replace `your_*_api_key_here` with your actual keys

## Step 6: Verify Installation

Check that all dependencies are installed:

```bash
python -c "import fastapi, uvicorn, aiohttp; print('✅ All dependencies installed')"
```

## Step 7: Run the API Server

**Development mode (with auto-reload):**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Production mode:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Step 8: Test the API

Open a new terminal window and test the health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.000000",
  "version": "3.0.0",
  "services": {
    "serper_api": "available"
  }
}
```

## Step 9: Access API Documentation

Open your browser and navigate to:

- **Swagger UI**: http://localhost:8000/swagger
- **ReDoc**: http://localhost:8000/ (root endpoint)

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: `SERPER_API_KEY not found`

**Solution:**
1. Check that `.env` file exists in project root
2. Verify API key is set correctly:
   ```bash
   cat .env | grep SERPER_API_KEY
   ```
3. Make sure `.env` file is in the same directory as `main.py`

### Issue: `Address already in use` (port 8000)

**Solution:**
Use a different port:
```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Then access at `http://localhost:8001`

### Issue: API returns errors or empty results

**Solution:**
1. Check API key is valid:
   ```bash
   curl "https://google.serper.dev/search?q=test" \
     -H "X-API-KEY: your_serper_api_key"
   ```

2. Check server logs for error messages
3. Verify ZIP code format (must be 5 digits)
4. Check Serper API quota/limits

### Issue: Slow response times

**Solution:**
1. Check your internet connection
2. Verify Serper API is responding:
   ```bash
   curl -w "@-" -o /dev/null -s "https://google.serper.dev/search?q=test" \
     -H "X-API-KEY: your_serper_api_key" <<< "time_total: %{time_total}\n"
   ```
3. Use caching (don't set `refresh=true` unless needed)
4. Reduce `limit` parameter for faster responses

## Running Tests

Run the automated test suite:

```bash
./test_localhost.sh
```

Or test individual endpoints (see [TEST_LOCALHOST.md](./TEST_LOCALHOST.md))

## Development Tips

### Hot Reload

The `--reload` flag enables automatic reloading when code changes:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Debug Logging

Enable debug logging by setting log level:
```python
# In main.py, change:
logging.basicConfig(level=logging.DEBUG)
```

### Environment Variables

You can also set environment variables directly:
```bash
export SERPER_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Next Steps

1. **Read the API Documentation**: See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
2. **Test the Endpoints**: See [TEST_LOCALHOST.md](./TEST_LOCALHOST.md)
3. **Understand the Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md)
4. **Start Building**: Integrate the API into your application!

## Production Deployment

For production deployment (e.g., Vercel, Heroku, AWS):

1. Set environment variables in your hosting platform
2. Use production-grade WSGI server (e.g., Gunicorn)
3. Enable HTTPS
4. Set up monitoring and logging
5. Configure rate limiting
6. Set up error tracking

See deployment-specific documentation for your platform.

## Support

If you encounter issues:
1. Check this guide first
2. Review [README.md](./README.md)
3. Check server logs for error messages
4. Create an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Python version)

---

**Happy coding! 🚀**


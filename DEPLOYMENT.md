# Deployment Guide

## Quick Deploy to Render.com (Recommended)

### Step 1: Push to GitHub

```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit: Grocery Scraper API"

# Push to GitHub (create repo first on github.com)
git remote add origin https://github.com/yourusername/grocery-scraper-api.git
git push -u origin main
```

### Step 2: Deploy on Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select your `grocery-scraper-api` repository
5. Configure:
   - **Name**: `grocery-scraper-api`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free (or paid for better performance)

6. Click **"Create Web Service"**

### Step 3: Get Your Live URL

After deployment (2-3 minutes), you'll get a URL like:
```
https://grocery-scraper-api.onrender.com
```

### Step 4: Test Your Live API

```bash
# Health check
curl https://grocery-scraper-api.onrender.com/health

# Test scraping
curl "https://grocery-scraper-api.onrender.com/scrape?query=milk&store=gianteagle&zipcode=15213"

# View documentation
# Visit: https://grocery-scraper-api.onrender.com/docs
```

## Alternative Deployment Options

### Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Heroku

```bash
# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create grocery-scraper-api
git push heroku main
```

### DigitalOcean App Platform

1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set run command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Docker Deployment

```bash
# Build image
docker build -t grocery-scraper-api .

# Run locally
docker run -p 8000:8000 grocery-scraper-api

# Deploy to any Docker hosting service
```

## Environment Variables for Production

Set these in your deployment platform:

- `PORT` - Server port (usually set automatically)
- `ENVIRONMENT` - Set to "production"
- `LOG_LEVEL` - Set to "info"

## Performance Considerations

### Free Tier Limitations
- **Render Free**: 750 hours/month, sleeps after 15min inactivity
- **Railway Free**: 500 hours/month
- **Heroku**: No free tier anymore

### Paid Recommendations
- **Render**: $7/month for always-on service
- **Railway**: $5/month for hobby plan
- **DigitalOcean**: $5/month for basic droplet

### Optimization Tips
1. **Caching**: Add Redis for frequently requested products
2. **Rate Limiting**: Prevent abuse with rate limiting
3. **Monitoring**: Set up health checks and alerts
4. **Scaling**: Use multiple instances for high traffic

## Monitoring Your API

### Health Checks
```bash
# Check if API is responding
curl https://your-api-url.com/health
```

### Logs
- **Render**: View logs in dashboard
- **Railway**: `railway logs`
- **Heroku**: `heroku logs --tail`

### Metrics to Monitor
- Response times
- Success/error rates
- Memory usage
- Scraping success rates per store

## Troubleshooting

### Common Issues

1. **Chrome not found**
   - Ensure Dockerfile installs Chrome correctly
   - Check Chrome binary path in logs

2. **Selenium timeouts**
   - Increase timeout values in config
   - Check if stores have anti-bot measures

3. **Memory issues**
   - Upgrade to paid tier with more RAM
   - Optimize Chrome options for lower memory usage

4. **Rate limiting**
   - Add delays between requests
   - Implement request queuing

### Debug Mode

For debugging, set environment variable:
```bash
DEBUG=true
```

This will:
- Enable verbose logging
- Show browser windows (if possible)
- Add detailed error messages

## Security Considerations

1. **CORS**: Configure allowed origins for production
2. **Rate Limiting**: Implement to prevent abuse
3. **Authentication**: Add API keys if needed
4. **HTTPS**: Ensure SSL certificates are configured
5. **Input Validation**: Already handled by Pydantic models

## Scaling

### Horizontal Scaling
- Deploy multiple instances
- Use load balancer
- Implement request queuing

### Vertical Scaling
- Upgrade to higher memory/CPU instances
- Optimize Chrome settings
- Use faster storage

### Caching Strategy
```python
# Example Redis caching
import redis
r = redis.Redis()

# Cache results for 1 hour
cache_key = f"scrape:{store}:{query}:{zipcode}"
cached_result = r.get(cache_key)
if cached_result:
    return json.loads(cached_result)

# Store result in cache
r.setex(cache_key, 3600, json.dumps(result))
```

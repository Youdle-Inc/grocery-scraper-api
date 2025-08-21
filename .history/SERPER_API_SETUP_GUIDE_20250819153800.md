# 🔑 SerpWow API Setup Guide

## 🚨 Current Issue
Your current API key `80ff8a83e123e4ae68792aef4a946ee7335bd8ca` is returning "not valid" errors.

## 🔧 How to Fix Your SerpWow API Key

### Step 1: Check Your SerpWow Account
1. Go to https://serpwow.com/
2. Sign in to your account
3. Check your account status and credits

### Step 2: Verify Your API Key
1. In your SerpWow dashboard, go to "API Keys" section
2. Copy your current API key
3. Make sure it's the correct key (should be different from the invalid one)

### Step 3: Test Your API Key
Test your new API key with this command:
```bash
curl -s "https://api.serpwow.com/live/search?api_key=YOUR_NEW_API_KEY&engine=google&search_type=shopping&q=milk&gl=us&hl=en&num=1" | python -m json.tool
```

### Step 4: Update Your .env File
Replace the old API key in your `.env` file:
```bash
# Edit .env file
SERPER_API_KEY=your_new_api_key_here
```

### Step 5: Restart the Server
```bash
pkill -f uvicorn
source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 &
```

## 🆘 Common Issues & Solutions

### Issue 1: "Supplied api_key is not valid"
**Solutions:**
- Regenerate your API key in the SerpWow dashboard
- Check if your account is active
- Verify you have credits available

### Issue 2: "No credits available"
**Solutions:**
- Purchase credits or upgrade your plan
- Check if you're on the free tier (limited searches)

### Issue 3: "Account suspended"
**Solutions:**
- Contact SerpWow support
- Check your usage limits

## 🧪 Test Your Setup

Once you have a working API key, test it:

```bash
# Test the API directly
curl -s "https://api.serpwow.com/live/search?api_key=YOUR_KEY&engine=google&search_type=shopping&q=milk&gl=us&hl=en&num=1" | python -m json.tool

# Test the integration
curl -s "http://localhost:8000/sonar/products/search?query=milk&store_name=Target&location=Chicago,IL" | python -m json.tool | grep -A 5 -B 5 "product_url"
```

## ✅ Success Indicators

When working correctly, you should see:
- ✅ Real product URLs like `https://www.target.com/p/product-name/-/A-12345678`
- ✅ Real image URLs from Target's CDN
- ✅ No "demo mode" messages in logs
- ✅ No "Invalid API key" errors

## 📞 Need Help?

If you're still having issues:
1. Check SerpWow's documentation: https://docs.trajectdata.com/serpwow/
2. Contact SerpWow support
3. Try regenerating your API key
4. Verify your account has credits for Google Shopping searches

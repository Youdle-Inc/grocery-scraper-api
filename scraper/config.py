"""
Store configurations for the Grocery Scraper
"""

# Store configurations with working selectors and URLs
SUPPORTED_STORES = {
    "gianteagle": {
        "name": "Giant Eagle",
        "status": "✅ Working (11 products found in tests)",
        "description": "Regional grocery chain in Pennsylvania, Ohio, West Virginia, Indiana, and Maryland",
        "base_url": "https://www.gianteagle.com/grocery/search?q={query}",
        "selectors": {
            "products": [
                ".ProductTile",
                "[data-test-id='ProductTile']",
                ".sc-jRKRTY",
                "[class*='ProductTile']"
            ],
            "title": [
                "[data-test-id='ProductTile_title']",
                ".sc-kNVpPD",
                "h3",
                ".product-title"
            ],
            "price": [
                ".sc-MWeOf",
                ".sc-hjfSN",
                ".price",
                "[class*='price']"
            ],
            "image": [
                ".ProductImage_image",
                ".sc-jIiDBi",
                "img[data-test-id]",
                "img"
            ]
        }
    },
    "wegmans": {
        "name": "Wegmans",
        "status": "✅ Working (6 products found in tests)",
        "description": "Regional grocery chain primarily in New York, Pennsylvania, New Jersey, Virginia, Maryland, Massachusetts, and North Carolina",
        "base_url": "https://www.wegmans.com/shop/search?query={query}",
        "selectors": {
            "products": [
                ".product-tile",
                ".product-card",
                "[data-testid='product-card']",
                "[class*='product']"
            ],
            "title": [
                ".product-title",
                ".product-name",
                "[data-testid='product-title']",
                "h3",
                "h4"
            ],
            "price": [
                ".product-price",
                ".price",
                "[data-testid='price']",
                "[class*='price']"
            ],
            "image": [
                ".product-image img",
                ".product-tile img",
                "img"
            ]
        }
    },
    "aldi": {
        "name": "ALDI",
        "status": "✅ Working (15 products found in tests)",
        "description": "German-owned discount grocery chain with locations across the United States",
        "base_url": "https://www.aldi.us/en/products/?text={query}",
        "selectors": {
            "products": [
                ".box--wrapper",
                ".product-tile",
                "[class*='product']"
            ],
            "title": [
                ".box--description",
                ".product-title",
                "h3",
                "h4"
            ],
            "price": [
                ".box--price",
                ".price",
                "[class*='price']"
            ],
            "image": [
                ".box--image img",
                "img"
            ]
        }
    },
    "albertsons": {
        "name": "Albertsons",
        "status": "⚠️ Limited results",
        "description": "American grocery company with stores across the United States",
        "base_url": "https://www.albertsons.com/shop/search-results.html?q={query}&tab=products",
        "selectors": {
            "products": [
                ".product-card-container",
                ".product-item",
                ".product-card",
                "[class*='product']"
            ],
            "title": [
                ".product-title",
                ".product-name",
                "h3",
                "h4"
            ],
            "price": [
                ".product-price",
                ".price",
                "[class*='price']"
            ],
            "image": [
                ".product-card__image-container img",
                ".product-image img",
                "img"
            ]
        }
    },
    "shoprite": {
        "name": "ShopRite",
        "status": "⚠️ Limited results",
        "description": "Supermarket chain in the northeastern United States",
        "base_url": "https://www.shoprite.com/sm/pickup/rsid/3000/search?q={query}",
        "selectors": {
            "products": [
                ".product-card",
                ".product-item",
                "[data-testid*='product']",
                ".grid-card",
                "[class*='product']"
            ],
            "title": [
                ".product-title",
                ".product-name",
                "h3",
                "h4",
                "[data-testid*='title']"
            ],
            "price": [
                ".product-price",
                ".price",
                "[class*='price']",
                "[data-testid*='price']"
            ],
            "image": [
                ".product-image img",
                "img"
            ]
        }
    }
}

# Scraper settings
SCRAPER_CONFIG = {
    "timeout": 30,
    "headless": True,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "implicit_wait": 10,
    "page_load_timeout": 30
}

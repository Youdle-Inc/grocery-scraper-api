"""
Walmart Affiliate API Client for product search
"""
import os
import logging
import aiohttp
import hashlib
import hmac
import time
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urlencode
try:
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Signature import pkcs1_15
    from Cryptodome.Hash import SHA256
except ImportError:
    # Fallback to Crypto if Cryptodome not available
    from Crypto.PublicKey import RSA
    from Crypto.Signature import pkcs1_15
    from Crypto.Hash import SHA256
import base64

logger = logging.getLogger(__name__)

class WalmartAPIClient:
    """Client for Walmart Affiliate API"""
    
    BASE_URL = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2"
    
    def __init__(self):
        """Initialize Walmart API client"""
        # Support both WALMART_CONSUMER_ID and consumerId (from TypeScript)
        self.consumer_id = os.getenv("WALMART_CONSUMER_ID") or os.getenv("consumerId")
        # Affiliate ID for product URL replacement (default matches frontend: 3752911)
        self.affiliate_id = os.getenv("WALMART_AFFILIATE_ID", "3752911")
        # Private key from environment - REQUIRED for Walmart API
        # Handle multi-line keys in .env file
        private_key_pem = self._read_multiline_env_var("WALMART_PRIVATE_KEY")
        
        if not private_key_pem:
            logger.info("ℹ️ WALMART_PRIVATE_KEY not set. Walmart partner API will be unavailable (will use Exa fallback).")
            self.private_key = None
        else:
            try:
                # Handle newlines - convert \n to actual newlines if needed
                if "\\n" in private_key_pem:
                    private_key_pem = private_key_pem.replace("\\n", "\n")
                
                # If key doesn't have PEM headers, assume it's just the base64 content
                if not private_key_pem.strip().startswith("-----BEGIN"):
                    # Check if key seems too short (RSA keys should be hundreds of characters)
                    key_length = len(private_key_pem.strip())
                    if key_length < 500:
                        logger.error(f"Walmart private key appears too short ({key_length} chars). RSA private keys are typically 1500+ characters.")
                        logger.error("Make sure you copied the ENTIRE key from Walmart Developer Portal.")
                        logger.error("If the key has newlines, you may need to use \\n in your .env file or put it in quotes.")
                        self.private_key = None
                        return
                    
                    logger.info("ℹ️ Walmart private key appears to be base64 only, adding PEM headers...")
                    # Try PKCS#8 format first (what Walmart guide generates), then fall back to PKCS#1
                    private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_pem.strip()}\n-----END PRIVATE KEY-----"
                
                # RSA.import_key handles both PKCS#1 (BEGIN RSA PRIVATE KEY) and PKCS#8 (BEGIN PRIVATE KEY)
                self.private_key = RSA.import_key(private_key_pem)
                logger.info("✅ Walmart private key loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Walmart private key: {e}")
                logger.error("Common issues:")
                logger.error("  1. Key is truncated - make sure you copied the ENTIRE key")
                logger.error("  2. Key has newlines - use \\n in .env or wrap in quotes")
                logger.error("  3. Key format is wrong - should be PEM format or base64")
                self.private_key = None
        
        self.key_version = 2  # Match frontend implementation (keyVer: 2)
    
    def _read_multiline_env_var(self, var_name: str) -> Optional[str]:
        """Read environment variable that may span multiple lines in .env file"""
        # First try standard os.getenv
        value = os.getenv(var_name)
        if value and len(value) > 500:  # If it's long enough, probably complete
            return value
        
        # Try reading from .env file directly to handle multi-line values
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                    in_var = False
                    var_lines = []
                    for line in lines:
                        stripped = line.strip()
                        if stripped.startswith(f"{var_name}=") or stripped.startswith(f"{var_name} ="):
                            # Found the variable
                            in_var = True
                            # Extract value after =
                            if "=" in line:
                                value_part = line.split("=", 1)[1].strip()
                                if value_part:
                                    var_lines.append(value_part)
                        elif in_var:
                            # Check if this is a continuation line
                            if stripped and not stripped.startswith("#") and "=" not in stripped:
                                # Continuation line (no = sign, not a comment)
                                var_lines.append(stripped)
                            elif stripped.startswith(f"{var_name}") or (stripped and "=" in stripped and not stripped.startswith("#")):
                                # New variable, stop reading
                                break
                            elif not stripped:
                                # Empty line might be part of multi-line value
                                continue
                            else:
                                # Something else, stop
                                break
                    
                    if var_lines:
                        # Join all lines
                        full_value = "".join(var_lines)
                        # Remove quotes if present
                        if full_value.startswith('"') and full_value.endswith('"'):
                            full_value = full_value[1:-1]
                        if full_value.startswith("'") and full_value.endswith("'"):
                            full_value = full_value[1:-1]
                        return full_value
        except Exception as e:
            logger.debug(f"Could not read multi-line env var: {e}")
        
        return value
    
    def is_available(self) -> bool:
        """Check if Walmart API is available"""
        return self.consumer_id is not None and self.private_key is not None
    
    def _generate_signature(self, timestamp: str) -> str:
        """Generate RSA signature for Walmart API authentication
        Note: Walmart signature does NOT include the URL, only consumer_id, timestamp, and key_version
        Matches NodeRSA implementation which signs the raw string directly (not a hash)
        """
        if not self.private_key:
            return ""
        
        # Create string to sign: consumer_id + timestamp + key_version (NO URL!)
        # This matches the TypeScript implementation exactly
        string_to_sign = f"{self.consumer_id}\n{timestamp}\n{self.key_version}\n"
        
        # NodeRSA signs the raw string directly (not a hash)
        # However, Python's RSA signing requires hashing first for security
        # We use SHA256 hash then sign with PKCS1v15 padding (standard RSA signing)
        h = SHA256.new(string_to_sign.encode())
        signature = pkcs1_15.new(self.private_key).sign(h)
        
        # Base64 encode
        return base64.b64encode(signature).decode()
    
    def _get_headers(self, url: str) -> Dict[str, str]:
        """Get headers with signature for Walmart API"""
        if not self.is_available():
            return {}
        
        timestamp = str(int(time.time() * 1000))  # Milliseconds
        signature = self._generate_signature(timestamp)  # Note: signature doesn't include URL
        
        return {
            "WM_CONSUMER.ID": self.consumer_id,
            "WM_CONSUMER.INTIMESTAMP": timestamp,
            "WM_SEC.AUTH_SIGNATURE": signature,
            "WM_SEC.KEY_VERSION": str(self.key_version)
        }
    
    async def search_products(
        self,
        query: str,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Search for products on Walmart.com"""
        if not self.is_available():
            return []
        
        # Walmart API limits to 25 results max
        limit = min(limit, 25)
        
        # Match frontend implementation: uses start=21 (skips first 20 results)
        url = f"{self.BASE_URL}/search?query={quote(query)}&numItems={limit}&start=21"
        headers = self._get_headers(url)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Walmart products API returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    products = []
                    
                    for item in data.get("items", [])[:limit]:
                        # Map stock status like frontend: "Available" -> "In Stock", "Not available" -> "Out of Stock", else -> "Limited Stock"
                        stock = item.get("stock", "")
                        if stock == "Available":
                            availability = "In Stock"
                        elif stock == "Not available":
                            availability = "Out of Stock"
                        else:
                            availability = "Limited Stock"
                        
                        # Process product URL - replace |PUBID| with affiliate ID (matching frontend)
                        product_url = item.get("productTrackingUrl", "") or item.get("productUrl", "")
                        if "|PUBID|" in product_url:
                            # Replace with affiliate ID (configurable via WALMART_AFFILIATE_ID env var)
                            product_url = product_url.replace("|PUBID|", self.affiliate_id)
                        
                        # Extract brand from brandName (matching frontend)
                        brand = item.get("brandName")
                        
                        # Use mediumImage like frontend (fallback to largeImage or thumbnailImage)
                        image_url = item.get("mediumImage") or item.get("largeImage") or item.get("thumbnailImage", "")
                        
                        # Extract category from categoryPath (matching frontend logic)
                        category_path = item.get("categoryPath", "")
                        category = None
                        if category_path:
                            category_arr = category_path.split("/")
                            if category_arr:
                                category = category_arr[-1]  # Gets final category node
                        
                        product = {
                            "name": item.get("name", ""),
                            "brand": brand,
                            "price": item.get("salePrice") or item.get("msrp"),
                            "currency": "USD",
                            "quantity": None,  # Extract from name if possible
                            "size": None,
                            "availability": availability,
                            "product_url": product_url,
                            "image_url": image_url,
                            "store_name": "Walmart",
                            "store_zipcode": None,
                            "rating": item.get("customerRating"),
                            "review_count": item.get("numReviews"),
                            "description": item.get("shortDescription", "") or item.get("longDescription", ""),
                            "category": category,
                            "source": ["walmart_api"],
                            "upc": item.get("upc"),
                            "item_id": str(item.get("itemId", ""))
                        }
                        
                        products.append(product)
                    
                    logger.info(f"✅ Walmart API returned {len(products)} products")
                    return products
                    
        except Exception as e:
            logger.error(f"Error searching Walmart products: {e}", exc_info=True)
            return []
    
    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a single product by item ID (matching frontend getProductById)"""
        if not self.is_available():
            return None
        
        url = f"{self.BASE_URL}/items/{product_id}"
        headers = self._get_headers(url)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Walmart product API returned status {response.status} for product {product_id}")
                        return None
                    
                    item = await response.json()
                    
                    # Map stock status like frontend
                    stock = item.get("stock", "")
                    if stock == "Available":
                        availability = "In Stock"
                    elif stock == "Not available":
                        availability = "Out of Stock"
                    else:
                        availability = "Limited Stock"
                    
                    # Process product URL - replace |PUBID| with affiliate ID
                    product_url = item.get("productTrackingUrl", "") or item.get("productUrl", "")
                    if "|PUBID|" in product_url:
                        product_url = product_url.replace("|PUBID|", self.affiliate_id)
                    
                    # Extract category from categoryPath
                    category_path = item.get("categoryPath", "")
                    category = None
                    if category_path:
                        category_arr = category_path.split("/")
                        if category_arr:
                            category = category_arr[-1]
                    
                    product = {
                        "name": item.get("name", ""),
                        "brand": item.get("brandName"),
                        "price": item.get("salePrice") or item.get("msrp"),
                        "currency": "USD",
                        "quantity": None,
                        "size": None,
                        "availability": availability,
                        "product_url": product_url,
                        "image_url": item.get("mediumImage") or item.get("largeImage") or item.get("thumbnailImage", ""),
                        "store_name": "Walmart",
                        "store_zipcode": None,
                        "rating": item.get("customerRating"),
                        "review_count": item.get("numReviews"),
                        "description": item.get("shortDescription", "") or item.get("longDescription", ""),
                        "category": category,
                        "source": ["walmart_api"],
                        "upc": item.get("upc"),
                        "item_id": str(item.get("itemId", ""))
                    }
                    
                    return product
                    
        except Exception as e:
            logger.error(f"Error fetching Walmart product {product_id}: {e}", exc_info=True)
            return None


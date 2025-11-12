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
        
        self.key_version = 1  # Match Walmart Developer Portal key version
    
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
        """
        if not self.private_key:
            return ""
        
        # Create string to sign: consumer_id + timestamp + key_version (NO URL!)
        # This matches the TypeScript implementation
        string_to_sign = f"{self.consumer_id}\n{timestamp}\n{self.key_version}\n"
        
        # Sign with RSA private key (NodeRSA signs the raw string, not a hash)
        # Use PKCS1v15 padding with SHA256 hash
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
        
        url = f"{self.BASE_URL}/search?query={quote(query)}&numItems={limit}&start=0"
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
                        product = {
                            "name": item.get("name", ""),
                            "brand": None,  # Walmart API doesn't always provide brand
                            "price": item.get("salePrice") or item.get("msrp"),
                            "currency": "USD",
                            "quantity": None,  # Extract from name if possible
                            "size": None,
                            "availability": "In Stock" if item.get("availableOnline") else "Check Store",
                            "product_url": item.get("productUrl", ""),
                            "image_url": item.get("largeImage", "") or item.get("mediumImage", "") or item.get("thumbnailImage", ""),
                            "store_id": "walmart",
                            "store_name": "Walmart",
                            "store_address": None,
                            "store_city": None,
                            "store_state": None,
                            "store_zipcode": None,
                            "rating": item.get("customerRating"),
                            "review_count": item.get("numReviews"),
                            "description": item.get("shortDescription", ""),
                            "category": item.get("categoryPath", "").split("/")[-1] if item.get("categoryPath") else None,
                            "source": ["walmart_api"],
                            "item_id": str(item.get("itemId", ""))
                        }
                        
                        products.append(product)
                    
                    logger.info(f"✅ Walmart API returned {len(products)} products")
                    return products
                    
        except Exception as e:
            logger.error(f"Error searching Walmart products: {e}", exc_info=True)
            return []


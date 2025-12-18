"""
Google Geocoding Service for Zip Code to City/State Conversion
Provides dynamic zip code lookup using Google Geocoding API with caching and fallback.
"""

import os
import logging
import asyncio
from typing import Dict, Optional, Tuple
from functools import lru_cache
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for converting zip codes to city/state using Google Geocoding API"""
    
    # Static fallback mapping for common zip codes (used when API unavailable)
    STATIC_ZIP_MAPPING = {
        # Chicago, IL
        "60601": ("Chicago", "IL"), "60602": ("Chicago", "IL"), "60603": ("Chicago", "IL"),
        "60604": ("Chicago", "IL"), "60605": ("Chicago", "IL"), "60606": ("Chicago", "IL"),
        "60607": ("Chicago", "IL"), "60608": ("Chicago", "IL"), "60609": ("Chicago", "IL"),
        "60610": ("Chicago", "IL"), "60611": ("Chicago", "IL"), "60612": ("Chicago", "IL"),
        "60613": ("Chicago", "IL"), "60614": ("Chicago", "IL"), "60615": ("Chicago", "IL"),
        "60616": ("Chicago", "IL"), "60617": ("Chicago", "IL"), "60618": ("Chicago", "IL"),
        "60619": ("Chicago", "IL"), "60620": ("Chicago", "IL"), "60621": ("Chicago", "IL"),
        "60622": ("Chicago", "IL"), "60623": ("Chicago", "IL"), "60624": ("Chicago", "IL"),
        "60625": ("Chicago", "IL"), "60626": ("Chicago", "IL"), "60628": ("Chicago", "IL"),
        "60629": ("Chicago", "IL"), "60630": ("Chicago", "IL"), "60631": ("Chicago", "IL"),
        "60632": ("Chicago", "IL"), "60633": ("Chicago", "IL"), "60634": ("Chicago", "IL"),
        "60636": ("Chicago", "IL"), "60637": ("Chicago", "IL"), "60638": ("Chicago", "IL"),
        "60639": ("Chicago", "IL"), "60640": ("Chicago", "IL"), "60641": ("Chicago", "IL"),
        "60642": ("Chicago", "IL"), "60643": ("Chicago", "IL"), "60644": ("Chicago", "IL"),
        "60645": ("Chicago", "IL"), "60646": ("Chicago", "IL"), "60647": ("Chicago", "IL"),
        "60649": ("Chicago", "IL"), "60651": ("Chicago", "IL"), "60652": ("Chicago", "IL"),
        "60653": ("Chicago", "IL"), "60654": ("Chicago", "IL"), "60655": ("Chicago", "IL"),
        "60656": ("Chicago", "IL"), "60657": ("Chicago", "IL"), "60659": ("Chicago", "IL"),
        "60660": ("Chicago", "IL"), "60661": ("Chicago", "IL"),
        # New York, NY
        "10001": ("New York", "NY"), "10002": ("New York", "NY"), "10003": ("New York", "NY"),
        "10004": ("New York", "NY"), "10005": ("New York", "NY"), "10006": ("New York", "NY"),
        "10007": ("New York", "NY"), "10010": ("New York", "NY"), "10011": ("New York", "NY"),
        "10012": ("New York", "NY"), "10013": ("New York", "NY"), "10014": ("New York", "NY"),
        # Rochester, NY (Wegmans HQ)
        "14618": ("Rochester", "NY"), "14620": ("Rochester", "NY"), "14610": ("Rochester", "NY"),
        "14607": ("Rochester", "NY"), "14609": ("Rochester", "NY"), "14611": ("Rochester", "NY"),
        # Pennsylvania - Wegmans locations
        "18104": ("Allentown", "PA"), "18017": ("Bethlehem", "PA"), "19426": ("Collegeville", "PA"),
        "19428": ("Conshohocken", "PA"), "19335": ("Downingtown", "PA"), "16509": ("Erie", "PA"),
        "16506": ("Erie", "PA"), "17050": ("Mechanicsburg", "PA"), "17601": ("Lancaster", "PA"),
        "19406": ("King of Prussia", "PA"), "19355": ("Malvern", "PA"), "18936": ("Montgomeryville", "PA"),
        "18064": ("Nazareth", "PA"), "18508": ("Scranton", "PA"), "16803": ("State College", "PA"),
        "18702": ("Wilkes-Barre", "PA"), "18974": ("Warrington", "PA"), "17701": ("Williamsport", "PA"),
        "19067": ("Yardley", "PA"), "19063": ("Media", "PA"),
        # Pittsburgh area, PA
        "15213": ("Pittsburgh", "PA"), "15217": ("Pittsburgh", "PA"), "15232": ("Pittsburgh", "PA"),
        "15219": ("Pittsburgh", "PA"), "15222": ("Pittsburgh", "PA"), "15206": ("Pittsburgh", "PA"),
        # Philadelphia area, PA
        "19103": ("Philadelphia", "PA"), "19102": ("Philadelphia", "PA"), "19104": ("Philadelphia", "PA"),
        "19106": ("Philadelphia", "PA"), "19107": ("Philadelphia", "PA"), "19123": ("Philadelphia", "PA"),
        # Memphis, TN
        "38125": ("Memphis", "TN"), "38103": ("Memphis", "TN"), "38104": ("Memphis", "TN"),
        "38105": ("Memphis", "TN"), "38106": ("Memphis", "TN"), "38107": ("Memphis", "TN"),
        "38108": ("Memphis", "TN"), "38109": ("Memphis", "TN"), "38111": ("Memphis", "TN"),
        "38112": ("Memphis", "TN"), "38113": ("Memphis", "TN"), "38114": ("Memphis", "TN"),
        "38115": ("Memphis", "TN"), "38116": ("Memphis", "TN"), "38117": ("Memphis", "TN"),
        "38118": ("Memphis", "TN"), "38119": ("Memphis", "TN"), "38120": ("Memphis", "TN"),
        "38122": ("Memphis", "TN"), "38126": ("Memphis", "TN"), "38127": ("Memphis", "TN"),
        "38128": ("Memphis", "TN"), "38130": ("Memphis", "TN"), "38131": ("Memphis", "TN"),
        "38132": ("Memphis", "TN"), "38133": ("Memphis", "TN"), "38134": ("Memphis", "TN"),
        "38135": ("Memphis", "TN"), "38138": ("Memphis", "TN"), "38139": ("Memphis", "TN"),
        # Los Angeles, CA
        "90001": ("Los Angeles", "CA"), "90002": ("Los Angeles", "CA"), "90003": ("Los Angeles", "CA"),
        "90004": ("Los Angeles", "CA"), "90005": ("Los Angeles", "CA"), "90006": ("Los Angeles", "CA"),
        "90007": ("Los Angeles", "CA"), "90008": ("Los Angeles", "CA"), "90010": ("Los Angeles", "CA"),
        # San Francisco, CA
        "94102": ("San Francisco", "CA"), "94103": ("San Francisco", "CA"), "94104": ("San Francisco", "CA"),
        "94105": ("San Francisco", "CA"), "94107": ("San Francisco", "CA"), "94108": ("San Francisco", "CA"),
        # Boston, MA
        "02108": ("Boston", "MA"), "02109": ("Boston", "MA"), "02110": ("Boston", "MA"),
        "02111": ("Boston", "MA"), "02113": ("Boston", "MA"), "02114": ("Boston", "MA"),
        # New Jersey - Wegmans locations
        "08807": ("Bridgewater", "NJ"), "08002": ("Cherry Hill", "NJ"), "07981": ("Hanover", "NJ"),
        "07726": ("Manalapan", "NJ"), "07645": ("Montvale", "NJ"), "08054": ("Mt Laurel", "NJ"),
        "07712": ("Ocean", "NJ"), "08540": ("Princeton", "NJ"), "07095": ("Woodbridge", "NJ"),
        # Virginia - Wegmans locations
        "22314": ("Alexandria", "VA"), "22201": ("Arlington", "VA"), "20151": ("Chantilly", "VA"),
        "22901": ("Charlottesville", "VA"), "20166": ("Dulles", "VA"), "22030": ("Fairfax", "VA"),
        "22401": ("Fredericksburg", "VA"), "20176": ("Leesburg", "VA"), "23112": ("Midlothian", "VA"),
        "20191": ("Reston", "VA"), "22182": ("Tysons", "VA"), "23462": ("Virginia Beach", "VA"),
        # Maryland - Wegmans locations
        "21014": ("Bel Air", "MD"), "21044": ("Columbia", "MD"), "21114": ("Crofton", "MD"),
        "21701": ("Frederick", "MD"), "20874": ("Germantown", "MD"), "21030": ("Hunt Valley", "MD"),
        "21117": ("Owings Mills", "MD"), "20850": ("Rockville", "MD"), "20774": ("Woodmore", "MD"),
        # North Carolina - Wegmans locations
        "27514": ("Chapel Hill", "NC"), "27601": ("Raleigh", "NC"), "27513": ("Cary", "NC"),
        "27587": ("Wake Forest", "NC"),
        # Massachusetts - Wegmans locations
        "01803": ("Burlington", "MA"), "02467": ("Chestnut Hill", "MA"), "02155": ("Medford", "MA"),
        "01532": ("Northborough", "MA"), "02090": ("Westwood", "MA"),
    }
    
    # State abbreviation to full name mapping for fallback
    STATE_NAMES = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
        "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
        "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
        "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
        "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
        "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
        "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
        "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
        "DC": "District of Columbia"
    }
    
    # Zip code prefix to state mapping for fallback when API unavailable
    ZIP_PREFIX_TO_STATE = {
        "006": "PR", "007": "PR", "008": "PR", "009": "PR",  # Puerto Rico
        "010": "MA", "011": "MA", "012": "MA", "013": "MA", "014": "MA",  # Massachusetts
        "015": "MA", "016": "MA", "017": "MA", "018": "MA", "019": "MA",
        "020": "MA", "021": "MA", "022": "MA", "023": "MA", "024": "MA",
        "025": "MA", "026": "MA", "027": "MA",
        "028": "RI", "029": "RI",  # Rhode Island
        "030": "NH", "031": "NH", "032": "NH", "033": "NH", "034": "NH",  # New Hampshire
        "035": "VT", "036": "VT", "037": "VT", "038": "VT", "039": "VT",  # Vermont
        "040": "ME", "041": "ME", "042": "ME", "043": "ME", "044": "ME",  # Maine
        "045": "ME", "046": "ME", "047": "ME", "048": "ME", "049": "ME",
        "050": "VT", "051": "VT", "052": "VT", "053": "VT", "054": "VT",
        "055": "MA", "056": "VT", "057": "VT", "058": "VT", "059": "VT",
        "060": "CT", "061": "CT", "062": "CT", "063": "CT", "064": "CT",  # Connecticut
        "065": "CT", "066": "CT", "067": "CT", "068": "CT", "069": "CT",
        "070": "NJ", "071": "NJ", "072": "NJ", "073": "NJ", "074": "NJ",  # New Jersey
        "075": "NJ", "076": "NJ", "077": "NJ", "078": "NJ", "079": "NJ",
        "080": "NJ", "081": "NJ", "082": "NJ", "083": "NJ", "084": "NJ",
        "085": "NJ", "086": "NJ", "087": "NJ", "088": "NJ", "089": "NJ",
        "100": "NY", "101": "NY", "102": "NY", "103": "NY", "104": "NY",  # New York
        "105": "NY", "106": "NY", "107": "NY", "108": "NY", "109": "NY",
        "110": "NY", "111": "NY", "112": "NY", "113": "NY", "114": "NY",
        "115": "NY", "116": "NY", "117": "NY", "118": "NY", "119": "NY",
        "120": "NY", "121": "NY", "122": "NY", "123": "NY", "124": "NY",
        "125": "NY", "126": "NY", "127": "NY", "128": "NY", "129": "NY",
        "130": "NY", "131": "NY", "132": "NY", "133": "NY", "134": "NY",
        "135": "NY", "136": "NY", "137": "NY", "138": "NY", "139": "NY",
        "140": "NY", "141": "NY", "142": "NY", "143": "NY", "144": "NY",
        "145": "NY", "146": "NY", "147": "NY", "148": "NY", "149": "NY",
        "150": "PA", "151": "PA", "152": "PA", "153": "PA", "154": "PA",  # Pennsylvania
        "155": "PA", "156": "PA", "157": "PA", "158": "PA", "159": "PA",
        "160": "PA", "161": "PA", "162": "PA", "163": "PA", "164": "PA",
        "165": "PA", "166": "PA", "167": "PA", "168": "PA", "169": "PA",
        "170": "PA", "171": "PA", "172": "PA", "173": "PA", "174": "PA",
        "175": "PA", "176": "PA", "177": "PA", "178": "PA", "179": "PA",
        "180": "PA", "181": "PA", "182": "PA", "183": "PA", "184": "PA",
        "185": "PA", "186": "PA", "187": "PA", "188": "PA", "189": "PA",
        "190": "PA", "191": "PA", "192": "PA", "193": "PA", "194": "PA",
        "195": "PA", "196": "PA",
        "197": "DE", "198": "DE", "199": "DE",  # Delaware
        "200": "DC", "201": "VA", "202": "DC", "203": "DC", "204": "DC",  # DC/Virginia
        "205": "DC", "206": "MD", "207": "MD", "208": "MD", "209": "MD",
        "210": "MD", "211": "MD", "212": "MD", "214": "MD", "215": "MD",  # Maryland
        "216": "MD", "217": "MD", "218": "MD", "219": "MD",
        "220": "VA", "221": "VA", "222": "VA", "223": "VA", "224": "VA",  # Virginia
        "225": "VA", "226": "VA", "227": "VA", "228": "VA", "229": "VA",
        "230": "VA", "231": "VA", "232": "VA", "233": "VA", "234": "VA",
        "235": "VA", "236": "VA", "237": "VA", "238": "VA", "239": "VA",
        "240": "VA", "241": "VA", "242": "VA", "243": "VA", "244": "VA",
        "245": "VA", "246": "WV",
        "247": "WV", "248": "WV", "249": "WV",  # West Virginia
        "250": "WV", "251": "WV", "252": "WV", "253": "WV", "254": "WV",
        "255": "WV", "256": "WV", "257": "WV", "258": "WV", "259": "WV",
        "260": "WV", "261": "WV", "262": "WV", "263": "WV", "264": "WV",
        "265": "WV", "266": "WV", "267": "WV", "268": "WV",
        "270": "NC", "271": "NC", "272": "NC", "273": "NC", "274": "NC",  # North Carolina
        "275": "NC", "276": "NC", "277": "NC", "278": "NC", "279": "NC",
        "280": "NC", "281": "NC", "282": "NC", "283": "NC", "284": "NC",
        "285": "NC", "286": "NC", "287": "NC", "288": "NC", "289": "NC",
        "290": "SC", "291": "SC", "292": "SC", "293": "SC", "294": "SC",  # South Carolina
        "295": "SC", "296": "SC", "297": "SC", "298": "SC", "299": "SC",
        "300": "GA", "301": "GA", "302": "GA", "303": "GA", "304": "GA",  # Georgia
        "305": "GA", "306": "GA", "307": "GA", "308": "GA", "309": "GA",
        "310": "GA", "311": "GA", "312": "GA", "313": "GA", "314": "GA",
        "315": "GA", "316": "GA", "317": "GA", "318": "GA", "319": "GA",
        "320": "FL", "321": "FL", "322": "FL", "323": "FL", "324": "FL",  # Florida
        "325": "FL", "326": "FL", "327": "FL", "328": "FL", "329": "FL",
        "330": "FL", "331": "FL", "332": "FL", "333": "FL", "334": "FL",
        "335": "FL", "336": "FL", "337": "FL", "338": "FL", "339": "FL",
        "340": "FL", "341": "FL", "342": "FL", "344": "FL", "346": "FL",
        "347": "FL", "349": "FL",
        "430": "OH", "431": "OH", "432": "OH", "433": "OH", "434": "OH",  # Ohio
        "435": "OH", "436": "OH", "437": "OH", "438": "OH", "439": "OH",
        "440": "OH", "441": "OH", "442": "OH", "443": "OH", "444": "OH",
        "445": "OH", "446": "OH", "447": "OH", "448": "OH", "449": "OH",
        "450": "OH", "451": "OH", "452": "OH", "453": "OH", "454": "OH",
        "455": "OH", "456": "OH", "457": "OH", "458": "OH", "459": "OH",
        "460": "IN", "461": "IN", "462": "IN", "463": "IN", "464": "IN",  # Indiana
        "465": "IN", "466": "IN", "467": "IN", "468": "IN", "469": "IN",
        "470": "IN", "471": "IN", "472": "IN", "473": "IN", "474": "IN",
        "475": "IN", "476": "IN", "477": "IN", "478": "IN", "479": "IN",
        "600": "IL", "601": "IL", "602": "IL", "603": "IL", "604": "IL",  # Illinois
        "605": "IL", "606": "IL", "607": "IL", "608": "IL", "609": "IL",
        "610": "IL", "611": "IL", "612": "IL", "613": "IL", "614": "IL",
        "615": "IL", "616": "IL", "617": "IL", "618": "IL", "619": "IL",
        "620": "IL", "621": "IL", "622": "IL", "623": "IL", "624": "IL",
        "625": "IL", "626": "IL", "627": "IL", "628": "IL", "629": "IL",
        "900": "CA", "901": "CA", "902": "CA", "903": "CA", "904": "CA",  # California
        "905": "CA", "906": "CA", "907": "CA", "908": "CA", "910": "CA",
        "911": "CA", "912": "CA", "913": "CA", "914": "CA", "915": "CA",
        "916": "CA", "917": "CA", "918": "CA", "919": "CA", "920": "CA",
        "921": "CA", "922": "CA", "923": "CA", "924": "CA", "925": "CA",
        "926": "CA", "927": "CA", "928": "CA", "930": "CA", "931": "CA",
        "932": "CA", "933": "CA", "934": "CA", "935": "CA", "936": "CA",
        "937": "CA", "938": "CA", "939": "CA", "940": "CA", "941": "CA",
        "942": "CA", "943": "CA", "944": "CA", "945": "CA", "946": "CA",
        "947": "CA", "948": "CA", "949": "CA", "950": "CA", "951": "CA",
        "952": "CA", "953": "CA", "954": "CA", "955": "CA", "956": "CA",
        "957": "CA", "958": "CA", "959": "CA", "960": "CA", "961": "CA",
        "750": "TX", "751": "TX", "752": "TX", "753": "TX", "754": "TX",  # Texas
        "755": "TX", "756": "TX", "757": "TX", "758": "TX", "759": "TX",
        "760": "TX", "761": "TX", "762": "TX", "763": "TX", "764": "TX",
        "765": "TX", "766": "TX", "767": "TX", "768": "TX", "769": "TX",
        "770": "TX", "771": "TX", "772": "TX", "773": "TX", "774": "TX",
        "775": "TX", "776": "TX", "777": "TX", "778": "TX", "779": "TX",
        "780": "TX", "781": "TX", "782": "TX", "783": "TX", "784": "TX",
        "785": "TX", "786": "TX", "787": "TX", "788": "TX", "789": "TX",
        "790": "TX", "791": "TX", "792": "TX", "793": "TX", "794": "TX",
        "795": "TX", "796": "TX", "797": "TX", "798": "TX", "799": "TX",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize geocoding service with optional Google API key"""
        self.api_key = api_key or os.getenv("GOOGLE_GEOCODING_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
        self._cache: Dict[str, Tuple[str, str, float, float]] = {}  # zipcode -> (city, state, lat, lng)
        
        if self.api_key:
            logger.info("Google Geocoding API initialized")
        else:
            logger.warning("No Google API key found - using static zip code mapping only")
    
    def is_available(self) -> bool:
        """Check if Google Geocoding API is available"""
        return bool(self.api_key)
    
    async def get_location_from_zipcode(self, zipcode: str) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
        """
        Get city, state, latitude, and longitude from zip code
        
        Args:
            zipcode: 5-digit US zip code
            
        Returns:
            Tuple of (city, state, latitude, longitude) or (None, None, None, None) if not found
        """
        if not zipcode or len(zipcode) != 5:
            return None, None, None, None
        
        # Check cache first
        if zipcode in self._cache:
            logger.debug(f"Cache hit for zipcode {zipcode}")
            return self._cache[zipcode]
        
        # Try Google Geocoding API if available
        if self.api_key:
            result = await self._geocode_with_google(zipcode)
            if result[0] is not None:
                self._cache[zipcode] = result
                return result
        
        # Fallback to static mapping
        return self._get_from_static_mapping(zipcode)
    
    async def get_city_state_from_zipcode(self, zipcode: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get city and state from zip code (convenience method)
        
        Args:
            zipcode: 5-digit US zip code
            
        Returns:
            Tuple of (city, state) or (None, None) if not found
        """
        city, state, _, _ = await self.get_location_from_zipcode(zipcode)
        return city, state
    
    def get_city_state_sync(self, zipcode: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Synchronous version of get_city_state_from_zipcode
        Uses only static mapping (no API calls)
        
        Args:
            zipcode: 5-digit US zip code
            
        Returns:
            Tuple of (city, state) or (None, None) if not found
        """
        if not zipcode or len(zipcode) != 5:
            return None, None
        
        # Check cache first
        if zipcode in self._cache:
            city, state, _, _ = self._cache[zipcode]
            return city, state
        
        # Use static mapping only (sync)
        city, state, _, _ = self._get_from_static_mapping(zipcode)
        return city, state
    
    async def _geocode_with_google(self, zipcode: str) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
        """Call Google Geocoding API to get location data"""
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={zipcode}&key={self.api_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status != 200:
                        logger.warning(f"Google Geocoding API returned status {response.status}")
                        return None, None, None, None
                    
                    data = await response.json()
                    
                    if data.get("status") != "OK" or not data.get("results"):
                        logger.debug(f"No results from Google Geocoding for {zipcode}: {data.get('status')}")
                        return None, None, None, None
                    
                    result = data["results"][0]
                    
                    # Extract city and state from address components
                    city = None
                    state = None
                    for component in result.get("address_components", []):
                        types = component.get("types", [])
                        if "locality" in types:
                            city = component.get("long_name")
                        elif "administrative_area_level_1" in types:
                            state = component.get("short_name")
                    
                    # Get coordinates
                    location = result.get("geometry", {}).get("location", {})
                    lat = location.get("lat")
                    lng = location.get("lng")
                    
                    if city and state:
                        logger.debug(f"Google Geocoding: {zipcode} -> {city}, {state} ({lat}, {lng})")
                        return city, state, lat, lng
                    
                    return None, None, None, None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Google Geocoding API timeout for {zipcode}")
            return None, None, None, None
        except Exception as e:
            logger.warning(f"Google Geocoding API error for {zipcode}: {e}")
            return None, None, None, None
    
    def _get_from_static_mapping(self, zipcode: str) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
        """Get location from static mapping or zip prefix"""
        # Check exact match first
        if zipcode in self.STATIC_ZIP_MAPPING:
            city, state = self.STATIC_ZIP_MAPPING[zipcode]
            logger.debug(f"Static mapping: {zipcode} -> {city}, {state}")
            return city, state, None, None
        
        # Try to determine state from zip prefix
        prefix = zipcode[:3]
        if prefix in self.ZIP_PREFIX_TO_STATE:
            state = self.ZIP_PREFIX_TO_STATE[prefix]
            state_name = self.STATE_NAMES.get(state, state)
            logger.debug(f"Zip prefix mapping: {zipcode} -> {state_name}, {state}")
            return state_name, state, None, None
        
        return None, None, None, None
    
    def get_state_from_zipcode(self, zipcode: str) -> Optional[str]:
        """
        Get state abbreviation from zip code using prefix mapping
        This is fast and doesn't require API calls
        
        Args:
            zipcode: 5-digit US zip code
            
        Returns:
            State abbreviation (e.g., "PA", "NY") or None
        """
        if not zipcode or len(zipcode) < 3:
            return None
        
        # Check exact match first
        if zipcode in self.STATIC_ZIP_MAPPING:
            _, state = self.STATIC_ZIP_MAPPING[zipcode]
            return state
        
        # Use prefix mapping
        prefix = zipcode[:3]
        return self.ZIP_PREFIX_TO_STATE.get(prefix)
    
    def clear_cache(self):
        """Clear the geocoding cache"""
        self._cache.clear()
        logger.info("Geocoding cache cleared")


# Global singleton instance
_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get or create the global geocoding service instance"""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service


def set_geocoding_service(service: GeocodingService):
    """Set the global geocoding service instance"""
    global _geocoding_service
    _geocoding_service = service



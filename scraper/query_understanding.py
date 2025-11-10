"""
Query Understanding Service
Analyzes and enhances user queries for optimal search results
"""

from typing import Dict, List, Optional, Tuple
import re
from collections import Counter

class QueryUnderstanding:
    """Understand and enhance user queries for universal grocery search"""
    
    # Comprehensive grocery synonyms
    SYNONYMS = {
        'soda': ['pop', 'soft drink', 'carbonated beverage', 'cola', 'soda pop'],
        'milk': ['dairy milk', 'cow milk', 'whole milk', '2% milk'],
        'eggs': ['chicken eggs', 'fresh eggs', 'large eggs', 'dozen eggs'],
        'bread': ['loaf', 'baked goods', 'white bread', 'wheat bread'],
        'cereal': ['breakfast cereal', 'cereal box', 'breakfast food'],
        'chips': ['potato chips', 'crisps', 'snack chips'],
        'cookies': ['biscuits', 'sweet treats', 'baked cookies'],
        'juice': ['fruit juice', 'orange juice', 'apple juice'],
        'yogurt': ['yoghurt', 'greek yogurt', 'plain yogurt'],
        'cheese': ['cheddar cheese', 'swiss cheese', 'american cheese'],
        'butter': ['salted butter', 'unsalted butter', 'sweet butter'],
        'chicken': ['chicken breast', 'chicken thighs', 'whole chicken'],
        'beef': ['ground beef', 'steak', 'roast beef'],
        'pork': ['pork chops', 'bacon', 'pork loin'],
        'fish': ['salmon', 'tuna', 'tilapia', 'cod'],
        'rice': ['white rice', 'brown rice', 'jasmine rice'],
        'pasta': ['spaghetti', 'penne', 'macaroni'],
        'soup': ['canned soup', 'broth', 'stock'],
        'crackers': ['saltines', 'wheat crackers', 'ritz crackers'],
        'peanut butter': ['pb', 'peanut spread', 'jif'],
        'mayonnaise': ['mayo', 'mayonnaise', 'hellmann\'s'],
        'ketchup': ['catsup', 'tomato ketchup', 'heinz ketchup'],
        'mustard': ['yellow mustard', 'dijon mustard', 'honey mustard'],
        'coffee': ['ground coffee', 'coffee beans', 'instant coffee'],
        'tea': ['black tea', 'green tea', 'herbal tea'],
        'bananas': ['banana', 'bananas'],
        'apples': ['apple', 'apples'],
        'oranges': ['orange', 'oranges'],
        'lettuce': ['iceberg lettuce', 'romaine lettuce', 'leaf lettuce'],
        'tomatoes': ['tomato', 'tomatoes', 'roma tomatoes'],
        'onions': ['onion', 'onions', 'yellow onion'],
        'potatoes': ['potato', 'potatoes', 'russet potatoes'],
        'carrots': ['carrot', 'carrots', 'baby carrots'],
    }
    
    # Comprehensive brand list
    BRANDS = [
        'kellogg', 'coca cola', 'coke', 'pepsi', 'nestle', 'kraft', 'heinz',
        'campbell', 'general mills', 'frito lay', 'unilever', 'procter & gamble',
        'p&g', 'tyson', 'perdue', 'hormel', 'conagra', 'j&j', 'johnson & johnson',
        'mars', 'hershey', 'mondelez', 'kellogg\'s', 'quaker', 'post',
        'nabisco', 'oreo', 'ritz', 'triscuit', 'wheat thins', 'cheez-it',
        'lays', 'doritos', 'fritos', 'tostitos', 'ruffles', 'cheetos',
        'great value', 'market pantry', 'good & gather', 'up&up', 'simply',
        'organic valley', 'horizon', 'stonyfield', 'chobani', 'yoplait',
        'dannon', 'activia', 'siggi\'s', 'fage', 'oikos',
        'tide', 'gain', 'downy', 'bounce', 'arm & hammer',
        'charmin', 'bounty', 'puffs', 'scott', 'cottonelle',
        'gatorade', 'powerade', 'vitamin water', 'smartwater', 'aquafina',
        'dasani', 'evian', 'fiji', 'poland spring', 'arrowhead',
        'folgers', 'maxwell house', 'starbucks', 'dunkin', 'green mountain',
        'lipton', 'twinings', 'bigelow', 'celestial seasonings',
        'hunt\'s', 'del monte', 'dole', 'chiquita', 'fresh express',
        'earthbound farm', 'organic girl', 'taylor farms',
        'tyson', 'perdue', 'foster farms', 'sanderson farms',
        'oscar mayer', 'hillshire farm', 'johnsonville', 'jimmy dean',
        'sara lee', 'thomas', 'pepperidge farm', 'arnold', 'nature\'s own',
        'wonder', 'martin\'s', 'ball park', 'hebrew national',
        'philadelphia', 'kraft', 'velveeta', 'sargento', 'cabot',
        'tillamook', 'land o\'lakes', 'kerrygold', 'belgioioso',
        'land o\'lakes', 'country crock', 'i can\'t believe it\'s not butter',
        'smart balance', 'earth balance', 'becel',
        'hellmann\'s', 'best foods', 'duke\'s', 'kraft', 'miracle whip',
        'hidden valley', 'wish-bone', 'ken\'s', 'newman\'s own',
        'hunts', 'contadina', 'muir glen', 'cento', 'san marzano',
        'barilla', 'ronzoni', 'mueller\'s', 'san giorgio', 'de cecco',
        'minute rice', 'uncle ben\'s', 'mahatma', 'carolina',
        'quaker', 'old fashioned', 'steel cut', 'instant',
        'progresso', 'campbell\'s', 'amy\'s', 'healthy choice', 'lean cuisine',
        'stouffer\'s', 'hungry man', 'banquet', 'swanson',
        'cheerios', 'frosted flakes', 'lucky charms', 'cocoa puffs',
        'cinnamon toast crunch', 'honey nut cheerios', 'froot loops',
        'cap\'n crunch', 'reeses puffs', 'special k', 'raisin bran',
        'wheaties', 'total', 'kix', 'trix', 'golden grahams',
        'cocoa pebbles', 'fruity pebbles', 'rice krispies',
        'oreo', 'chips ahoy', 'nilla wafers', 'ritz', 'triscuit',
        'wheat thins', 'cheez-it', 'goldfish', 'ritz bits',
        'pepperidge farm', 'entenmann\'s', 'sara lee', 'hostess',
        'little debbie', 'tastykake', 'drakes', 'entenmann\'s',
        'nature valley', 'quaker chewy', 'clif bar', 'larabar',
        'kind', 'rxbar', 'quest', 'thinkthin', 'atkins',
        'slim fast', 'special k', 'fiber one', 'nature valley',
        'lays', 'doritos', 'fritos', 'tostitos', 'ruffles',
        'cheetos', 'fritos', 'sun chips', 'baked lays',
        'popchips', 'terra', 'kettle', 'cape cod',
        'planters', 'blue diamond', 'fisher', 'diamond',
        'sun maid', 'ocean spray', 'welch\'s', 'motts',
        'tropicana', 'minute maid', 'simply', 'naked',
        'bolthouse farms', 'odwalla', 'naked juice',
        'coca-cola', 'pepsi', 'sprite', 'fanta', 'dr pepper',
        'mountain dew', '7up', 'sierra mist', 'fresca',
        'arizona', 'snapple', 'lipton', 'honest tea',
        'red bull', 'monster', 'rockstar', 'bang',
        'starbucks', 'dunkin', 'folgers', 'maxwell house',
        'green mountain', 'keurig', 'nescafe', 'taster\'s choice',
        'lipton', 'twinings', 'bigelow', 'celestial seasonings',
        'tazo', 'yogi', 'traditional medicinals',
    ]
    
    # Comprehensive attributes
    ATTRIBUTES = [
        'organic', 'gluten-free', 'low-fat', 'sugar-free', 'vegan',
        'non-gmo', 'cage-free', 'free-range', 'whole grain', 'low sodium',
        'reduced fat', 'fat-free', 'skim', '2%', 'whole milk',
        'grass-fed', 'hormone-free', 'antibiotic-free', 'natural',
        'no preservatives', 'no artificial', 'all-natural',
        'kosher', 'halal', 'fair trade', 'sustainable',
        'local', 'fresh', 'frozen', 'canned', 'dried',
        'large', 'extra large', 'jumbo', 'medium', 'small',
        'family size', 'bulk', 'economy size', 'value pack',
        'single serve', 'multi-pack', 'variety pack',
        'unsalted', 'salted', 'sweet', 'savory',
        'spicy', 'mild', 'hot', 'original', 'flavored',
        'plain', 'vanilla', 'chocolate', 'strawberry',
        'whole wheat', 'white', 'multigrain', 'sourdough',
        'enriched', 'fortified', 'vitamin d', 'calcium',
        'protein', 'fiber', 'omega-3', 'probiotic',
        'pasteurized', 'homogenized', 'ultra-pasteurized',
        'grade a', 'aa', 'a', 'usda', 'certified',
    ]
    
    # Comprehensive categories
    CATEGORIES = {
        'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'eggs', 'cream', 'sour cream', 'cottage cheese'],
        'produce': ['fruit', 'vegetables', 'fresh', 'organic produce', 'apples', 'bananas', 'oranges', 'lettuce', 'tomatoes'],
        'meat': ['chicken', 'beef', 'pork', 'fish', 'seafood', 'turkey', 'lamb', 'bacon', 'sausage'],
        'bakery': ['bread', 'pastries', 'cakes', 'muffins', 'bagels', 'rolls', 'donuts', 'croissants'],
        'beverages': ['soda', 'juice', 'water', 'coffee', 'tea', 'sports drink', 'energy drink'],
        'snacks': ['chips', 'crackers', 'cookies', 'nuts', 'trail mix', 'granola bars', 'pretzels'],
        'frozen': ['frozen food', 'frozen vegetables', 'frozen fruit', 'ice cream', 'frozen meals'],
        'canned': ['canned goods', 'canned vegetables', 'canned fruit', 'canned soup', 'canned beans'],
        'pantry': ['rice', 'pasta', 'flour', 'sugar', 'spices', 'oils', 'vinegar', 'condiments'],
        'breakfast': ['cereal', 'oatmeal', 'pancakes', 'waffles', 'syrup', 'breakfast bars'],
        'deli': ['deli meat', 'deli cheese', 'sandwich meat', 'lunch meat', 'sliced cheese'],
        'baby': ['baby food', 'formula', 'diapers', 'baby wipes', 'baby care'],
        'pet': ['dog food', 'cat food', 'pet supplies', 'pet treats'],
        'household': ['cleaning supplies', 'paper products', 'laundry', 'trash bags'],
        'personal care': ['shampoo', 'soap', 'toothpaste', 'deodorant', 'body wash'],
    }
    
    def analyze(self, query: str) -> Dict:
        """Analyze query and extract information"""
        query_lower = query.lower().strip()
        
        return {
            "original": query,
            "cleaned": self._clean_query(query_lower),
            "tokens": query_lower.split(),
            "has_brand": self._detect_brand(query_lower),
            "has_category": self._detect_category(query_lower),
            "has_attribute": self._detect_attributes(query_lower),
            "has_quantity": self._detect_quantity(query_lower),
            "intent": self._classify_intent(query_lower),
            "expansions": self._generate_expansions(query_lower)
        }
    
    def _clean_query(self, query: str) -> str:
        """Remove common stop words"""
        stop_words = {'i', 'need', 'want', 'looking', 'for', 'the', 'a', 'an', 'some'}
        tokens = query.split()
        cleaned = [t for t in tokens if t not in stop_words]
        return ' '.join(cleaned)
    
    def _detect_brand(self, query: str) -> Optional[str]:
        """Detect brand in query with fuzzy matching"""
        query_lower = query.lower()
        # Sort brands by length (longest first) to match "coca cola" before "coke"
        sorted_brands = sorted(self.BRANDS, key=len, reverse=True)
        for brand in sorted_brands:
            brand_lower = brand.lower()
            # Exact match or word boundary match
            if brand_lower in query_lower:
                # Check word boundaries for better accuracy
                pattern = r'\b' + re.escape(brand_lower) + r'\b'
                if re.search(pattern, query_lower):
                    return brand
        return None
    
    def _detect_category(self, query: str) -> Optional[str]:
        """Detect category with priority scoring"""
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        for category, keywords in self.CATEGORIES.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > best_score:
                best_score = score
                best_match = category
        
        return best_match if best_score > 0 else None
    
    def _detect_attributes(self, query: str) -> List[str]:
        """Detect product attributes with word boundary matching"""
        found = []
        query_lower = query.lower()
        for attr in self.ATTRIBUTES:
            attr_lower = attr.lower()
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(attr_lower) + r'\b'
            if re.search(pattern, query_lower):
                found.append(attr)
        return found
    
    def _detect_quantity(self, query: str) -> Optional[str]:
        """Detect quantity/size with comprehensive patterns"""
        patterns = [
            r'(\d+\s*(pack|ct|count|oz|lb|gallon|liter|fl\s*oz|ml|kg|g))',
            r'(\d+\s*-\s*\w+)',  # "12-pack"
            r'(\d+\s*x\s*\d+)',  # "12x12"
            r'(family\s+size)',
            r'(bulk)',
            r'(\d+\s*dozen)',
            r'(\d+\s*count)',
            r'(\d+\s*piece)',
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _classify_intent(self, query: str) -> str:
        """Classify search intent with priority"""
        # Brand searches are most specific
        if self._detect_brand(query):
            return "BRAND_SEARCH"
        # Category browsing
        if self._detect_category(query):
            return "CATEGORY_BROWSE"
        # Attribute filtering
        if self._detect_attributes(query):
            return "ATTRIBUTE_FILTER"
        # Default to product search
        return "PRODUCT_SEARCH"
    
    def _generate_expansions(self, query: str) -> List[str]:
        """Generate comprehensive query expansions"""
        expansions = [query]
        query_lower = query.lower()
        
        # Synonym expansion
        for word, syns in self.SYNONYMS.items():
            if word in query_lower:
                for syn in syns:
                    # Replace word with synonym
                    expanded = re.sub(r'\b' + re.escape(word) + r'\b', syn, query_lower, flags=re.IGNORECASE)
                    if expanded != query_lower:
                        expansions.append(expanded)
        
        # Plural/singular variations
        if query_lower.endswith('s') and len(query_lower) > 1:
            expansions.append(query_lower[:-1])  # Remove 's'
        elif not query_lower.endswith('s'):
            expansions.append(query_lower + 's')  # Add 's'
        
        return list(set(expansions))
    
    def extract_entities(self, query: str) -> Dict:
        """Extract all entities from query"""
        query_lower = query.lower()
        return {
            "brand": self._detect_brand(query_lower),
            "category": self._detect_category(query_lower),
            "attributes": self._detect_attributes(query_lower),
            "quantity": self._detect_quantity(query_lower),
            "product_name": self._extract_product_name(query_lower)
        }
    
    def _extract_product_name(self, query: str) -> str:
        """Extract product name by removing brands, attributes, quantities"""
        cleaned = query.lower()
        
        # Remove brand
        brand = self._detect_brand(cleaned)
        if brand:
            cleaned = re.sub(r'\b' + re.escape(brand.lower()) + r'\b', '', cleaned)
        
        # Remove attributes
        for attr in self._detect_attributes(cleaned):
            cleaned = re.sub(r'\b' + re.escape(attr.lower()) + r'\b', '', cleaned)
        
        # Remove quantities
        quantity = self._detect_quantity(cleaned)
        if quantity:
            cleaned = re.sub(re.escape(quantity.lower()), '', cleaned)
        
        # Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if cleaned else query.lower()
    
    def enhance_for_exa(self, query: str, zipcode: str = None) -> str:
        """Enhance query specifically for Exa API with optimal formatting"""
        analysis = self.analyze(query)
        enhanced = analysis['cleaned']
        
        # Build optimal query structure
        parts = []
        
        # Add brand if detected
        if analysis['has_brand']:
            parts.append(analysis['has_brand'])
        
        # Add product name (cleaned)
        product_name = self._extract_product_name(enhanced)
        if product_name:
            parts.append(product_name)
        
        # Add attributes
        if analysis['has_attribute']:
            parts.extend(analysis['has_attribute'])
        
        # Add quantity
        if analysis['has_quantity']:
            parts.append(analysis['has_quantity'])
        
        # Reconstruct query
        if parts:
            enhanced = ' '.join(parts)
        
        # Add grocery context if not present
        if not any(word in enhanced for word in ['grocery', 'store', 'product', 'buy', 'shop']):
            enhanced = f"{enhanced} grocery product"
        
        return enhanced
    
    def build_optimal_query(self, query: str, zipcode: str = None, store_name: str = None) -> Dict[str, str]:
        """Build optimal query variations for multi-strategy search"""
        analysis = self.analyze(query)
        
        queries = {
            "primary": self.enhance_for_exa(query, zipcode),
            "expanded": [],
            "exact": analysis['cleaned'],
            "category_based": None,
            "brand_based": None
        }
        
        # Generate expansions
        expansions = self._generate_expansions(query)
        queries["expanded"] = [self.enhance_for_exa(exp, zipcode) for exp in expansions[:3]]  # Top 3
        
        # Category-based query
        if analysis['has_category']:
            queries["category_based"] = f"{analysis['has_category']} {analysis['cleaned']}"
        
        # Brand-based query
        if analysis['has_brand']:
            queries["brand_based"] = f"{analysis['has_brand']} {self._extract_product_name(query)}"
        
        return queries


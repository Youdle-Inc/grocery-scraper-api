# Costco.com Page Structure Research

## Overview
Research conducted on November 19, 2025 to understand Costco's product listing page structure for building a Costco extractor.

## Page Structure

### Search Results Page
- **URL Pattern**: `https://www.costco.com/s?keyword={query}`
- **Page Title**: `{query} | Costco`
- **Framework**: Uses Material-UI (MUI) components with Next.js

### Product List Container
- **Container ID**: `#productList`
- **Container Classes**: `MuiGrid2-root MuiGrid2-container MuiGrid2-direction-xs-row MuiGrid2-spacing-xs-6`
- **Structure**: Direct children are product cards (no nested wrappers)

### Product Card Structure

#### Container Element
- **Tag**: `<div>`
- **Classes**: `MuiGrid2-root MuiGrid2-direction-xs-row MuiGrid2-grid-xs-3`
- **Data Attributes**: 
  - `data-testid="Grid"`

#### Product Card Wrapper
- **Tag**: `<div>` (direct child of grid item)
- **Classes**: `MuiBox-root`
- **Data Attributes**:
  - `data-source="native"`
  - `data-testid="ProductTile_{PRODUCT_ID}"`
  - `data-tile-index="{index}"`
  - `data-private="false"`
- **Role**: `role="group"`

### Key Product Elements

#### 1. Product Name
**Location**: Multiple possible locations
- **Primary**: `<h3>` element with:
  - **ID**: `ProductTile_{PRODUCT_ID}_title`
  - **Classes**: `MuiTypography-root MuiTypography-t6`
  - **Data Attribute**: `data-testid` (contains "title")
- **Alternative**: `<a>` link element:
  - **Classes**: `MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineHover`
  - **Contains**: Product name as text content

**Example**: "OvaEasy Whole Egg Crystals #10 Cans, 2-pack (144 Total Eggs)"

#### 2. Product URL
**Location**: `<a>` tag
- **Pattern**: `https://www.costco.com/{slug}.product.{PRODUCT_ID}.html`
- **Example**: `https://www.costco.com/ovaeasy-whole-egg-crystals-10-cans-2-pack-144-total-eggs.product.4000200872.html`
- **Classes**: `MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineHover`

#### 3. Product Price
**Location**: `<div>` containing price text
- **Container Classes**: `MuiBox-root` (with MUI classes)
- **Price Element**: 
  - **Tag**: `<div>` with class `MuiTypography-root MuiTypography-t5`
  - **Text Format**: `$XX.XX` or `$X,XXX.XX`
  - **Pattern**: `/\$[\d,]+\.?\d*/`
- **Special Cases**:
  - "Members Only" text when price requires membership login
  - Price ranges: `$XX.XX - $XX.XX`

**Example**: `$99.99`

#### 4. Product Image
**Location**: `<img>` tag
- **Container**: `<div>` with `data-testid="ProductImage_{PRODUCT_ID}"`
- **Image Attributes**:
  - **Src Pattern**: `https://bfasset.costco-static.com/{path}?auto=webp&format=jpg&width=350&height=350&fit=bounds&canvas=350,350`
  - **Alt**: Product name
  - **Loading**: `lazy`
  - **Classes**: `MuiBox-root`
  - **Data Attribute**: `data-airgap-id`

**Example**: `https://bfasset.costco-static.com/U447IH35/as/56ngskhmsxhfx63spxx56xf/1758833-847__1?auto=webp&format=jpg&width=350&height=350&fit=bounds&canvas=350,350`

#### 5. Product Rating/Reviews
**Location**: `<div>` containing rating display
- **Container Classes**: `MuiBox-root`
- **Rating Display**: Star icons (SVG) + review count
- **Review Count Format**: `(XX)` where XX is number of reviews
- **Pattern**: `\((\d+)\)`

**Example**: `(41)` reviews

#### 6. Badges/Labels
**Common Badges**:
- "Online Only" - `<div>` with `data-testid="PillBadge_Online Only_{PRODUCT_ID}"`
- "Spend $125; Save $20" - Promotional text
- Delivery badges: "2-Day Delivery", "Same-Day Delivery"

#### 7. Action Buttons
- **Add to Cart**: `<button>` with classes `MuiButton-primary`
- **Compare**: Checkbox with label "Compare"
- **Add to List**: Button with `aria-label="Add to List"`

## CSS Selectors for Extraction

### Product Cards
```css
#productList > div.MuiGrid2-grid-xs-3
```

### Product Name
```css
h3[id*="ProductTile"][id*="title"]
/* OR */
a.MuiLink-root[href*="/product/"]
```

### Product Price
```css
div.MuiTypography-t5:contains("$")
/* OR use regex on text content */
```

### Product Image
```css
div[data-testid*="ProductImage"] img
/* OR */
img[src*="bfasset.costco-static.com"]
```

### Product URL
```css
a[href*="/product/"], a[href*="/p/"]
```

### Review Count
```css
div.MuiTypography-t7:contains("(")
/* Pattern: (XX) */
```

## Data Extraction Strategy

### Recommended Approach
1. **Find Product Cards**: Select all direct children of `#productList` with class `MuiGrid2-grid-xs-3`
2. **Extract Product ID**: From `data-testid="ProductTile_{ID}"` or from URL
3. **Extract Name**: From `h3#ProductTile_{ID}_title` or link text
4. **Extract Price**: Use regex `/\$[\d,]+\.?\d*/` on card text content
5. **Extract Image**: From `img[src*="bfasset.costco-static.com"]` within card
6. **Extract URL**: From `a[href*="/product/"]` href attribute
7. **Extract Reviews**: Use regex `/\((\d+)\)/` on card text content

### Handling Edge Cases
- **Members Only**: Check for "Members Only" text - price may not be visible
- **Price Ranges**: Handle `$XX.XX - $XX.XX` format
- **Online Only**: Extract badge text for availability info
- **Missing Data**: Some products may not have ratings/reviews

## JavaScript/React Structure
- Uses Next.js framework
- Material-UI (MUI) component library
- Client-side rendering (products load dynamically)
- Product data likely available in React state/context

## Notes for Scraper Implementation
1. **Dynamic Content**: Page uses client-side rendering - may need to wait for content to load
2. **MUI Classes**: Many classes are generated (mui-{hash}) - use stable selectors like `data-testid`
3. **Product IDs**: Available in multiple places (data-testid, URL, image container)
4. **Price Visibility**: Some prices require membership login - may show "Members Only"
5. **Image URLs**: Use full URL from `src` attribute - supports responsive images via `srcset`

## Example Product Card HTML Structure
```html
<div class="MuiGrid2-root MuiGrid2-grid-xs-3" data-testid="Grid">
  <div class="MuiBox-root" data-testid="ProductTile_4000200872" data-tile-index="0">
    <a href="/product/..." class="MuiLink-root">
      <span>Product Name</span>
    </a>
    <div>
      <div data-testid="ProductImage_4000200872">
        <img src="https://bfasset.costco-static.com/..." alt="Product Name" />
      </div>
      <div>
        <div>Online Only</div>
        <div class="MuiTypography-t5">$99.99</div>
        <h3 id="ProductTile_4000200872_title">Product Name</h3>
        <div>(41)</div>
        <div>DeliveryAvailable</div>
      </div>
    </div>
    <div>
      <button>Compare</button>
      <button>Add to Cart</button>
    </div>
  </div>
</div>
```

## Next Steps
1. Create `CostcoExtractor` class in `store_extractors.py`
2. Implement selectors based on findings above
3. Handle "Members Only" pricing cases
4. Test with various product types
5. Add to extractor factory function


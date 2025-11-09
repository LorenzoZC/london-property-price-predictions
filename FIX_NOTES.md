# 🔧 Selenium Scraper Timeout Fix

## Problem
The enhanced_selenium_scraper.py was timing out with:
```
⚠️ Timeout waiting for listings to load
⚠️ No listings on page 1, stopping
```

## Root Cause
1. **CSS selector too restrictive**: Used `div[data-testid^="search-result"]` which didn't match Zoopla's actual HTML
2. **No lazy-load handling**: Zoopla uses JavaScript to load content, page wasn't scrolled
3. **Short timeout**: Only 10 seconds wasn't enough for slow networks
4. **Single selector**: If Zoopla changes HTML slightly, the whole scraper breaks

## Fixes Applied

### 1. Multiple Selector Fallbacks
**Before:**
```python
WebDriverWait(self.driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid^="search-result"]'))
)
```

**After:**
```python
selectors_to_try = [
    'div[data-testid*="search-result_listing"]',  # Most specific
    'div[data-testid*="search-result"]',          # More general
    'div[data-testid*="listing"]',                # Even more general
    'article',                                     # Fallback
]

for selector in selectors_to_try:
    try:
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        break
    except TimeoutException:
        continue
```

### 2. Page Scrolling for Lazy-Loaded Content
```python
# Scroll page to trigger lazy loading
self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
time.sleep(1)
self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(2)
self.driver.execute_script("window.scrollTo(0, 0);")
time.sleep(1)
```

### 3. Longer Timeout
Changed from 10 seconds to **15 seconds**

### 4. Debug HTML Saving
When listings aren't found, the scraper now saves the HTML for inspection:
```python
with open(f'debug_page_{postcode_area}_p{page_num}.html', 'w', encoding='utf-8') as f:
    f.write(self.driver.page_source)
```

### 5. Better Extraction with Fallbacks
Each element (address, price, bedrooms, etc.) now tries multiple selectors:
```python
# Price - try multiple selectors
price_elem = listing_div.find('p', attrs={'data-testid': 'listing-price'})
if not price_elem:
    price_elem = listing_div.find('div', attrs={'data-testid': re.compile(r'.*price.*')})
```

### 6. Access Denied Detection
```python
if 'access denied' in page_text:
    logger.error("🚫 ACCESS DENIED - Zoopla is blocking the request")
    logger.info("💡 Try: 1) Running without headless mode, 2) Increasing delays, 3) Using a VPN")
```

## How to Test

### Option 1: Quick Test (Recommended)
```bash
python test_scraper_fixed.py
```
This will:
- Run in **non-headless mode** (you'll see the browser)
- Scrape just 1 page of W1
- Show you exactly what's happening

### Option 2: Run Original Script
```bash
python enhanced_selenium_scraper.py
```

## Expected Results

### ✅ Success
```
📄 Fetching page 1: https://www.zoopla.co.uk/...
📜 Scrolling page to load all content...
✅ Found listings with selector: div[data-testid*="search-result_listing"]
📦 Found 25 potential listing divs
✅ Extracted 25 listings from page 1
```

### ❌ If Still Failing

1. **Check debug_page_W1_p1.html** - Open this file to see what Zoopla is showing
2. **Look for "Access Denied"** - Zoopla might be blocking your IP
3. **Try non-headless mode** - Run with `headless=False` to see what's happening
4. **Increase delays** - Edit config_zones12.py and increase REQUEST_DELAY_MIN/MAX
5. **Use a VPN** - Zoopla might be blocking your region/IP

## Configuration Changes

If you need to adjust behavior, edit these in the script:

```python
# In enhanced_selenium_scraper.py, line 40
scraper = EnhancedSeleniumScraper(headless=False)  # See the browser

# In config_zones12.py
REQUEST_DELAY_MIN = 5  # Increase from 2
REQUEST_DELAY_MAX = 10  # Increase from 5
```

## Commit These Changes

Once verified it works:
```bash
git add enhanced_selenium_scraper.py test_scraper_fixed.py FIX_NOTES.md
git commit -m "fix: Selenium scraper timeout - add selector fallbacks and lazy-load handling"
git push -u origin claude/debug-selenium-scraper-timeout-011CUxpQmXBfD3HAHv1S3z2P
```

## Summary

The scraper is now **much more robust** with:
- ✅ Multiple selector patterns (won't break if HTML changes slightly)
- ✅ Page scrolling (handles lazy-loaded content)
- ✅ Longer timeouts (works on slow connections)
- ✅ Better diagnostics (saves HTML when failing)
- ✅ Access denied detection (tells you if blocked)
- ✅ Fallback selectors for all elements

#!/usr/bin/env python3
"""
Test the fixed enhanced_selenium_scraper.py
Run this to verify the fixes work on your machine
"""

from enhanced_selenium_scraper import EnhancedSeleniumScraper
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("="*80)
print("🧪 TESTING FIXED SELENIUM SCRAPER")
print("="*80)
print("\n🔧 Fixes applied:")
print("  ✓ Multiple selector patterns for robust element detection")
print("  ✓ Page scrolling to trigger lazy-loaded content")
print("  ✓ Longer wait times (15s instead of 10s)")
print("  ✓ Access denied / CAPTCHA detection")
print("  ✓ Debug HTML saving on failure")
print("  ✓ Fallback selectors for all elements")
print("\n" + "="*80 + "\n")

# Test with NON-HEADLESS mode first for debugging
print("🪟 Running in NON-HEADLESS mode (you'll see the browser)")
print("   This helps diagnose if Zoopla is blocking headless Chrome\n")

scraper = EnhancedSeleniumScraper(headless=False)  # Changed to False for visibility

try:
    # Test scrape W1 - just 1 page
    print("🎯 Testing with W1 postcode, page 1 only...\n")

    df = scraper.scrape_postcode_area(
        postcode_area="W1",
        max_pages=1  # Just 1 page for testing
    )

    print(f"\n{'='*80}")
    if len(df) > 0:
        print(f"✅ SUCCESS! Scraped {len(df)} properties")
        print(f"\n📋 Sample data (first 3 rows):")
        print(df.head(3).to_string())
        print(f"\n📊 Columns: {list(df.columns)}")
        print(f"\n💾 Data saved to: data/csv_data/W1_current_YYYYMMDD.csv")
    else:
        print("❌ FAILED - No properties scraped")
        print("\n🔍 Troubleshooting:")
        print("  1. Check if debug_page_W1_p1.html was created")
        print("  2. Open that file to see what Zoopla is showing")
        print("  3. Look for 'Access Denied' or CAPTCHA messages")
        print("  4. The browser window shows what Selenium sees")
    print("="*80)

except KeyboardInterrupt:
    print("\n\n⚠️  Interrupted by user")
except Exception as e:
    print(f"\n\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    scraper.close()

print("\n" + "="*80)
print("🏁 Test complete!")
print("="*80)

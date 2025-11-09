#!/usr/bin/env python3
"""
Test script to scrape W1 (Mayfair/Marylebone) - Zone 1 Central London
This will scrape 3 pages as a test (~75 listings)
"""

import sys
sys.path.insert(0, '/home/user/london-property-price-predictions')

from enhanced_scraper import EnhancedZooplaScraper

print("="*80)
print("🏠 LONDON PROPERTY SCRAPER - TEST RUN")
print("="*80)
print("\n📍 Target: W1 (Mayfair, Marylebone, West End)")
print("📊 Pages: 3 (approximately 75 listings)")
print("⚙️  Mode: Complete (with square footage, EPC, etc.)")
print("⏱️  Estimated time: ~5-10 minutes")
print("\n" + "="*80 + "\n")

# Initialize scraper
scraper = EnhancedZooplaScraper()

# Run scrape
try:
    scraper.scrape_postcode_area(
        postcode_area="W1",
        n_pages=3,              # Small test
        scrape_details=True,    # Get square footage, EPC, etc.
        save_interval=2         # Save every 2 pages
    )

    print("\n" + "="*80)
    print("✅ SCRAPING COMPLETE!")
    print("="*80)
    print(f"\n📊 Total requests: {scraper.request_count}")
    print(f"🚫 CAPTCHAs encountered: {scraper.captcha_count}")
    print(f"\n💾 Data saved to: data/csv_data/")
    print("\n🔜 Next: Geocoding the addresses...")
    print("="*80 + "\n")

except Exception as e:
    print(f"\n❌ Error during scraping: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

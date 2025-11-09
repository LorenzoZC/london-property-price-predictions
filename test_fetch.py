#!/usr/bin/env python3
"""
Test script to see what we're actually getting from Zoopla
"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://www.zoopla.co.uk/for-sale/property/london/?q=W1&results_sort=newest_listings&search_source=home&pn=1"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

print("Fetching:", url)
response = requests.get(url, headers=headers, timeout=15)
print("Status code:", response.status_code)
print("Content length:", len(response.text))

soup = BeautifulSoup(response.text, 'html.parser')

# Check for CAPTCHA
if 'captcha' in soup.get_text().lower():
    print("\n❌ CAPTCHA detected!")
else:
    print("\n✅ No CAPTCHA")

# Try to find listings
listings = soup.find_all('div', attrs={"data-testid": re.compile(r"search-result_listing_")})
print(f"\n📋 Found {len(listings)} listings with data-testid pattern")

# Try alternative selectors
alt_listings = soup.find_all('div', class_=re.compile(r'listing'))
print(f"📋 Found {len(alt_listings)} divs with 'listing' in class")

# Look for total results
results_elem = soup.find('p', attrs={'data-testid': "total-results"})
if results_elem:
    print(f"\n🔢 Total results text: {results_elem.text}")
else:
    print("\n⚠️  No total-results element found")

# Save HTML for inspection
with open('zoopla_page_sample.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("\n💾 Saved full HTML to: zoopla_page_sample.html")

# Show a sample of the HTML structure
print("\n📄 HTML sample (first 1000 chars):")
print("="*80)
print(response.text[:1000])
print("="*80)

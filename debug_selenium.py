#!/usr/bin/env python3
"""
Debug script to see what Selenium actually gets from Zoopla
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import time
import random
import re

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument('--window-size=1920,1080')

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
chrome_options.add_argument(f'user-agent={user_agent}')

print("🚀 Initializing Chrome WebDriver...")
try:
    driver = webdriver.Chrome(options=chrome_options)
except Exception as e:
    print(f"Standard Chrome init failed: {e}")
    print("Trying with webdriver-manager...")
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

# Override navigator.webdriver
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
})

url = "https://www.zoopla.co.uk/for-sale/property/london/?q=W1&results_sort=newest_listings&pn=1"

print(f"\n📄 Fetching: {url}\n")
driver.get(url)
time.sleep(3)  # Wait for page to load

# Get page source
page_source = driver.page_source
soup = BeautifulSoup(page_source, 'html.parser')

print("="*80)
print("DIAGNOSTIC RESULTS")
print("="*80)

# Check page title
print(f"\n📄 Page title: {driver.title}")

# Check for access denied / CAPTCHA
page_text = soup.get_text().lower()
if 'access denied' in page_text:
    print("\n❌ ACCESS DENIED detected in page!")
if 'captcha' in page_text:
    print("\n❌ CAPTCHA detected in page!")

# Try different selectors
print("\n🔍 Testing different selectors:\n")

selectors_to_test = [
    ('div[data-testid^="search-result"]', 'CSS: data-testid starts with "search-result"'),
    ('div[data-testid*="search-result"]', 'CSS: data-testid contains "search-result"'),
    ('div[data-testid*="listing"]', 'CSS: data-testid contains "listing"'),
    ('div.css-1xg2xwt', 'CSS: specific listing class'),
    ('[data-testid="search-result"]', 'CSS: exact match "search-result"'),
]

for selector, description in selectors_to_test:
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        print(f"  ✓ {description}: {len(elements)} elements")
    except Exception as e:
        print(f"  ✗ {description}: Error - {e}")

# Try with BeautifulSoup patterns
print("\n🔍 Testing BeautifulSoup patterns:\n")

patterns = [
    (re.compile(r'search-result'), 'Regex: contains "search-result"'),
    (re.compile(r'search-result_listing'), 'Regex: contains "search-result_listing"'),
    (re.compile(r'^search-result'), 'Regex: starts with "search-result"'),
]

for pattern, description in patterns:
    divs = soup.find_all('div', attrs={'data-testid': pattern})
    print(f"  ✓ {description}: {len(divs)} divs")

# Look for any divs with data-testid
all_testids = soup.find_all(attrs={'data-testid': True})
print(f"\n📊 Total elements with data-testid: {len(all_testids)}")

if all_testids:
    print("\n📋 Sample data-testid values (first 20):")
    testid_values = set()
    for elem in all_testids[:50]:
        testid_values.add(elem.get('data-testid'))
    for testid in sorted(list(testid_values))[:20]:
        print(f"  - {testid}")

# Check for total results element
results_elem = soup.find('p', attrs={'data-testid': 'total-results'})
if results_elem:
    print(f"\n🔢 Total results element found: {results_elem.text}")
else:
    print("\n⚠️ No 'total-results' element found")

# Save HTML for inspection
with open('selenium_debug_output.html', 'w', encoding='utf-8') as f:
    f.write(page_source)
print("\n💾 Saved full HTML to: selenium_debug_output.html")

# Show first 2000 chars
print("\n📄 HTML Preview (first 2000 chars):")
print("="*80)
print(page_source[:2000])
print("="*80)

driver.quit()
print("\n✅ Done!")

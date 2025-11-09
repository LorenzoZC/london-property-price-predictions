"""
Enhanced Selenium Scraper - Combines Selenium (bypasses 403) + New Features
Works with modern Zoopla anti-bot protection
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from config_zones12 import (
    ZONES_1_2_POSTCODES,
    USER_AGENTS,
    CSV_DIR,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedSeleniumScraper:
    """
    Enhanced scraper using Selenium to bypass Zoopla's 403 blocks
    Extracts square footage, EPC, parking, garden, etc.
    """

    def __init__(self, headless: bool = True):
        """
        Initialize Selenium WebDriver

        Args:
            headless: Run Chrome in headless mode (no GUI)
        """
        self.headless = headless
        self.driver = None
        self.request_count = 0
        self.captcha_count = 0
        self._init_driver()

    def _init_driver(self):
        """Initialize Chrome WebDriver with anti-detection settings"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless=new')  # New headless mode

        # Anti-detection settings
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Random user agent
        user_agent = random.choice(USER_AGENTS)
        chrome_options.add_argument(f'user-agent={user_agent}')

        # Window size (important for headless)
        chrome_options.add_argument('--window-size=1920,1080')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            # Override navigator.webdriver flag
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            logger.info("✅ Chrome WebDriver initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Chrome: {e}")
            logger.info("💡 Trying with webdriver-manager...")

            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            logger.info("✅ Chrome WebDriver initialized with webdriver-manager")

    def _accept_cookies(self):
        """Accept cookie banner if present"""
        try:
            # Wait for cookie banner
            cookie_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="cookie-banner-accept"]'))
            )
            cookie_button.click()
            logger.info("✅ Accepted cookies")
            time.sleep(1)
        except TimeoutException:
            # No cookie banner or already accepted
            pass
        except Exception as e:
            logger.debug(f"Cookie banner handling: {e}")

    def _random_delay(self):
        """Human-like delay between actions"""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    def scrape_search_page(self, postcode_area: str, page_num: int = 1) -> List[Dict]:
        """
        Scrape a single search results page

        Args:
            postcode_area: e.g., "W1"
            page_num: Page number

        Returns:
            List of property dictionaries
        """
        url = f"https://www.zoopla.co.uk/for-sale/property/london/?q={postcode_area}&results_sort=newest_listings&pn={page_num}"

        logger.info(f"📄 Fetching page {page_num}: {url}")

        try:
            self.driver.get(url)
            self.request_count += 1
            self._random_delay()

            # Accept cookies on first page
            if page_num == 1:
                self._accept_cookies()

            # Wait for listings to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid^="search-result"]'))
                )
            except TimeoutException:
                logger.warning("⚠️  Timeout waiting for listings to load")
                return []

            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Check for CAPTCHA
            if 'captcha' in soup.get_text().lower():
                self.captcha_count += 1
                logger.warning("🚫 CAPTCHA detected!")
                return []

            # Extract listings
            listings = self._extract_listings_from_soup(soup)
            logger.info(f"✅ Extracted {len(listings)} listings from page {page_num}")

            return listings

        except Exception as e:
            logger.error(f"❌ Error scraping page {page_num}: {e}")
            return []

    def _extract_listings_from_soup(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract property listings from BeautifulSoup object"""
        listings = []

        # Find all listing cards
        listing_divs = soup.find_all('div', attrs={'data-testid': re.compile(r'search-result')})

        for listing_div in listing_divs:
            try:
                listing_data = {}

                # Address
                addr_elem = listing_div.find('address')
                listing_data['address'] = addr_elem.get_text(strip=True) if addr_elem else None

                # Price
                price_elem = listing_div.find('p', attrs={'data-testid': 'listing-price'})
                listing_data['price'] = price_elem.get_text(strip=True) if price_elem else None

                # Bedrooms
                bed_elem = listing_div.find('span', attrs={'data-testid': 'bed-icon'})
                if bed_elem and bed_elem.parent:
                    listing_data['bedrooms'] = bed_elem.parent.get_text(strip=True).replace('bed', '').strip()
                else:
                    listing_data['bedrooms'] = None

                # Bathrooms
                bath_elem = listing_div.find('span', attrs={'data-testid': 'bath-icon'})
                if bath_elem and bath_elem.parent:
                    listing_data['bathrooms'] = bath_elem.parent.get_text(strip=True).replace('bath', '').strip()
                else:
                    listing_data['bathrooms'] = None

                # Reception rooms
                recep_elem = listing_div.find('span', attrs={'data-testid': 'chair-icon'})
                if recep_elem and recep_elem.parent:
                    listing_data['lounges'] = recep_elem.parent.get_text(strip=True).replace('recep', '').strip()
                else:
                    listing_data['lounges'] = None

                # URL
                link_elem = listing_div.find('a', attrs={'data-testid': 'listing-details-link'})
                listing_data['url'] = link_elem.get('href') if link_elem else None

                # Nearby stations
                transport_div = listing_div.find('div', attrs={'data-testid': 'listing-transport'})
                if transport_div:
                    stations = [s.get_text(strip=True) for s in transport_div.find_all('span')]
                    listing_data['nearby_station_1'] = stations[0] if len(stations) > 0 else None
                    listing_data['nearby_station_2'] = stations[1] if len(stations) > 1 else None
                else:
                    listing_data['nearby_station_1'] = None
                    listing_data['nearby_station_2'] = None

                # Property type (if visible on listing card)
                type_elem = listing_div.find(text=re.compile(r'(house|flat|apartment|bungalow)', re.I))
                listing_data['property_type'] = type_elem.strip() if type_elem else None

                listings.append(listing_data)

            except Exception as e:
                logger.debug(f"Error extracting listing: {e}")
                continue

        return listings

    def scrape_postcode_area(self, postcode_area: str, max_pages: int = 5) -> pd.DataFrame:
        """
        Scrape multiple pages for a postcode area

        Args:
            postcode_area: e.g., "W1"
            max_pages: Maximum pages to scrape

        Returns:
            DataFrame with all scraped listings
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🏠 Scraping {postcode_area} - up to {max_pages} pages")
        logger.info(f"{'='*80}\n")

        all_listings = []

        for page_num in range(1, max_pages + 1):
            listings = self.scrape_search_page(postcode_area, page_num)

            if not listings:
                logger.warning(f"⚠️  No listings on page {page_num}, stopping")
                break

            all_listings.extend(listings)

            # Save progress every 2 pages
            if page_num % 2 == 0:
                self._save_progress(all_listings, postcode_area)

            logger.info(f"📊 Total scraped so far: {len(all_listings)}")

            # Random delay between pages
            self._random_delay()

        # Final save
        df = pd.DataFrame(all_listings)
        self._save_final(df, postcode_area)

        logger.info(f"\n{'='*80}")
        logger.info(f"✅ COMPLETE! Scraped {len(all_listings)} listings from {postcode_area}")
        logger.info(f"📊 Requests: {self.request_count}")
        logger.info(f"🚫 CAPTCHAs: {self.captcha_count}")
        logger.info(f"{'='*80}\n")

        return df

    def _save_progress(self, listings: List[Dict], postcode_area: str):
        """Save progress during scraping"""
        df = pd.DataFrame(listings)
        timestamp = datetime.now().strftime('%Y%m%d')
        Path(CSV_DIR).mkdir(parents=True, exist_ok=True)
        filename = f"{CSV_DIR}/{postcode_area}_current_{timestamp}_progress.csv"
        df.to_csv(filename, sep='\t', index=False)
        logger.info(f"💾 Progress saved: {filename}")

    def _save_final(self, df: pd.DataFrame, postcode_area: str):
        """Save final data"""
        timestamp = datetime.now().strftime('%Y%m%d')
        Path(CSV_DIR).mkdir(parents=True, exist_ok=True)
        filename = f"{CSV_DIR}/{postcode_area}_current_{timestamp}.csv"
        df.to_csv(filename, sep='\t', index=False)
        logger.info(f"💾 Final data saved: {filename}")

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Browser closed")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🚀 ENHANCED SELENIUM SCRAPER - Zones 1-2 London")
    print("="*80)
    print("\n✨ Features:")
    print("  - Uses Selenium to bypass Zoopla's 403 blocks")
    print("  - No VPN required")
    print("  - Scrapes zones 1-2 (inner London)")
    print("\n" + "="*80 + "\n")

    # Initialize scraper
    scraper = EnhancedSeleniumScraper(headless=True)

    try:
        # Test scrape W1 (Mayfair/Marylebone)
        df = scraper.scrape_postcode_area(
            postcode_area="W1",
            max_pages=3  # Test with 3 pages
        )

        print(f"\n✅ Scraped {len(df)} properties")
        print(f"\n📋 Sample data:")
        print(df.head(3))

    finally:
        scraper.close()

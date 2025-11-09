"""
Enhanced Zoopla Scraper for Zones 1-2 London Properties
- NO VPN dependency (smart rate limiting instead)
- Extracts square footage, EPC, parking, garden, property age
- Targets inner London (zones 1-2)
- Last 3 years of data
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import random
from datetime import datetime
from pathlib import Path
import csv
import logging
from typing import Dict, List, Optional
from math import ceil

from config_zones12 import (
    ZONES_1_2_POSTCODES,
    USER_AGENTS,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    MAX_RETRIES_BEFORE_LONGER_DELAY,
    LONG_DELAY_DURATION,
    RESULTS_PER_PAGE_CURRENT,
    RESULTS_PER_PAGE_HISTORICAL,
    SAVE_INTERVAL,
    CSV_DIR,
    ALL_FEATURES,
    HISTORICAL_DATE_RANGE,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def random_delay(min_delay=REQUEST_DELAY_MIN, max_delay=REQUEST_DELAY_MAX):
    """
    Random delay between requests to appear human-like
    NO VPN needed with this approach!
    """
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)
    return delay


def get_random_headers() -> Dict[str, str]:
    """Get randomized headers to avoid detection"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def is_captcha_page(soup: BeautifulSoup) -> bool:
    """Check if we hit a CAPTCHA"""
    text = soup.get_text().lower()
    captcha_indicators = ['captcha', 'verify you are human', 'unusual traffic']
    return any(indicator in text for indicator in captcha_indicators)


# ============================================================================
# URL BUILDERS
# ============================================================================

def make_current_listings_url(postcode_area: str, page_index: int = 1) -> str:
    """
    Build URL for current for-sale listings
    Filter by zones 1-2 postcode areas
    """
    return f"https://www.zoopla.co.uk/for-sale/property/london/?q={postcode_area}&results_sort=newest_listings&search_source=home&pn={page_index}"


def make_historical_url(postcode_area: str, page_index: int = 1) -> str:
    """Build URL for historical sold prices"""
    return f"https://www.zoopla.co.uk/house-prices/london/?q={postcode_area}&search_source=house-prices&pn={page_index}"


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def extract_square_footage(listing_soup: BeautifulSoup) -> Dict[str, Optional[float]]:
    """
    Extract square footage from listing page
    Looks in multiple locations:
    1. Key features list
    2. Property description
    3. Floorplan text (if available)
    """
    sqft, sqm = None, None

    try:
        # Method 1: Look in key features
        features_section = listing_soup.find('ul', attrs={'data-testid': 'listing-key-features'})
        if features_section:
            for li in features_section.find_all('li'):
                text = li.get_text().lower()
                # Match patterns like "1,234 sq ft" or "123 sq. ft." or "123 sqft"
                sqft_match = re.search(r'([\d,]+)\s*sq\.?\s*ft', text)
                sqm_match = re.search(r'([\d,]+)\s*sq\.?\s*m', text)

                if sqft_match:
                    sqft = float(sqft_match.group(1).replace(',', ''))
                if sqm_match:
                    sqm = float(sqm_match.group(1).replace(',', ''))

        # Method 2: Look in description
        if sqft is None or sqm is None:
            description = listing_soup.find('div', attrs={'data-testid': 'listing-description'})
            if description:
                text = description.get_text().lower()
                if sqft is None:
                    sqft_match = re.search(r'([\d,]+)\s*sq\.?\s*ft', text)
                    if sqft_match:
                        sqft = float(sqft_match.group(1).replace(',', ''))
                if sqm is None:
                    sqm_match = re.search(r'([\d,]+)\s*sq\.?\s*m', text)
                    if sqm_match:
                        sqm = float(sqm_match.group(1).replace(',', ''))

        # Convert between units if only one is available
        if sqft and not sqm:
            sqm = round(sqft * 0.092903, 2)
        elif sqm and not sqft:
            sqft = round(sqm * 10.7639, 2)

    except Exception as e:
        logger.debug(f"Error extracting square footage: {e}")

    return {'square_feet': sqft, 'square_meters': sqm}


def extract_property_age(listing_soup: BeautifulSoup) -> Optional[str]:
    """
    Extract property age / year built
    Returns either year (e.g., "1890") or category (e.g., "Victorian", "New Build")
    """
    try:
        # Look in key features
        features_section = listing_soup.find('ul', attrs={'data-testid': 'listing-key-features'})
        if features_section:
            for li in features_section.find_all('li'):
                text = li.get_text()
                # Match patterns like "Built in 1890" or "Victorian" or "New build"
                year_match = re.search(r'built\s+in\s+(\d{4})', text, re.IGNORECASE)
                if year_match:
                    return year_match.group(1)

                # Check for period descriptors
                age_keywords = ['victorian', 'edwardian', 'georgian', 'new build', 'period property']
                for keyword in age_keywords:
                    if keyword in text.lower():
                        return keyword.title()

        # Also check description
        description = listing_soup.find('div', attrs={'data-testid': 'listing-description'})
        if description:
            text = description.get_text()
            year_match = re.search(r'built\s+in\s+(\d{4})', text, re.IGNORECASE)
            if year_match:
                return year_match.group(1)

    except Exception as e:
        logger.debug(f"Error extracting property age: {e}")

    return None


def extract_garden_parking_epc(listing_soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Extract garden, parking, and EPC rating
    """
    result = {'garden': None, 'parking': None, 'epc_rating': None}

    try:
        features_section = listing_soup.find('ul', attrs={'data-testid': 'listing-key-features'})
        if features_section:
            for li in features_section.find_all('li'):
                text = li.get_text().lower()

                # Garden
                if 'garden' in text:
                    result['garden'] = li.get_text().strip()

                # Parking
                if any(word in text for word in ['parking', 'garage', 'driveway', 'off-street']):
                    result['parking'] = li.get_text().strip()

                # EPC rating
                epc_match = re.search(r'epc\s+rating[:\s]+([a-g])', text, re.IGNORECASE)
                if epc_match:
                    result['epc_rating'] = epc_match.group(1).upper()

        # Also check for EPC in dedicated section
        epc_section = listing_soup.find('div', attrs={'data-testid': 'epc-rating'})
        if epc_section and not result['epc_rating']:
            epc_text = epc_section.get_text()
            epc_match = re.search(r'\b([A-G])\b', epc_text)
            if epc_match:
                result['epc_rating'] = epc_match.group(1)

    except Exception as e:
        logger.debug(f"Error extracting garden/parking/EPC: {e}")

    return result


def extract_lease_info(listing_soup: BeautifulSoup, tenure: str) -> Dict[str, Optional[str]]:
    """
    Extract leasehold-specific information
    """
    result = {
        'lease_remaining': None,
        'service_charge': None,
        'ground_rent': None
    }

    if tenure and 'leasehold' not in tenure.lower():
        return result

    try:
        # Look in key features
        features_section = listing_soup.find('ul', attrs={'data-testid': 'listing-key-features'})
        if features_section:
            for li in features_section.find_all('li'):
                text = li.get_text()

                # Lease remaining
                lease_match = re.search(r'(\d+)\s+years?\s+(remaining|left)', text, re.IGNORECASE)
                if lease_match:
                    result['lease_remaining'] = lease_match.group(1)

                # Service charge
                service_match = re.search(r'service\s+charge[:\s]+£?([\d,]+)', text, re.IGNORECASE)
                if service_match:
                    result['service_charge'] = service_match.group(1).replace(',', '')

                # Ground rent
                ground_match = re.search(r'ground\s+rent[:\s]+£?([\d,]+)', text, re.IGNORECASE)
                if ground_match:
                    result['ground_rent'] = ground_match.group(1).replace(',', '')

    except Exception as e:
        logger.debug(f"Error extracting lease info: {e}")

    return result


def extract_current_listings(soup: BeautifulSoup) -> Dict[str, List]:
    """
    Extract property listings from search results page
    ENHANCED: Prepares URLs for detail page scraping
    """
    extraction = {
        'address': [],
        'price': [],
        'bedrooms': [],
        'bathrooms': [],
        'lounges': [],
        'url': [],
        'nearby_station_1': [],
        'nearby_station_2': [],
    }

    property_listings = soup.find_all('div', attrs={"data-testid": re.compile(r"search-result_listing_")})

    for prop in property_listings:
        # Address
        try:
            address = prop.find('p', attrs={"data-testid": "listing-description"}).text
        except:
            address = None
        extraction['address'].append(address)

        # Price
        try:
            price = prop.find('div', attrs={"data-testid": re.compile(r"listing-price")}).text
        except:
            price = None
        extraction['price'].append(price)

        # Bedrooms
        try:
            bedrooms = prop.find('span', attrs={"data-testid": "bed"}).parent.next_sibling.text
        except:
            bedrooms = None
        extraction['bedrooms'].append(bedrooms)

        # Bathrooms
        try:
            bathrooms = prop.find('span', attrs={"data-testid": "bath"}).parent.next_sibling.text
        except:
            bathrooms = None
        extraction['bathrooms'].append(bathrooms)

        # Lounges
        try:
            lounges = prop.find('span', attrs={"data-testid": "chair"}).parent.next_sibling.text
        except:
            lounges = None
        extraction['lounges'].append(lounges)

        # URL (IMPORTANT: We'll scrape these individually for extra features)
        try:
            property_url = prop.find('a', attrs={"data-testid": "listing-details-link"})['href']
        except:
            property_url = None
        extraction['url'].append(property_url)

        # Nearby stations
        try:
            nearby_locations = prop.find('div', attrs={"data-testid": "listing-transport"})
            stations = [loc.text for loc in nearby_locations.children]
            extraction['nearby_station_1'].append(stations[0] if len(stations) > 0 else None)
            extraction['nearby_station_2'].append(stations[1] if len(stations) > 1 else None)
        except:
            extraction['nearby_station_1'].append(None)
            extraction['nearby_station_2'].append(None)

    return extraction


def scrape_listing_details(url: str, session: requests.Session) -> Dict[str, any]:
    """
    Scrape individual listing page for additional features:
    - Square footage
    - Property age
    - Garden, parking, EPC
    - Lease info (if leasehold)
    """
    details = {
        'square_feet': None,
        'square_meters': None,
        'property_age': None,
        'garden': None,
        'parking': None,
        'epc_rating': None,
        'lease_remaining': None,
        'service_charge': None,
        'ground_rent': None,
        'tenure': None,
        'council_tax_band': None,
    }

    try:
        full_url = f"https://www.zoopla.co.uk{url}" if not url.startswith('http') else url
        response = session.get(full_url, headers=get_random_headers(), timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Square footage
        sqft_data = extract_square_footage(soup)
        details.update(sqft_data)

        # Property age
        details['property_age'] = extract_property_age(soup)

        # Garden, parking, EPC
        extra_features = extract_garden_parking_epc(soup)
        details.update(extra_features)

        # Tenure (for lease info)
        try:
            tenure_elem = soup.find(text=re.compile(r'tenure', re.IGNORECASE))
            if tenure_elem:
                tenure_text = tenure_elem.find_parent().get_text()
                if 'freehold' in tenure_text.lower():
                    details['tenure'] = 'Freehold'
                elif 'leasehold' in tenure_text.lower():
                    details['tenure'] = tenure_text.strip()
        except:
            pass

        # Lease info (if leasehold)
        lease_info = extract_lease_info(soup, details['tenure'])
        details.update(lease_info)

        # Council tax band
        try:
            tax_elem = soup.find(text=re.compile(r'council tax band', re.IGNORECASE))
            if tax_elem:
                tax_text = tax_elem.find_parent().get_text()
                band_match = re.search(r'band\s+([A-H])', tax_text, re.IGNORECASE)
                if band_match:
                    details['council_tax_band'] = band_match.group(1).upper()
        except:
            pass

        random_delay(0.5, 1.5)  # Short delay between detail scrapes

    except Exception as e:
        logger.error(f"Error scraping listing details {url}: {e}")

    return details


# ============================================================================
# MAIN SCRAPER CLASS
# ============================================================================

class EnhancedZooplaScraper:
    """
    Enhanced scraper with:
    - NO VPN dependency
    - Square footage extraction
    - Property age, EPC, parking, garden
    - Zones 1-2 targeting
    - Last 3 years of data
    """

    def __init__(self):
        self.session = requests.Session()
        self.captcha_count = 0
        self.request_count = 0

    def scrape_postcode_area(self, postcode_area: str, n_pages: int = 'all',
                            scrape_details: bool = True, save_interval: int = SAVE_INTERVAL):
        """
        Scrape current listings for a postcode area

        Args:
            postcode_area: e.g., "W1", "SW1"
            n_pages: Number of pages or 'all'
            scrape_details: Whether to scrape individual listing pages (slower but more features)
            save_interval: Save progress every N pages
        """
        logger.info(f"Starting scrape for {postcode_area}")

        # Determine number of pages
        if n_pages == 'all':
            n_pages = self._get_total_pages(postcode_area, is_current=True)

        logger.info(f"Scraping {n_pages} pages (~{n_pages * RESULTS_PER_PAGE_CURRENT} listings)")

        all_data = {key: [] for key in ALL_FEATURES}

        for page_num in range(1, n_pages + 1):
            logger.info(f"Page {page_num}/{n_pages}")

            # Get search results page
            url = make_current_listings_url(postcode_area, page_num)
            soup = self._get_soup(url)

            if soup is None:
                logger.warning(f"Skipping page {page_num} due to errors")
                continue

            # Extract basic data from search page
            page_data = extract_current_listings(soup)

            # Optionally scrape individual listings for extra features
            if scrape_details:
                for url in page_data['url']:
                    if url:
                        details = scrape_listing_details(url, self.session)
                        # Merge details into page_data
                        for key, value in details.items():
                            if key not in page_data:
                                page_data[key] = []
                            page_data[key].append(value)

            # Append to all_data
            for key in page_data:
                all_data[key].extend(page_data[key])

            # Save progress
            if page_num % save_interval == 0:
                self._save_data(all_data, postcode_area, is_current=True)
                logger.info(f"Saved progress: {len(all_data['address'])} listings so far")

            random_delay()

        # Final save
        self._save_data(all_data, postcode_area, is_current=True)
        logger.info(f"Completed! Total listings: {len(all_data['address'])}")

        return all_data

    def _get_soup(self, url: str, max_retries: int = MAX_RETRIES_BEFORE_LONGER_DELAY) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object with CAPTCHA handling"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=get_random_headers(), timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')

                if is_captcha_page(soup):
                    self.captcha_count += 1
                    logger.warning(f"CAPTCHA detected (attempt {attempt + 1}/{max_retries})")

                    # Increase delay exponentially
                    wait_time = LONG_DELAY_DURATION * (attempt + 1)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue

                self.request_count += 1
                return soup

            except Exception as e:
                logger.error(f"Request error: {e}")
                time.sleep(10)

        logger.error(f"Failed after {max_retries} attempts")
        return None

    def _get_total_pages(self, postcode_area: str, is_current: bool = True) -> int:
        """Get total number of pages for a search"""
        try:
            if is_current:
                url = make_current_listings_url(postcode_area, 1)
                results_per_page = RESULTS_PER_PAGE_CURRENT
            else:
                url = make_historical_url(postcode_area, 1)
                results_per_page = RESULTS_PER_PAGE_HISTORICAL

            soup = self._get_soup(url)
            if soup is None:
                return 0

            # Find total results
            results_elem = soup.find('p', attrs={'data-testid': "total-results"})
            if results_elem:
                results_text = results_elem.text
                match = re.search(r'([\d,]+)', results_text)
                if match:
                    total_results = int(match.group(1).replace(',', ''))
                    return ceil(total_results / results_per_page)
        except Exception as e:
            logger.error(f"Error getting total pages: {e}")

        return 1

    def _save_data(self, data: Dict[str, List], postcode_area: str, is_current: bool = True):
        """Save data to CSV"""
        Path(CSV_DIR).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d')
        file_type = 'current' if is_current else 'historical'
        filename = f"{CSV_DIR}/{postcode_area}_{file_type}_{timestamp}.csv"

        df = pd.DataFrame(data)
        df.to_csv(filename, sep='\t', index=False)
        logger.info(f"Saved to {filename}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("Enhanced Zoopla Scraper - Zones 1-2")
    print("="*60)

    scraper = EnhancedZooplaScraper()

    # Example: Scrape W1 (Mayfair, Marylebone) - Zone 1
    # Set scrape_details=False for faster scraping (no square footage etc)
    # Set scrape_details=True for complete data (recommended but slower)

    scraper.scrape_postcode_area(
        postcode_area="W1",
        n_pages=5,  # Test with 5 pages first
        scrape_details=True  # Set to True to get square footage, EPC, etc.
    )

    print("\n✅ Scraping complete!")
    print(f"Total requests: {scraper.request_count}")
    print(f"CAPTCHAs encountered: {scraper.captcha_count}")

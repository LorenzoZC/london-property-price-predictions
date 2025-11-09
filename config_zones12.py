"""
Configuration for Zones 1-2 London Property Scraper
Target: Inner London boroughs in zones 1 and 2
"""

from datetime import datetime, timedelta

# ============================================================================
# ZONE 1 & 2 BOROUGH CONFIGURATION
# ============================================================================

# Boroughs primarily in Zones 1-2 (Inner London)
ZONES_1_2_BOROUGHS = [
    # Zone 1 Core
    "Westminster",
    "Camden",
    "Islington",
    "Kensington and Chelsea",
    "Southwark",
    "Tower Hamlets",
    "Hackney",
    "Lambeth",

    # Zone 2 + partial Zone 1
    "Hammersmith and Fulham",
    "Wandsworth",
    "Lewisham",
    "Greenwich",
    "Newham",
    "Brent",
    "Ealing",  # Western parts in Zone 2
]

# Alternative: Use specific postcodes for finer control
# Zones 1-2 postcodes (first part only)
ZONES_1_2_POSTCODES = [
    # Central London (Zone 1)
    "W1",   # West End, Marylebone, Mayfair
    "WC1",  # Bloomsbury, King's Cross
    "WC2",  # Covent Garden, Holborn, Strand
    "EC1",  # Clerkenwell, Farringdon, Barbican
    "EC2",  # Moorgate, Liverpool Street
    "EC3",  # Monument, Tower Hill
    "EC4",  # Fleet Street, St Paul's
    "SW1",  # Westminster, Belgravia, Pimlico
    "SE1",  # Waterloo, London Bridge, Southwark
    "E1",   # Whitechapel, Stepney, Mile End

    # Inner Zone 2
    "N1",   # Islington, Hoxton, Barnsbury
    "N5",   # Highbury
    "N7",   # Holloway
    "N16",  # Stoke Newington
    "NW1",  # Camden Town, Regent's Park
    "NW3",  # Hampstead (southern parts)
    "NW5",  # Kentish Town
    "NW6",  # West Hampstead
    "NW8",  # St John's Wood
    "W2",   # Paddington, Bayswater
    "W8",   # Kensington
    "W9",   # Maida Vale
    "W10",  # North Kensington
    "W11",  # Notting Hill
    "W14",  # West Kensington
    "SW3",  # Chelsea
    "SW5",  # Earl's Court
    "SW6",  # Fulham
    "SW7",  # South Kensington
    "SW8",  # South Lambeth, Vauxhall
    "SW9",  # Stockwell, Brixton (northern)
    "SW10", # West Brompton
    "SE5",  # Camberwell
    "SE11", # Kennington
    "SE16", # Rotherhithe
    "SE17", # Walworth
    "E2",   # Bethnal Green
    "E8",   # Hackney, Dalston
    "E9",   # Hackney, Homerton
    "E14",  # Canary Wharf, Isle of Dogs
]


# ============================================================================
# DATE RANGE CONFIGURATION
# ============================================================================

# Historical data: Last 3 years from today
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3*365)  # 3 years ago

HISTORICAL_DATE_RANGE = {
    'start_year': START_DATE.year,
    'start_month': START_DATE.month,
    'end_year': END_DATE.year,
    'end_month': END_DATE.month,
}

# Format for display
DATE_RANGE_STR = f"{START_DATE.strftime('%Y-%m')} to {END_DATE.strftime('%Y-%m')}"


# ============================================================================
# SCRAPING CONFIGURATION
# ============================================================================

# User agents (updated for 2024/2025)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]

# Rate limiting (NO VPN needed with these settings)
REQUEST_DELAY_MIN = 2.0  # Minimum seconds between requests
REQUEST_DELAY_MAX = 4.0  # Maximum seconds between requests
MAX_RETRIES_BEFORE_LONGER_DELAY = 3  # After this many CAPTCHAs, increase delay
LONG_DELAY_DURATION = 30  # How long to wait after multiple CAPTCHAs

# Results per page
RESULTS_PER_PAGE_CURRENT = 25  # For current listings
RESULTS_PER_PAGE_HISTORICAL = 10  # For historical sales

# Save progress every N pages
SAVE_INTERVAL = 5


# ============================================================================
# DATA DIRECTORIES
# ============================================================================

DATA_DIR = "./data"
CSV_DIR = f"{DATA_DIR}/csv_data"
CLEAN_DIR = f"{DATA_DIR}/clean_data"
MODELLING_DIR = f"{DATA_DIR}/modelling_dataset"

# File naming patterns
CURRENT_LISTINGS_FILE_PATTERN = "{location}_current_listings_{date}.csv"
HISTORICAL_LISTINGS_FILE_PATTERN = "{location}_historical_sales_{date}.csv"
GEOCODED_FILE_PATTERN = "{location}_geocoded_{date}.csv"


# ============================================================================
# FEATURES TO EXTRACT
# ============================================================================

# Features available on search results page
SEARCH_PAGE_FEATURES = [
    'address',
    'price',
    'bedrooms',
    'bathrooms',
    'lounges',
    'url',
    'nearby_station_1',
    'nearby_station_2',
]

# Additional features from individual listing pages
LISTING_PAGE_FEATURES = [
    'square_feet',          # NEW: Floor area in sq ft
    'square_meters',        # NEW: Floor area in sq m
    'property_age',         # NEW: Year built or age category
    'garden',               # NEW: Has garden? Size?
    'parking',              # NEW: Parking spaces/type
    'epc_rating',           # NEW: Energy Performance Certificate
    'council_tax_band',     # Existing
    'tenure',               # Existing (freehold/leasehold)
    'property_type',        # Existing
    'lease_remaining',      # NEW: Years remaining on lease (if leasehold)
    'service_charge',       # NEW: Annual service charge
    'ground_rent',          # NEW: Annual ground rent
    'first_listed_date',    # Existing
    'first_listed_price',   # Existing
    'last_sold_date',       # Existing
    'last_sold_price',      # Existing
    'latitude',             # From embedded map
    'longitude',            # From embedded map
]

# Combined feature list
ALL_FEATURES = SEARCH_PAGE_FEATURES + [f for f in LISTING_PAGE_FEATURES if f not in SEARCH_PAGE_FEATURES]


# ============================================================================
# GEOCODING CONFIGURATION (FREE NOMINATIM)
# ============================================================================

NOMINATIM_CONFIG = {
    'base_url': 'https://nominatim.openstreetmap.org',
    'email': 'your_email@example.com',  # Required by Nominatim usage policy
    'user_agent': 'LondonPropertyPricePrediction/2.0',
    'rate_limit': 1.0,  # Max 1 request per second (Nominatim policy)
    'timeout': 10,  # Request timeout in seconds
}


# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = f"{DATA_DIR}/scraper.log"


# ============================================================================
# DEBUGGING / TESTING
# ============================================================================

# Set to True to scrape only a few pages for testing
DEBUG_MODE = False
DEBUG_MAX_PAGES = 5

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  London Property Scraper - Zones 1-2 Configuration          ║
╚══════════════════════════════════════════════════════════════╝

Target Areas: {len(ZONES_1_2_BOROUGHS)} boroughs, {len(ZONES_1_2_POSTCODES)} postcodes
Date Range: {DATE_RANGE_STR}
VPN Required: NO (using rate limiting instead)
Geocoding: FREE (Nominatim/OpenStreetMap)
Features: {len(ALL_FEATURES)} total fields

Ready to scrape! 🚀
""")

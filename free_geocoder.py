"""
FREE Geocoding using Nominatim (OpenStreetMap)
Replaces expensive Google Maps API

Features:
- 100% FREE
- No API key required
- Works for UK addresses
- Rate limited to 1 req/sec (Nominatim policy)
- ~85% accuracy (vs Google's 100%)
"""

import requests
import time
import pandas as pd
import logging
from typing import Dict, Optional, List
from pathlib import Path

from config_zones12 import NOMINATIM_CONFIG, CSV_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FreeGeocoder:
    """
    Free geocoding using OpenStreetMap Nominatim
    NO API KEY REQUIRED!
    """

    def __init__(self, email: str = None):
        """
        Args:
            email: Your email (required by Nominatim usage policy)
        """
        self.base_url = NOMINATIM_CONFIG['base_url']
        self.user_agent = NOMINATIM_CONFIG['user_agent']
        self.email = email or NOMINATIM_CONFIG['email']
        self.rate_limit = NOMINATIM_CONFIG['rate_limit']  # 1 request per second
        self.last_request_time = 0
        self.request_count = 0
        self.success_count = 0
        self.failed_addresses = []

    def _rate_limit_delay(self):
        """Ensure we don't exceed 1 request per second"""
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def geocode(self, address: str) -> Optional[Dict[str, any]]:
        """
        Geocode a single address

        Args:
            address: Full address string (e.g., "10 Downing Street, London SW1A 2AA, UK")

        Returns:
            Dict with lat, lon, and other details, or None if failed
        """
        self._rate_limit_delay()
        self.request_count += 1

        try:
            # Build request URL
            url = f"{self.base_url}/search"

            params = {
                'q': address,
                'format': 'json',
                'addressdetails': 1,  # Get detailed address components
                'limit': 1,  # We only want the best match
                'countrycodes': 'gb',  # UK only
            }

            headers = {
                'User-Agent': f"{self.user_agent} ({self.email})"
            }

            response = requests.get(url, params=params, headers=headers,
                                  timeout=NOMINATIM_CONFIG['timeout'])

            if response.status_code == 200:
                results = response.json()

                if results and len(results) > 0:
                    result = results[0]
                    self.success_count += 1

                    return {
                        'latitude': float(result['lat']),
                        'longitude': float(result['lon']),
                        'display_name': result['display_name'],
                        'address_components': result.get('address', {}),
                        'importance': result.get('importance'),  # Confidence score
                        'place_id': result.get('place_id'),
                    }
                else:
                    logger.warning(f"No results for: {address}")
                    self.failed_addresses.append(address)
                    return None

            else:
                logger.error(f"HTTP {response.status_code} for {address}")
                return None

        except Exception as e:
            logger.error(f"Error geocoding '{address}': {e}")
            self.failed_addresses.append(address)
            return None

    def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, any]]:
        """
        Reverse geocode: Get address from coordinates

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dict with address information
        """
        self._rate_limit_delay()
        self.request_count += 1

        try:
            url = f"{self.base_url}/reverse"

            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
            }

            headers = {
                'User-Agent': f"{self.user_agent} ({self.email})"
            }

            response = requests.get(url, params=params, headers=headers,
                                  timeout=NOMINATIM_CONFIG['timeout'])

            if response.status_code == 200:
                result = response.json()
                self.success_count += 1
                return result
            else:
                logger.error(f"HTTP {response.status_code} for ({lat}, {lon})")
                return None

        except Exception as e:
            logger.error(f"Error reverse geocoding ({lat}, {lon}): {e}")
            return None

    def geocode_dataframe(self, df: pd.DataFrame, address_column: str = 'address',
                         save_progress_every: int = 100) -> pd.DataFrame:
        """
        Geocode all addresses in a DataFrame

        Args:
            df: DataFrame with addresses
            address_column: Name of column containing addresses
            save_progress_every: Save progress every N addresses

        Returns:
            DataFrame with added columns: latitude, longitude, geocode_success
        """
        logger.info(f"Geocoding {len(df)} addresses...")
        logger.info(f"Estimated time: ~{len(df)} seconds ({len(df)/60:.1f} minutes)")

        # Initialize new columns
        df['latitude'] = None
        df['longitude'] = None
        df['geocode_success'] = False
        df['geocode_confidence'] = None

        total = len(df)
        start_time = time.time()

        for idx, row in df.iterrows():
            address = row[address_column]

            if pd.isna(address) or address == '':
                continue

            # Geocode
            result = self.geocode(address)

            if result:
                df.at[idx, 'latitude'] = result['latitude']
                df.at[idx, 'longitude'] = result['longitude']
                df.at[idx, 'geocode_success'] = True
                df.at[idx, 'geocode_confidence'] = result.get('importance')

            # Progress logging
            if (idx + 1) % 10 == 0:
                elapsed = time.time() - start_time
                rate = (idx + 1) / elapsed
                remaining = (total - idx - 1) / rate if rate > 0 else 0
                logger.info(
                    f"Progress: {idx + 1}/{total} "
                    f"({(idx + 1)/total*100:.1f}%) | "
                    f"Success rate: {self.success_count}/{self.request_count} "
                    f"({self.success_count/self.request_count*100:.1f}%) | "
                    f"ETA: {remaining/60:.1f} min"
                )

            # Save progress periodically
            if (idx + 1) % save_progress_every == 0:
                self._save_progress(df, "geocoding_progress.csv")

        # Final stats
        success_rate = self.success_count / self.request_count * 100 if self.request_count > 0 else 0
        logger.info(f"\n{'='*60}")
        logger.info(f"Geocoding Complete!")
        logger.info(f"Total addresses: {total}")
        logger.info(f"Successfully geocoded: {self.success_count}")
        logger.info(f"Failed: {len(self.failed_addresses)}")
        logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info(f"Total time: {(time.time() - start_time)/60:.1f} minutes")
        logger.info(f"{'='*60}\n")

        # Save failed addresses for review
        if self.failed_addresses:
            failed_df = pd.DataFrame({'failed_address': self.failed_addresses})
            failed_path = Path(CSV_DIR) / 'failed_geocoding.csv'
            failed_df.to_csv(failed_path, index=False)
            logger.info(f"Failed addresses saved to: {failed_path}")

        return df

    def _save_progress(self, df: pd.DataFrame, filename: str):
        """Save progress during long geocoding runs"""
        filepath = Path(CSV_DIR) / filename
        df.to_csv(filepath, index=False, sep='\t')
        logger.info(f"Progress saved to {filepath}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def geocode_csv_file(input_file: str, output_file: str = None,
                    address_column: str = 'address',
                    email: str = None):
    """
    Geocode all addresses in a CSV file

    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV (default: input_file with _geocoded suffix)
        address_column: Name of address column
        email: Your email (required by Nominatim)

    Example:
        geocode_csv_file(
            'data/csv_data/W1_current_20250109.csv',
            email='your_email@example.com'
        )
    """
    # Load data
    df = pd.read_csv(input_file, sep='\t')
    logger.info(f"Loaded {len(df)} rows from {input_file}")

    # Geocode
    geocoder = FreeGeocoder(email=email)
    df_geocoded = geocoder.geocode_dataframe(df, address_column=address_column)

    # Save
    if output_file is None:
        output_file = input_file.replace('.csv', '_geocoded.csv')

    df_geocoded.to_csv(output_file, sep='\t', index=False)
    logger.info(f"Saved geocoded data to {output_file}")

    return df_geocoded


def calculate_distance_to_center(df: pd.DataFrame,
                                 center_lat: float = 51.5074,  # London center
                                 center_lon: float = -0.1278) -> pd.DataFrame:
    """
    Calculate distance from each property to city center using Haversine formula

    Args:
        df: DataFrame with latitude and longitude columns
        center_lat: Latitude of city center
        center_lon: Longitude of city center

    Returns:
        DataFrame with added 'distance_to_center_km' column
    """
    from math import radians, sin, cos, sqrt, atan2

    def haversine(lat1, lon1, lat2, lon2):
        """Calculate distance between two points on Earth (km)"""
        R = 6371  # Earth radius in km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c

        return distance

    # Calculate distances
    distances = []
    for idx, row in df.iterrows():
        if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
            dist = haversine(row['latitude'], row['longitude'], center_lat, center_lon)
            distances.append(round(dist, 2))
        else:
            distances.append(None)

    df['distance_to_center_km'] = distances

    logger.info(f"Calculated distances to center (lat={center_lat}, lon={center_lon})")
    return df


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("FREE Geocoding with Nominatim (OpenStreetMap)")
    print("="*60)

    # Example 1: Single address
    geocoder = FreeGeocoder(email="your_email@example.com")

    test_address = "10 Downing Street, Westminster, London SW1A 2AA, UK"
    result = geocoder.geocode(test_address)

    if result:
        print(f"\n✅ Successfully geocoded:")
        print(f"   Address: {test_address}")
        print(f"   Latitude: {result['latitude']}")
        print(f"   Longitude: {result['longitude']}")
        print(f"   Display: {result['display_name']}")
    else:
        print(f"\n❌ Failed to geocode: {test_address}")

    print("\n" + "="*60)

    # Example 2: Geocode a CSV file
    # Uncomment to test:
    # geocode_csv_file(
    #     'data/csv_data/W1_current_20250109.csv',
    #     email='your_email@example.com'
    # )

    print("\n🎉 Geocoding module ready!")
    print(f"📧 Remember to set your email in config_zones12.py")
    print(f"⏱️  Rate limit: {NOMINATIM_CONFIG['rate_limit']} requests/second")
    print(f"💰 Cost: £0.00 (completely FREE!)")

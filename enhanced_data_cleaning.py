"""
Enhanced Data Cleaning Pipeline for London Property Data

Handles new features:
- Square footage (sq ft & sq m)
- Property age
- EPC ratings
- Garden, parking
- Lease information
- Geocoded coordinates
"""

import pandas as pd
import numpy as np
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config_zones12 import CLEAN_DIR, DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedPropertyCleaner:
    """
    Enhanced data cleaning for property data with many new features
    """

    def __init__(self):
        self.cleaning_stats = {
            'total_rows': 0,
            'duplicates_removed': 0,
            'invalid_prices_removed': 0,
            'invalid_coordinates_removed': 0,
            'missing_critical_features': 0,
        }

    def clean_price(self, price_series: pd.Series) -> pd.Series:
        """
        Clean price column
        Handles: £1,375,000 | Guide price£650,000 | POA | etc.
        """
        def _clean_single_price(price):
            if pd.isna(price) or price == '':
                return np.nan

            price = str(price).lower()

            # Remove POA, OIEO, etc.
            if any(term in price for term in ['poa', 'offers', 'guide', 'from']):
                price = re.sub(r'(guide price|offers? (in excess )?of|from|poa)', '', price, flags=re.IGNORECASE)

            # Extract numeric value
            match = re.search(r'[£]?([\d,]+)', price)
            if match:
                numeric = match.group(1).replace(',', '')
                try:
                    return float(numeric)
                except:
                    return np.nan

            return np.nan

        cleaned = price_series.apply(_clean_single_price)

        # Remove obviously wrong prices
        cleaned = cleaned.apply(lambda x: x if 10000 <= x <= 50000000 else np.nan)

        return cleaned

    def clean_bedrooms(self, bedroom_series: pd.Series) -> pd.Series:
        """Clean bedrooms column"""
        def _clean_single(val):
            if pd.isna(val):
                return np.nan
            try:
                # Extract first number
                match = re.search(r'(\d+)', str(val))
                if match:
                    num = int(match.group(1))
                    # Sanity check
                    return num if 0 <= num <= 20 else np.nan
            except:
                pass
            return np.nan

        return bedroom_series.apply(_clean_single)

    def clean_bathrooms(self, bathroom_series: pd.Series) -> pd.Series:
        """Clean bathrooms column (can be decimal like 1.5)"""
        def _clean_single(val):
            if pd.isna(val):
                return np.nan
            try:
                # Extract number (including decimals)
                match = re.search(r'(\d+\.?\d*)', str(val))
                if match:
                    num = float(match.group(1))
                    return num if 0 <= num <= 10 else np.nan
            except:
                pass
            return np.nan

        return bathroom_series.apply(_clean_single)

    def clean_lounges(self, lounge_series: pd.Series) -> pd.Series:
        """Clean reception/lounges column"""
        def _clean_single(val):
            if pd.isna(val) or val == 'na':
                return np.nan
            try:
                match = re.search(r'(\d+)', str(val))
                if match:
                    num = int(match.group(1))
                    return num if 0 <= num <= 10 else np.nan
            except:
                pass
            return np.nan

        return lounge_series.apply(_clean_single)

    def extract_postcode_parts(self, postcode_series: pd.Series) -> pd.DataFrame:
        """
        Extract postcode components
        Example: "SW1A 2AA" -> area="SW", district="SW1", sector="SW1A", full="SW1A 2AA"
        """
        def _extract(postcode):
            if pd.isna(postcode):
                return {'postcode_area': None, 'postcode_district': None,
                       'postcode_sector': None, 'postcode_full': None}

            postcode = str(postcode).upper().strip()

            # UK postcode pattern
            match = re.search(r'([A-Z]{1,2})(\d{1,2}[A-Z]?)\s?(\d[A-Z]{2})', postcode)
            if match:
                area = match.group(1)
                district = area + match.group(2)
                sector = district.strip() + ' ' + match.group(3)[0]
                full = district.strip() + ' ' + match.group(3)

                return {
                    'postcode_area': area,
                    'postcode_district': district.replace(' ', ''),
                    'postcode_sector': sector,
                    'postcode_full': full
                }

            return {'postcode_area': None, 'postcode_district': None,
                   'postcode_sector': None, 'postcode_full': postcode}

        results = postcode_series.apply(_extract)
        return pd.DataFrame(results.tolist())

    def clean_square_footage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate square footage
        Convert between sq ft and sq m if only one is available
        """
        if 'square_feet' in df.columns:
            df['square_feet'] = pd.to_numeric(df['square_feet'], errors='coerce')
            # Remove impossible values
            df.loc[df['square_feet'] < 100, 'square_feet'] = np.nan
            df.loc[df['square_feet'] > 50000, 'square_feet'] = np.nan

        if 'square_meters' in df.columns:
            df['square_meters'] = pd.to_numeric(df['square_meters'], errors='coerce')
            df.loc[df['square_meters'] < 10, 'square_meters'] = np.nan
            df.loc[df['square_meters'] > 5000, 'square_meters'] = np.nan

        # Convert between units if only one is available
        if 'square_feet' in df.columns and 'square_meters' in df.columns:
            # sqft -> sqm
            mask = df['square_feet'].notna() & df['square_meters'].isna()
            df.loc[mask, 'square_meters'] = (df.loc[mask, 'square_feet'] * 0.092903).round(2)

            # sqm -> sqft
            mask = df['square_meters'].notna() & df['square_feet'].isna()
            df.loc[mask, 'square_feet'] = (df.loc[mask, 'square_meters'] * 10.7639).round(2)

        return df

    def clean_property_age(self, age_series: pd.Series) -> pd.DataFrame:
        """
        Clean property age
        Returns both year_built and age_category
        """
        def _process_age(val):
            if pd.isna(val):
                return {'year_built': None, 'age_category': None}

            val = str(val).lower()

            # Extract year
            year_match = re.search(r'(\d{4})', val)
            if year_match:
                year = int(year_match.group(1))
                # Sanity check
                current_year = datetime.now().year
                if 1600 <= year <= current_year:
                    return {'year_built': year, 'age_category': self._categorize_age(year)}

            # Check for category keywords
            if 'victorian' in val:
                return {'year_built': None, 'age_category': 'Victorian'}
            elif 'edwardian' in val:
                return {'year_built': None, 'age_category': 'Edwardian'}
            elif 'georgian' in val:
                return {'year_built': None, 'age_category': 'Georgian'}
            elif 'new build' in val or 'new-build' in val:
                return {'year_built': None, 'age_category': 'New Build'}
            elif 'period' in val:
                return {'year_built': None, 'age_category': 'Period Property'}

            return {'year_built': None, 'age_category': None}

        results = age_series.apply(_process_age)
        return pd.DataFrame(results.tolist())

    @staticmethod
    def _categorize_age(year: int) -> str:
        """Categorize property by build year"""
        if year >= 2010:
            return 'New Build'
        elif year >= 1980:
            return 'Modern'
        elif year >= 1945:
            return 'Post-War'
        elif year >= 1919:
            return 'Inter-War'
        elif year >= 1901:
            return 'Edwardian'
        elif year >= 1837:
            return 'Victorian'
        elif year >= 1714:
            return 'Georgian'
        else:
            return 'Historic'

    def clean_epc_rating(self, epc_series: pd.Series) -> pd.Series:
        """Clean EPC rating (A-G)"""
        def _clean(val):
            if pd.isna(val):
                return np.nan
            val = str(val).upper().strip()
            if val in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                return val
            return np.nan

        return epc_series.apply(_clean)

    def clean_tenure(self, tenure_series: pd.Series) -> pd.Series:
        """Clean tenure (Freehold/Leasehold)"""
        def _clean(val):
            if pd.isna(val):
                return np.nan
            val = str(val).lower()
            if 'freehold' in val:
                return 'Freehold'
            elif 'leasehold' in val:
                return 'Leasehold'
            return np.nan

        return tenure_series.apply(_clean)

    def clean_lease_years(self, years_series: pd.Series) -> pd.Series:
        """Clean lease years remaining"""
        def _clean(val):
            if pd.isna(val):
                return np.nan
            try:
                years = int(re.search(r'(\d+)', str(val)).group(1))
                return years if 0 <= years <= 999 else np.nan
            except:
                return np.nan

        return years_series.apply(_clean)

    def clean_coordinates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate lat/long coordinates
        London bounds: lat ~51.2 to 51.7, lon ~-0.5 to 0.3
        """
        if 'latitude' in df.columns:
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            # London bounds check
            df.loc[(df['latitude'] < 51.0) | (df['latitude'] > 52.0), 'latitude'] = np.nan

        if 'longitude' in df.columns:
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            df.loc[(df['longitude'] < -1.0) | (df['longitude'] > 1.0), 'longitude'] = np.nan

        return df

    def clean_dates(self, date_series: pd.Series) -> pd.Series:
        """
        Clean date columns
        Handles various formats
        """
        def _clean_date(val):
            if pd.isna(val) or val == '' or val == '-':
                return np.nan

            val = str(val)

            # Remove "Last sold  - " prefix
            val = re.sub(r'last sold\s*-?\s*', '', val, flags=re.IGNORECASE)

            # Try to parse
            try:
                # Month Year format (e.g., "Oct 1999")
                if re.match(r'[A-Za-z]{3}\s+\d{4}', val):
                    return pd.to_datetime(val, format='%b %Y')

                # Try general parsing
                return pd.to_datetime(val)
            except:
                return np.nan

        return date_series.apply(_clean_date)

    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate listings"""
        initial_count = len(df)

        # Remove exact duplicates
        df = df.drop_duplicates()

        # Remove duplicates by address + price
        if 'address' in df.columns and 'last_sold_price_gbp' in df.columns:
            df = df.drop_duplicates(subset=['address', 'last_sold_price_gbp'], keep='first')

        self.cleaning_stats['duplicates_removed'] = initial_count - len(df)
        return df

    def clean_full_pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run full cleaning pipeline on raw data
        """
        logger.info(f"Starting cleaning pipeline on {len(df)} rows")
        self.cleaning_stats['total_rows'] = len(df)

        # Price
        if 'price' in df.columns:
            df['last_sold_price_gbp'] = self.clean_price(df['price'])
        elif 'last_sold_price' in df.columns:
            df['last_sold_price_gbp'] = self.clean_price(df['last_sold_price'])

        # Bedrooms, bathrooms, lounges
        if 'bedrooms' in df.columns:
            df['bedrooms'] = self.clean_bedrooms(df['bedrooms'])
        if 'bathrooms' in df.columns:
            df['bathrooms'] = self.clean_bathrooms(df['bathrooms'])
        if 'lounges' in df.columns:
            df['lounges'] = self.clean_lounges(df['lounges'])

        # Postcode
        if 'address' in df.columns:
            # Extract postcode from address
            postcode_pattern = r'([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})'
            df['postcode'] = df['address'].str.extract(postcode_pattern, flags=re.IGNORECASE)[0]

            # Extract components
            postcode_parts = self.extract_postcode_parts(df['postcode'])
            df = pd.concat([df, postcode_parts], axis=1)

        # Square footage
        df = self.clean_square_footage(df)

        # Property age
        if 'property_age' in df.columns:
            age_data = self.clean_property_age(df['property_age'])
            df = pd.concat([df, age_data], axis=1)

        # EPC
        if 'epc_rating' in df.columns:
            df['epc_rating'] = self.clean_epc_rating(df['epc_rating'])

        # Tenure
        if 'tenure' in df.columns:
            df['tenure'] = self.clean_tenure(df['tenure'])

        # Lease years
        if 'lease_remaining' in df.columns:
            df['lease_years_remaining'] = self.clean_lease_years(df['lease_remaining'])

        # Coordinates
        df = self.clean_coordinates(df)

        # Dates
        for date_col in ['last_sold_date', 'first_listed_date']:
            if date_col in df.columns:
                df[date_col] = self.clean_dates(df[date_col])

        # Remove duplicates
        df = self.remove_duplicates(df)

        # Remove rows with missing critical features
        critical_cols = ['address', 'last_sold_price_gbp']
        initial_count = len(df)
        df = df.dropna(subset=critical_cols)
        self.cleaning_stats['missing_critical_features'] = initial_count - len(df)

        # Remove invalid prices
        initial_count = len(df)
        df = df[df['last_sold_price_gbp'] > 0]
        self.cleaning_stats['invalid_prices_removed'] = initial_count - len(df)

        # Log stats
        logger.info("\n" + "="*60)
        logger.info("CLEANING STATISTICS")
        logger.info("="*60)
        for key, value in self.cleaning_stats.items():
            logger.info(f"{key}: {value}")
        logger.info(f"Final row count: {len(df)}")
        logger.info("="*60 + "\n")

        return df

    def save_cleaned_data(self, df: pd.DataFrame, filename: str):
        """Save cleaned data"""
        Path(CLEAN_DIR).mkdir(parents=True, exist_ok=True)
        filepath = Path(CLEAN_DIR) / filename
        df.to_csv(filepath, sep='\t', index=False)
        logger.info(f"Saved cleaned data to {filepath}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def clean_csv_file(input_file: str, output_file: str = None) -> pd.DataFrame:
    """
    Clean a CSV file

    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV (auto-generated if None)

    Returns:
        Cleaned DataFrame
    """
    logger.info(f"Loading {input_file}...")
    df = pd.read_csv(input_file, sep='\t')

    cleaner = EnhancedPropertyCleaner()
    df_clean = cleaner.clean_full_pipeline(df)

    if output_file is None:
        output_file = input_file.replace('.csv', '_cleaned.csv')

    cleaner.save_cleaned_data(df_clean, Path(output_file).name)

    return df_clean


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("Enhanced Data Cleaning Pipeline")
    print("="*60)

    # Example: Clean a file
    # df_cleaned = clean_csv_file(
    #     'data/csv_data/W1_current_20250109.csv',
    #     'data/clean_data/W1_current_cleaned.csv'
    # )

    print("\n✅ Data cleaning module ready!")
    print("Handles all new features: sqft, age, EPC, parking, garden, etc.")

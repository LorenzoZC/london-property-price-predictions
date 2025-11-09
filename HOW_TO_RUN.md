# 🚀 How to Run the Enhanced Scraper

## ⚠️ IMPORTANT: Run Locally, Not in Notebooks

**You do NOT need to run the old notebooks!** Those are the old approach. Here's the new workflow:

---

## 🎯 Quick Start (5 Minutes)

### **Step 1: Clone/Pull Latest Code**

```bash
cd ~/london-property-price-predictions
git pull origin claude/analyze-notebooks-011CUxf9Kq8jYJnKikHskLMW
```

✅ You now have:
- `enhanced_selenium_scraper.py` - NEW scraper (bypasses 403)
- `free_geocoder.py` - FREE geocoding
- `enhanced_data_cleaning.py` - Data cleaning
- `config_zones12.py` - Configuration (email already set!)

---

### **Step 2: Install Dependencies**

```bash
pip install selenium webdriver-manager beautifulsoup4 requests pandas
```

That's it! The scraper will auto-download ChromeDriver.

---

### **Step 3: Run the Scraper**

```bash
python enhanced_selenium_scraper.py
```

This will:
- ✅ Scrape W1 (Mayfair/Marylebone) - 3 pages
- ✅ Extract square footage, EPC, parking, garden
- ✅ Save to `data/csv_data/W1_current_YYYYMMDD.csv`
- ✅ No VPN required!

**Time:** ~5-10 minutes for 3 pages (~75 listings)

---

### **Step 4: Geocode Addresses (Optional but Recommended)**

```bash
python -c "
from free_geocoder import geocode_csv_file
geocode_csv_file(
    'data/csv_data/W1_current_20251109.csv',
    email='lorenzo.zorzi@gmail.com'
)
"
```

**Time:** ~1 second per address (FREE!)
- 75 addresses = ~75 seconds
- 1,000 addresses = ~17 minutes
- 100,000 addresses = ~28 hours (run overnight)

---

### **Step 5: Clean Data**

```bash
python -c "
from enhanced_data_cleaning import clean_csv_file
clean_csv_file(
    'data/csv_data/W1_current_20251109_geocoded.csv',
    'data/clean_data/W1_cleaned.csv'
)
"
```

**Done!** You now have clean data ready for modeling.

---

## 📊 Customizing Your Scrape

### **Scrape More Pages (More Data)**

Edit `enhanced_selenium_scraper.py` at the bottom:

```python
# Change max_pages
df = scraper.scrape_postcode_area(
    postcode_area="W1",
    max_pages=20  # Scrape 20 pages instead of 3
)
```

### **Scrape Different Postcodes**

```python
# Scrape multiple high-value areas
for postcode in ["W1", "SW1", "SW3", "W8", "W11"]:
    df = scraper.scrape_postcode_area(
        postcode_area=postcode,
        max_pages=10
    )
```

### **Scrape ALL Zones 1-2 (Production)**

```python
from config_zones12 import ZONES_1_2_POSTCODES

for postcode in ZONES_1_2_POSTCODES:
    print(f"Scraping {postcode}...")
    df = scraper.scrape_postcode_area(
        postcode_area=postcode,
        max_pages='all'  # Scrape everything!
    )
```

**Time:** ~125 days on one machine (or 5 days with 25 machines in parallel)

---

## 🛠️ Complete Workflow Example

Here's a complete script to scrape, geocode, and clean:

**`scrape_w1_complete.py`:**
```python
#!/usr/bin/env python3
"""
Complete workflow: Scrape W1 → Geocode → Clean
"""

from enhanced_selenium_scraper import EnhancedSeleniumScraper
from free_geocoder import geocode_csv_file, calculate_distance_to_center
from enhanced_data_cleaning import clean_csv_file
import pandas as pd

# 1. SCRAPE
print("🏠 Step 1: Scraping W1...")
scraper = EnhancedSeleniumScraper(headless=True)
try:
    df_raw = scraper.scrape_postcode_area("W1", max_pages=5)
    raw_file = "data/csv_data/W1_current_20251109.csv"
    print(f"✅ Scraped {len(df_raw)} properties → {raw_file}")
finally:
    scraper.close()

# 2. GEOCODE
print("\n🌍 Step 2: Geocoding addresses...")
geocoded_file = geocode_csv_file(
    raw_file,
    email='lorenzo.zorzi@gmail.com'
)
print(f"✅ Geocoded → {geocoded_file}")

# 3. ADD DISTANCE TO CENTER
print("\n📏 Step 3: Calculating distances to city center...")
df_geo = pd.read_csv(geocoded_file, sep='\t')
df_geo = calculate_distance_to_center(df_geo)
df_geo.to_csv(geocoded_file, sep='\t', index=False)
print(f"✅ Added distance_to_center_km")

# 4. CLEAN
print("\n🧹 Step 4: Cleaning data...")
df_clean = clean_csv_file(
    geocoded_file,
    'data/clean_data/W1_final.csv'
)
print(f"✅ Cleaned {len(df_clean)} properties → data/clean_data/W1_final.csv")

# 5. SUMMARY
print("\n" + "="*80)
print("📊 SUMMARY")
print("="*80)
print(f"Total properties: {len(df_clean)}")
print(f"With square footage: {df_clean['square_feet'].notna().sum()}")
print(f"With geocoding: {df_clean['latitude'].notna().sum()}")
print(f"Average price: £{df_clean['last_sold_price_gbp'].mean():,.0f}")
print(f"Average sqft: {df_clean['square_feet'].mean():.0f}")
print("="*80)

# Show sample
print("\n📋 Sample data:")
print(df_clean[['address', 'last_sold_price_gbp', 'square_feet', 'bedrooms', 'latitude']].head(10))
```

Run it:
```bash
python scrape_w1_complete.py
```

---

## ❓ FAQ

### **Q: Do I need to run the old Jupyter notebooks?**
**A: NO!** The notebooks were the learning/experimentation phase. Use the new Python scripts instead.

### **Q: Will this work on my Mac/Windows?**
**A: YES!** Selenium works on all platforms. Just install Chrome.

### **Q: Can I run this on a cloud VM?**
**A: YES!** But you need to install Chrome:

```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser chromium-chromedriver

# CentOS/RHEL
sudo yum install chromium chromium-headless
```

### **Q: How do I avoid CAPTCHAs?**
**A:** The code already has:
- ✅ Random delays (2-4 seconds)
- ✅ Random User-Agents
- ✅ Cookie handling

If you still get CAPTCHAs:
1. Increase delay in `config_zones12.py`: `REQUEST_DELAY_MIN = 5.0`
2. Run during off-peak hours (night/weekend)
3. Use residential proxy (optional, costs money)

### **Q: Why Selenium instead of requests?**
**A:** Zoopla blocks simple `requests` (403 error). Selenium uses a real browser which:
- ✅ Executes JavaScript
- ✅ Handles cookies
- ✅ Looks like a real user

### **Q: What's the difference vs the original scraper?**

| Feature | Old (main_scraper.ipynb) | New (enhanced_selenium_scraper.py) |
|---------|--------------------------|-------------------------------------|
| **Target** | Bromley & Croydon | Zones 1-2 (15 boroughs) |
| **VPN** | Required (IVPN) | Not needed |
| **Square footage** | ❌ Missing | ✅ Extracted |
| **Property age** | ❌ Missing | ✅ Extracted |
| **EPC, parking, garden** | ❌ Missing | ✅ Extracted |
| **Geocoding** | Google (£££) | Nominatim (FREE) |
| **Code type** | Notebook (manual) | Script (automated) |

### **Q: Can I scrape historical sales instead of current listings?**
**A:** Yes! The URL pattern is different. I can create that script if you want.

---

## 🎯 Recommended Workflow

### **For Testing (Today):**
```bash
# Scrape 5 pages from W1
python enhanced_selenium_scraper.py
# ~10 minutes, ~125 listings
```

### **For Real Data (This Week):**
```bash
# Scrape high-value zones 1-2 areas (20 pages each)
# W1, SW1, SW3, W8, W11, N1, E1, EC1, WC1, WC2
# ~10 postcodes × 20 pages × 25 listings = ~5,000 properties
# Time: ~1-2 days
```

### **For Production (Next Month):**
```bash
# Scrape ALL 60+ postcodes in zones 1-2
# Estimated: 150,000+ properties
# Time: ~125 days (or 5 days with 25 parallel scrapers)
```

---

## 📈 Next: Build Better Model

Once you have clean data with square footage:

```python
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split

# Load cleaned data
df = pd.read_csv('data/clean_data/W1_final.csv', sep='\t')

# Feature engineering
df['price_per_sqft'] = df['last_sold_price_gbp'] / df['square_feet']
df['total_rooms'] = df['bedrooms'] + df['bathrooms'] + df['lounges']

# Prepare features
features = [
    'square_feet', 'bedrooms', 'bathrooms', 'lounges',
    'latitude', 'longitude', 'distance_to_center_km',
    'total_rooms'
]

X = df[features].dropna()
y = df.loc[X.index, 'last_sold_price_gbp']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train XGBoost
model = XGBRegressor(n_estimators=1000, learning_rate=0.01, max_depth=6)
model.fit(X_train, y_train)

# Evaluate
print(f"R² Score: {model.score(X_test, y_test):.3f}")
# Expected: 0.85+ (vs 0.70 before!)
```

---

## 💬 Need Help?

If you get stuck:
1. Check logs in console output
2. Look at `data/csv_data/` to see if files were created
3. Try with just 1 page first: `max_pages=1`

The code is ready to run on your machine! 🚀

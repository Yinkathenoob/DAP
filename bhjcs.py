import urllib.request
import ssl
from bs4 import BeautifulSoup
import os
import re

ssl._create_default_https_context = ssl._create_unverified_context
wayback_prefix = "https://web.archive.org"

# Read main page
with open('cached_pages/main.html', 'r', encoding='utf-8', errors='ignore') as f:
    main_soup = BeautifulSoup(f.read(), 'html.parser')

# Get all region links
regions = []
articles = main_soup.find_all('article', {'data-href': re.compile(r'/regions/')})
for article in articles:
    href = article.get('data-href')
    if href:
        regions.append(href)

print(f"Found {len(regions)} regions:")
for r in regions:
    print(f"  - {r.split('/')[-2]}")

# Now check each region's cached file
print("\n" + "="*60)
print("CLINICS PER REGION:")
print("="*60)

total_clinics = []
region_files = [f for f in os.listdir('cached_pages') if f.startswith('region_')]

for region_file in region_files:
    with open(f'cached_pages/{region_file}', 'r', encoding='utf-8', errors='ignore') as f:
        region_soup = BeautifulSoup(f.read(), 'html.parser')
    
    region_name = region_file.replace('region_', '').replace('.html', '').replace('_', ' ')
    
    # Find clinic links
    clinic_links = []
    
    # Method 1: data-href attributes
    articles = region_soup.find_all('article', {'data-href': True})
    for article in articles:
        href = article.get('data-href')
        if href and '/regions/' not in href and '/our-clinics/' in href:
            clinic_links.append(href)
    
    # Method 2: regular links
    for link in region_soup.find_all('a', href=True):
        href = link['href']
        if '/our-clinics/' in href and '/regions/' not in href and '#' not in href:
            if href not in clinic_links:
                clinic_links.append(href)
    
    clinic_links = list(set(clinic_links))
    clinic_links = [l for l in clinic_links if not l.endswith('/our-clinics/')]
    
    print(f"\n{region_name}: {len(clinic_links)} clinics")
    for c in clinic_links:
        clinic_name = c.split('/')[-2] if c.endswith('/') else c.split('/')[-1]
        print(f"    - {clinic_name}")
        total_clinics.append(c)

# Remove duplicates
total_clinics = list(set(total_clinics))
print(f"\n{'='*60}")
print(f"TOTAL UNIQUE CLINICS: {len(total_clinics)}")
print(f"{'='*60}")

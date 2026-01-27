import urllib.request
import ssl
import pandas as pd
from bs4 import BeautifulSoup
import re
import os
import time
import random

ssl._create_default_https_context = ssl._create_unverified_context
os.makedirs('cached_pages', exist_ok=True)

def download_page(url, filename, retries=3):
    """Download page with retry logic"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if len(content) > 500:
                return content
    
    for attempt in range(retries):
        try:
            delay = random.uniform(3, 6)
            time.sleep(delay)
            
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            with open(filename, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(html)
            
            return html
            
        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                wait_time = 20 * (attempt + 1)
                print(f"    Waiting {wait_time}s...")
                time.sleep(wait_time)
    
    return None

def extract_clinic_data(soup):
    """Extract clinic information based on actual HTML structure"""
    data = {
        'Name of Clinic': '',
        'Address': '',
        'Email': '',
        'Phone': '',
        'Services': ''
    }
    
    # === NAME ===
    h1 = soup.find('h1', class_='entry-title')
    if h1:
        data['Name of Clinic'] = h1.get_text(strip=True)
    else:
        h1 = soup.find('h1')
        if h1:
            data['Name of Clinic'] = h1.get_text(strip=True)
    
    # === ADDRESS ===
    address_div = soup.find('div', class_='address')
    if address_div:
        address_link = address_div.find('a')
        if address_link:
            for br in address_link.find_all('br'):
                br.replace_with(', ')
            # Remove the icon span
            for span in address_link.find_all('span'):
                span.decompose()
            data['Address'] = address_link.get_text(strip=True)
    
    # === EMAIL (FIXED!) ===
    # The href looks like: https://web.archive.org/web/.../mailto:email@domain.com
    email_link = soup.find('a', href=re.compile(r'mailto:', re.I))
    if email_link:
        href = email_link.get('href', '')
        # Extract email from wayback URL
        if 'mailto:' in href:
            email = href.split('mailto:')[-1].split('?')[0]
            data['Email'] = email
    
    # Fallback: get email from link text
    if not data['Email']:
        metabox = soup.find('div', class_='clinic-metabox')
        if metabox:
            # Find email pattern in text
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.com\.au', metabox.get_text())
            if email_match:
                data['Email'] = email_match.group(0)
    
    # === PHONE ===
    tel_links = soup.find_all('a', href=re.compile(r'tel:', re.I))
    for tel in tel_links:
        href = tel.get('href', '')
        # Extract phone from wayback URL if needed
        if 'tel:' in href:
            phone = href.split('tel:')[-1]
            phone = re.sub(r'[^\d]', '', phone)  # Keep only digits
            # Skip 1800/1300 numbers
            if not phone.startswith('1800') and not phone.startswith('1300') and len(phone) >= 8:
                # Format nicely
                if len(phone) == 10:
                    data['Phone'] = f"({phone[:2]}) {phone[2:6]} {phone[6:]}"
                elif len(phone) == 8:
                    data['Phone'] = f"{phone[:4]} {phone[4:]}"
                else:
                    data['Phone'] = phone
                break
    
    # Fallback: find phone in metabox text
    if not data['Phone']:
        metabox = soup.find('div', class_='clinic-metabox')
        if metabox:
            text = metabox.get_text()
            phone_match = re.search(r'0[23478]\s*\d{4}\s*\d{4}', text)
            if phone_match:
                data['Phone'] = phone_match.group(0)
    
    # === SERVICES ===
    services = []
    services_section = soup.find('div', class_='featured-posts')
    if services_section:
        heading = services_section.find('h2')
        if heading and 'Services' in heading.get_text():
            articles = services_section.find_all('article', class_=re.compile(r'hentry'))
            for article in articles:
                h3 = article.find('h3')
                if h3:
                    link = h3.find('a')
                    if link:
                        service_name = link.get_text(strip=True)
                        if service_name and service_name not in services:
                            services.append(service_name)
    
    if not services:
        articles = soup.find_all('article', class_=re.compile(r'hentry.*featured-post'))
        for article in articles:
            data_href = article.get('data-href', '')
            if '/regions/' in data_href:
                continue
            if '/our-services/' in data_href:
                h3 = article.find('h3')
                if h3:
                    service_name = h3.get_text(strip=True)
                    if service_name and service_name not in services:
                        services.append(service_name)
    
    data['Services'] = ', '.join(services)
    
    return data

def main():
    wayback_base = "https://web.archive.org/web/20250708180027/https://www.myfootdr.com.au/our-clinics/"
    wayback_prefix = "https://web.archive.org"
    
    print("=" * 60)
    print("MYFOOTDR CLINIC SCRAPER")
    print("=" * 60)
    
    # STEP 1: Get main page
    print("\n[STEP 1] Getting main page...")
    main_html = download_page(wayback_base, 'cached_pages/main.html')
    if not main_html:
        print("Failed to get main page!")
        return
    
    soup = BeautifulSoup(main_html, 'html.parser')
    
    # Find region links from data-href attributes
    region_links = []
    articles = soup.find_all('article', {'data-href': re.compile(r'/regions/')})
    for article in articles:
        href = article.get('data-href')
        if href:
            if href.startswith('/'):
                href = f"{wayback_prefix}/web/20250708180027/https://www.myfootdr.com.au{href}"
            region_links.append(href)
    
    region_links = list(set(region_links))
    print(f"Found {len(region_links)} regions")
    
    # STEP 2: Get clinic links from each region
    print("\n[STEP 2] Getting clinic links from regions...")
    clinic_links = []
    
    for i, region_url in enumerate(region_links):
        region_name = region_url.split('/')[-2]
        print(f"  [{i+1}/{len(region_links)}] {region_name}")
        
        safe_name = re.sub(r'[^\w]', '_', region_name)
        filename = f'cached_pages/region_{safe_name}.html'
        
        html = download_page(region_url, filename)
        if html:
            region_soup = BeautifulSoup(html, 'html.parser')
            
            # Find clinic links (articles with data-href NOT containing /regions/)
            articles = region_soup.find_all('article', {'data-href': True})
            for article in articles:
                href = article.get('data-href')
                if href and '/regions/' not in href and '/our-clinics/' in href:
                    if href.startswith('/'):
                        href = f"{wayback_prefix}/web/20250708180027/https://www.myfootdr.com.au{href}"
                    clinic_links.append(href)
            
            # Also find regular links
            for link in region_soup.find_all('a', href=True):
                href = link['href']
                if '/our-clinics/' in href and '/regions/' not in href and '#' not in href:
                    if href.startswith('/web/'):
                        href = wayback_prefix + href
                    elif href.startswith('/'):
                        href = f"{wayback_prefix}/web/20250708180027/https://www.myfootdr.com.au{href}"
                    if href.startswith('http'):
                        clinic_links.append(href)
    
    clinic_links = list(set(clinic_links))
    # Remove main page if present
    clinic_links = [l for l in clinic_links if not l.endswith('/our-clinics/')]
    
    print(f"\nTotal unique clinic links: {len(clinic_links)}")
    
    # STEP 3: Scrape each clinic
    print("\n[STEP 3] Scraping clinic pages...")
    print("-" * 60)
    
    all_clinics = []
    failed = []
    
    for i, url in enumerate(clinic_links):
        clinic_slug = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
        safe_name = re.sub(r'[^\w]', '_', clinic_slug)[:50]
        filename = f'cached_pages/clinic_{i}_{safe_name}.html'
        
        print(f"\n[{i+1}/{len(clinic_links)}] {clinic_slug}")
        
        html = download_page(url, filename)
        
        if html:
            clinic_soup = BeautifulSoup(html, 'html.parser')
            data = extract_clinic_data(clinic_soup)
            
            if data['Name of Clinic'] and 'Our Clinics' not in data['Name of Clinic']:
                all_clinics.append(data)
                print(f"  ✓ Name: {data['Name of Clinic']}")
                print(f"    Address: {data['Address'][:50]}..." if len(data['Address']) > 50 else f"    Address: {data['Address']}")
                print(f"    Email: {data['Email']}")
                print(f"    Phone: {data['Phone']}")
                print(f"    Services: {len(data['Services'].split(', ')) if data['Services'] else 0} found")
            else:
                print(f"  ✗ Not a clinic page")
        else:
            print(f"  ✗ Download failed")
            failed.append(url)
        
        # Save progress every 10 clinics
        if (i + 1) % 10 == 0 and all_clinics:
            temp_df = pd.DataFrame(all_clinics)
            temp_df.to_csv('myfootdr_clinics_progress.csv', index=False)
            print(f"\n  [Progress saved: {len(all_clinics)} clinics]\n")
    
    # STEP 4: Save final results
    print("\n" + "=" * 60)
    print("[STEP 4] Saving results...")
    print("=" * 60)
    
    if all_clinics:
        df = pd.DataFrame(all_clinics)
        df.drop_duplicates(subset=['Name of Clinic'], inplace=True)
        df.to_csv('myfootdr_clinics.csv', index=False)
        
        print(f"\n✓ SUCCESS! Saved {len(df)} clinics to myfootdr_clinics.csv")
        print(f"\nData Quality:")
        print(f"  - Name: {(df['Name of Clinic'] != '').sum()}/{len(df)}")
        print(f"  - Address: {(df['Address'] != '').sum()}/{len(df)}")
        print(f"  - Email: {(df['Email'] != '').sum()}/{len(df)}")
        print(f"  - Phone: {(df['Phone'] != '').sum()}/{len(df)}")
        print(f"  - Services: {(df['Services'] != '').sum()}/{len(df)}")
        
        if failed:
            print(f"\n⚠ {len(failed)} pages failed - saved to failed_urls.txt")
            with open('failed_urls.txt', 'w') as f:
                f.write('\n'.join(failed))
    else:
        print("\n✗ No clinics found!")

if __name__ == "__main__":
    start = time.time()
    main()
    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed/60:.1f} minutes")
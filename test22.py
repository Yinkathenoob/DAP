import urllib.request
import ssl
import time
import pandas as pd
from bs4 import BeautifulSoup
import re
import os

# Bypass SSL verification
ssl._create_default_https_context = ssl._create_unverified_context

def download_page(url, filename):
    """Download page and save locally"""
    if os.path.exists(filename):
        print(f"Already downloaded: {filename}")
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    try:
        print(f"Downloading: {url}")
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            # Try multiple encodings
            raw_bytes = response.read()
            
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    html = raw_bytes.decode(encoding)
                    break
                except:
                    continue
            else:
                # Fallback: decode with errors ignored
                html = raw_bytes.decode('utf-8', errors='ignore')
        
        # Save locally
        with open(filename, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(html)
        
        time.sleep(15)  # Wait 15 seconds between requests
        return html
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def extract_clinic_data(soup, url):
    """Extract clinic information from page"""
    data = {
        'Name of Clinic': '',
        'Address': '',
        'Email': '',
        'Phone': '',
        'Services': ''
    }
    
    # Get clinic name (usually h1)
    h1 = soup.find('h1')
    if h1:
        data['Name of Clinic'] = h1.get_text(strip=True)
    
    # Get email
    email_link = soup.find('a', href=re.compile(r'^mailto:', re.I))
    if email_link:
        data['Email'] = email_link['href'].replace('mailto:', '').replace('Mailto:', '').split('?')[0]
    
    # Get phone
    phone_link = soup.find('a', href=re.compile(r'^tel:', re.I))
    if phone_link:
        data['Phone'] = phone_link['href'].replace('tel:', '')
    
    # Get address - look for common patterns
    address_elem = (
        soup.find('address') or
        soup.find('div', class_=re.compile(r'address', re.I)) or
        soup.find('p', class_=re.compile(r'address', re.I)) or
        soup.find(string=re.compile(r'\d+\s+\w+\s+(Street|St|Road|Rd|Avenue|Ave)', re.I))
    )
    
    if address_elem:
        if hasattr(address_elem, 'get_text'):
            data['Address'] = address_elem.get_text(strip=True)
        else:
            data['Address'] = str(address_elem).strip()
    
    # Get services
    services_list = []
    service_sections = soup.find_all(['div', 'section', 'ul'], class_=re.compile(r'service', re.I))
    for section in service_sections:
        items = section.find_all('li')
        if items:
            services_list.extend([item.get_text(strip=True) for item in items])
    
    if services_list:
        data['Services'] = ', '.join(list(set(services_list))[:10])
    
    return data

def main():
    base_url = "https://web.archive.org/web/20250708180027/https://www.myfootdr.com.au/our-clinics/"
    
    # Create folder for cached pages
    os.makedirs('cached_pages', exist_ok=True)
    
    # Step 1: Download main page
    main_html = download_page(base_url, 'cached_pages/main.html')
    if not main_html:
        print("Failed to get main page")
        return
    
    soup = BeautifulSoup(main_html, 'html.parser')
    
    # Step 2: Find all links
    all_links = soup.find_all('a', href=True)
    
    clinic_links = []
    for link in all_links:
        href = link['href']
        if 'myfootdr.com.au/our-clinics/' in href or '/our-clinics/' in href:
            # Make sure it's a full URL
            if href.startswith('/web/'):
                href = 'https://web.archive.org' + href
            elif not href.startswith('http'):
                continue
            
            if href != base_url and 'our-clinics/#' not in href:
                clinic_links.append(href)
    
    clinic_links = list(set(clinic_links))
    print(f"\nFound {len(clinic_links)} unique links to explore\n")
    
    # Step 3: Download and parse each page
    all_clinics = []
    
    for i, link in enumerate(clinic_links):
        # Create safe filename
        safe_name = re.sub(r'[^\w]', '_', link[-50:])
        filename = f'cached_pages/page_{i}_{safe_name}.html'
        
        html = download_page(link, filename)
        
        if html:
            page_soup = BeautifulSoup(html, 'html.parser')
            clinic_data = extract_clinic_data(page_soup, link)
            
            if clinic_data['Name of Clinic'] and clinic_data['Name of Clinic'] != 'Our Clinics':
                all_clinics.append(clinic_data)
                print(f"  ✓ Found clinic: {clinic_data['Name of Clinic']}")
    
    # Step 4: Save results
    if all_clinics:
        df = pd.DataFrame(all_clinics)
        df.drop_duplicates(subset=['Name of Clinic'], inplace=True)
        df.to_csv('myfootdr_clinics.csv', index=False)
        print(f"\n{'='*50}")
        print(f"✓ Saved {len(df)} clinics to myfootdr_clinics.csv")
        print(f"{'='*50}")
        print(df.to_string())
    else:
        print("\nNo clinics found")

if __name__ == "__main__":
    main()


print()
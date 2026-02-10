import requests
from bs4 import BeautifulSoup
from lxml import etree
import json
import time
import re

# --- CONFIG ---
FETCH_LIMIT = 50
BASE_URL = "https://hobbygames.ru"
SITEMAP_URL = f"{BASE_URL}/sitemap_products.xml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def get_all_product_urls():
    """Fetches all product URLs from the sitemap."""
    print("Fetching sitemap...")
    try:
        r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        tree = etree.fromstring(r.content)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        # Products usually have 3 slashes: /category/subcategory/product
        return [loc.text for loc in tree.findall(".//s:loc", ns) if loc.text.count('/') == 3]
    except Exception as e:
        print(f"Sitemap error: {e}")
        return []

def scrape_product(url):
    """Deep scrapes a single product page with surgical precision."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')

        # 1. Basic Info
        name = soup.select_one('div.products-header h1').get_text(strip=True) if soup.select_one('div.products-header h1') else "N/A"
        price = soup.find(class_='product-card-price__current').get_text(strip=True) if soup.find(class_='product-card-price__current') else "N/A"

        # 2. Gallery Extraction (Targeting the 1980x1980 high-res links)
        gallery_images = []
        gallery_links = soup.find_all('a', class_='lightGallery')
        for link in gallery_links:
            img_path = link.get('href')
            if img_path:
                # Ensure absolute URL
                full_img_url = img_path if img_path.startswith('http') else BASE_URL + img_path
                if full_img_url not in gallery_images:
                    gallery_images.append(full_img_url)

        # 3. Content Blocks
        main_box = soup.find('div', id='container-main_content')
        description_text = ""
        package_text = ""
        details = {}

        if main_box:
            # A. The Story/Narrative
            story_div = main_box.find('div', id='desc')
            if story_div:
                description_text = story_div.get_text(separator="\n", strip=True)

            # B. The Components (Package)
            package_div = main_box.find('div', id='package')
            if package_div:
                package_text = package_div.get_text(separator="\n", strip=True)

            # C. Characteristics (Year, Manufacturer, etc.)
            m_div = main_box.find('div', class_='manufacturers')
            if m_div:
                # Target the label/value pairs specifically
                rows = m_div.find_all('div', class_=re.compile(r'col-(md|xs)-'))
                for row in rows:
                    label_tag = row.find(class_='manufacturers__label')
                    value_tag = row.find(class_='manufacturers__value')
                    if label_tag and value_tag:
                        key = label_tag.get_text(strip=True).replace(':', '')
                        val = value_tag.get_text(strip=True)
                        # If a key exists (like multiple producers), append it
                        if key in details:
                            details[key] = f"{details[key]}, {val}"
                        else:
                            details[key] = val

            # D. Product Code
            code_tag = main_box.find('div', class_='product-price-card__code')
            if code_tag:
                code_text = code_tag.get_text(strip=True)
                code_digits = "".join(filter(str.isdigit, code_text))
                details["product_code"] = code_digits

        return {
            "title": name,
            "price": price,
            "url": url,
            "description": description_text,
            "package": package_text,
            "details": details,
            "gallery": gallery_images
        }

    except Exception as e:
        print(f"Error on {url}: {e}")
        return None

def main(fetch_limit = None):
    urls = get_all_product_urls()
    results = []

    # --- ADJUST LIMIT HERE ---
    # Set to len(urls) for the full site. Using 3 for a quick test.
    limit = fetch_limit if fetch_limit is not None else len(urls)

    for i, url in enumerate(urls[:limit]):
        print(f"[{i+1}/{limit}] Processing: {url}")
        data = scrape_product(url)
        if data:
            results.append(data)
        time.sleep(0.3) # Ethical delay

    # Save to JSON
    filename = "hobbygames_full_export.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"\nDone! {len(results)} items saved to {filename}")

if __name__ == "__main__":
    main(FETCH_LIMIT)
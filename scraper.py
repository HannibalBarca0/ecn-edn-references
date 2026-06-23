#!/usr/bin/env python3
"""
ECN/EDN French Medical Textbook Research Scraper
Searches: Elsevier-Masson, Vernazobres-Grégo, S-Éditions, Decarre, Studyrama

This script uses curl to scrape publisher websites and find downloadable
ECN/EDN reference PDFs and textbooks for all medical specialties.
"""

import subprocess
import json
import re
import os
import sys
from urllib.parse import urljoin, quote
from html import escape
from datetime import datetime

def curl_get(url, timeout=30):
    """Fetch a URL with curl."""
    try:
        result = subprocess.run(
            ['curl', '-s', '-L', '--max-time', str(timeout),
             '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
             '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
             '-H', 'Accept-Language: fr-FR,fr;q=0.9,en;q=0.8',
             url],
            capture_output=True, text=True, timeout=timeout+5
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return f"TIMEOUT"
    except Exception as e:
        return f"Error: {e}"

def extract_price(html):
    """Extract price from HTML content."""
    # Look for common price patterns in French
    price_patterns = [
        r'(\d+[.,]\d{2})\s*[€€]',
        r'[€€]\s*(\d+[.,]\d{2})',
        r'prix[:\s]*(\d+[.,]\d{2})\s*[€€]',
        r'(\d+[.,]\d{2})\s*€\s*TTC',
        r'class="price"[^>]*>(\d+[.,]\d{2})',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1).replace(',', '.')
    return None

def extract_edition_year(html):
    """Extract edition year from HTML."""
    year_patterns = [
        r'(\d{4})[èe]me?\s*édition',
        r'[ée]dition\s*(\d{4})',
        r'(\d{4})\s*[-\u2013]\s*(\d{4})',
        r'EDN\s*(\d{4})',
        r'ECN\s*(\d{4})',
        r'ISBN[:\s]*[\d-]{10,17}',
    ]
    years = []
    for pattern in year_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                for y in m:
                    if y.isdigit() and 2010 <= int(y) <= 2030:
                        years.append(y)
            elif m.isdigit() and 2010 <= int(m) <= 2030:
                years.append(m)
    return sorted(set(years))

def extract_isbn(html):
    """Extract ISBN from HTML."""
    isbn_pattern = r'ISBN[:\s]*((?:\d[-\s]?){10,17})'
    match = re.search(isbn_pattern, html, re.IGNORECASE)
    return match.group(1).strip() if match else None

# ============================================================
# 1. ELSEVIER-MASSON - Collection des Collèges
# ============================================================
def search_elsevier_masson():
    print("=" * 80)
    print("ELSEVIER-MASSON (Collection des Collèges)")
    print("=" * 80)
    
    base = "https://www.elsevier-masson.fr"
    results = []
    
    # Search URLs to try
    search_urls = [
        ("Collection des Collèges", f"{base}/recherche/?q=collection+des+coll%C3%A8ges"),
        ("Collège EDN", f"{base}/recherche/?q=coll%C3%A8ge+EDN"),
        ("Collège ECN", f"{base}/recherche/?q=coll%C3%A8ge+ECN"),
        ("Catalogue Médecine", f"{base}/catalogue/medecine/"),
        ("Les collèges", f"{base}/catalogue/medecine/colleges/"),
        ("Collège + spécialités", f"{base}/recherche/?q=coll%C3%A8ge+de"),
    ]
    
    for label, url in search_urls:
        print(f"\n--- Searching: {label}")
        print(f"    URL: {url}")
        html = curl_get(url)
        if not html or "Error" in html[:100] or "TIMEOUT" in html[:100] or len(html) < 100:
            print(f"    Failed or empty response ({len(html) if html else 0} bytes)")
            continue
        
        print(f"    Got {len(html)} bytes")
        
        # Look for product URLs (various patterns)
        prod_patterns = [
            r'href=["\'](/product/[^"\']+)["\']',
            r'href=["\'](/p-[^"\']+)["\']',
            r'href=["\'](/livre[^"\']+)["\']',
            r'href=["\'](/ouvrage[^"\']+)["\']',
            r'href=["\'](/catalogue[^"\']+)["\']',
        ]
        
        for pattern in prod_patterns:
            links = re.findall(pattern, html)
            for link in links:
                full_url = urljoin(base, link)
                if full_url not in results:
                    results.append({
                        'url': full_url,
                        'source': label,
                        'publisher': 'Elsevier-Masson'
                    })
        
        # Extract book titles/specialties
        title_patterns = [
            r'(?:Coll[èe]ge\s+(?:des?|d[eu]\s*))([^<]+?(?:m[ée]decine|chirurgie|p[ée]diatrie|cardiologie|etc\.))',
            r'(?:Collection des Coll[èe]ges)[^<]*<[^>]*>([^<]+)',
            r'<h[23][^>]*>([^<]*(?:Coll[èe]ge|ECN|EDN|m[ée]decine|sp[ée]cialit[ée])[^<]*)</h[23]>',
            r'alt=["\']([^"\']*(?:Coll[èe]ge|ECN|EDN)[^"\']*)["\']',
        ]
        for pattern in title_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for m in matches[:5]:
                title = m.strip()
                if len(title) > 10:
                    print(f"    Found title: {escape(title)}")
        
        # Extract prices
        price = extract_price(html)
        if price:
            print(f"    Price found: {price}€")
        
        # Extract years
        years = extract_edition_year(html)
        if years:
            print(f"    Edition years found: {', '.join(years)}")
    
    return results

# ============================================================
# 2. VERNAZOBRES-GRÉGO - Référentiels des Collèges
# ============================================================
def search_vg_livres():
    print("\n" + "=" * 80)
    print("VERNAZOBRES-GRÉGO (Référentiels des Collèges)")
    print("=" * 80)
    
    base = "https://www.vg-livres.com"
    results = []
    
    search_urls = [
        ("ECN/EDN category", f"{base}/104-edn-ecn"),
        ("Référentiels", f"{base}/recherche?controller=search&s=r%C3%A9f%C3%A9rentiel"),
        ("Collège search", f"{base}/recherche?controller=search&s=coll%C3%A8ge"),
        ("ECN search", f"{base}/recherche?controller=search&s=ECN"),
        ("EDN search", f"{base}/recherche?controller=search&s=EDN"),
        ("Médecine", f"{base}/recherche?controller=search&s=m%C3%A9decine"),
        ("Home", base + "/"),
    ]
    
    for label, url in search_urls:
        print(f"\n--- Searching: {label}")
        print(f"    URL: {url}")
        html = curl_get(url)
        if not html or "Error" in html[:100] or "TIMEOUT" in html[:100] or len(html) < 100:
            print(f"    Failed or empty ({len(html) if html else 0} bytes)")
            continue
        
        print(f"    Got {len(html)} bytes")
        
        # Look for product links (PrestaShop pattern)
        prods = re.findall(r'href=["\']([^"\']+)["\']', html)
        for link in prods:
            full_url = urljoin(base, link) if not link.startswith('http') else link
            if any(kw in full_url.lower() for kw in ['product', 'livre', 'manuel', 'ouvrage', 'edn', 'ecn', 'colleg', 'referentiel']):
                if full_url not in [r['url'] for r in results]:
                    results.append({
                        'url': full_url,
                        'source': label,
                        'publisher': 'Vernazobres-Grégo'
                    })
        
        # Extract product names from images
        imgs = re.findall(r'alt=["\']([^"\']+)["\']', html)
        for img in imgs:
            if any(kw in img.lower() for kw in ['ecn', 'edn', 'colleg', 'referent', 'medecine', 'specialite']):
                print(f"    Product image: {escape(img.strip())}")
        
        # Look for category links  
        cats = re.findall(r'href=["\'](/recherche[^"\']*id_category=\d+)["\']', html)
        for cat_url in cats[:5]:
            full_url = urljoin(base, cat_url)
            if full_url not in [r['url'] for r in results]:
                results.append({
                    'url': full_url,
                    'source': f"Category from {label}",
                    'publisher': 'Vernazobres-Grégo'
                })
        
        # Extract prices
        prices = re.findall(r'(?:price|prix)[^:]*:\s*(\d+[.,]\d{2})', html)
        for p in prices[:3]:
            print(f"    Price: {p}€")
        
        prices2 = re.findall(r'<span[^>]*class=["\']price[^"\']*["\'][^>]*>(\d+[.,]\d{2})', html)
        for p in prices2[:3]:
            print(f"    Price (span): {p}€")
        
        # Edition years
        years = extract_edition_year(html)
        if years:
            print(f"    Years: {', '.join(years)}")
    
    return results

# ============================================================
# 3. S-ÉDITIONS (Éditions S)
# ============================================================
def search_s_editions():
    print("\n" + "=" * 80)
    print("S-ÉDITIONS (Éditions S)")
    print("=" * 80)
    
    # Try multiple possible domains for S-Éditions
    domains = [
        "https://www.s-editions.com",
        "https://editions-s.com",
        "https://www.editions-s.com",
        "https://www.librairie-s-editions.com",
    ]
    
    results = []
    for base in domains:
        urls_to_try = [
            base,
            base + "/fr/",
            base + "/medecine/",
            base + "/catalogue/",
        ]
        
        for url in urls_to_try:
            print(f"\n--- Trying: {url}")
            html = curl_get(url)
            if not html or "Error" in html[:100] or "TIMEOUT" in html[:100] or len(html) < 200:
                print(f"    No response ({len(html) if html else 0} bytes)")
                continue
            
            print(f"    Got {len(html)} bytes - page title: ", end="")
            title_m = re.search(r'<title>([^<]+)</title>', html)
            if title_m:
                print(title_m.group(1))
            else:
                print("(no title)")
            
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
            for link in links:
                full_url = urljoin(base, link)
                if any(kw in link.lower() for kw in ['ecn', 'edn', 'colleg', 'medecin', 'livre', 'ouvrage', 'produit']):
                    if full_url not in [r['url'] for r in results]:
                        results.append({
                            'url': full_url,
                            'source': f"S-Éditions ({base})",
                            'publisher': 'S-Éditions'
                        })
            
            # Extract any visible text about ECN/EDN
            matches = re.findall(r'(?:ECN|EDN)[^<]{3,100}', html)
            for m in matches[:5]:
                print(f"    Content: {escape(m.strip())}")
    
    return results

# ============================================================
# 4. DECARRE
# ============================================================
def search_decarre():
    print("\n" + "=" * 80)
    print("DECARRE")
    print("=" * 80)
    
    domains = ["https://www.decarre.fr", "https://www.editions-decarre.fr"]
    results = []
    
    for base in domains:
        search_urls = [
            base,
            base + "/medecine/",
            base + "/recherche/?q=ECN",
            base + "/recherche/?q=EDN",
            base + "/recherche/?q=coll%C3%A8ge",
            base + "/recherche/?q=m%C3%A9decine",
        ]
        
        for url in search_urls:
            print(f"\n--- Trying: {url}")
            html = curl_get(url)
            if not html or "Error" in html[:100] or "TIMEOUT" in html[:100] or len(html) < 200:
                print(f"    No response ({len(html) if html else 0} bytes)")
                continue
            
            print(f"    Got {len(html)} bytes")
            title_m = re.search(r'<title>([^<]+)</title>', html)
            if title_m:
                print(f"    Title: {title_m.group(1)}")
            
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
            for link in links:
                full_url = urljoin(base, link)
                if any(kw in link.lower() for kw in ['ecn', 'edn', 'colleg', 'medecin', 'livre', 'ouvrage', 'produit']):
                    if full_url not in [r['url'] for r in results]:
                        results.append({
                            'url': full_url,
                            'source': f"Decarre ({base})",
                            'publisher': 'Decarre'
                        })
            
            matches = re.findall(r'(?:ECN|EDN|Coll[èe]ge)[^<]{3,100}', html)
            for m in matches[:5]:
                print(f"    Content: {escape(m.strip())}")
    
    return results

# ============================================================
# 5. STUDYRAMA
# ============================================================
def search_studyrama():
    print("\n" + "=" * 80)
    print("STUDYRAMA")
    print("=" * 80)
    
    base = "https://www.studyrama.com"
    results = []
    
    search_urls = [
        base,
        base + "/revision/medecine/",
        base + "/revision/",
        base + "/?s=ECN",
        base + "/?s=EDN",
        base + "/?s=coll%C3%A8ge+m%C3%A9decine",
        base + "/?s=r%C3%A9f%C3%A9rentiel+m%C3%A9decine",
    ]
    
    for url in search_urls:
        print(f"\n--- Fetching: {url}")
        html = curl_get(url)
        if not html or "Error" in html[:100] or "TIMEOUT" in html[:100] or len(html) < 200:
            print(f"    No response ({len(html) if html else 0} bytes)")
            continue
        
        print(f"    Got {len(html)} bytes")
        title_m = re.search(r'<title>([^<]+)</title>', html)
        if title_m:
            print(f"    Title: {title_m.group(1)}")
        
        links = re.findall(r'href=["\']([^"\']+)["\']', html)
        for link in links:
            full_url = urljoin(base, link)
            if any(kw in link.lower() for kw in ['ecn', 'edn', 'colleg', 'medecin', 'livre', 'manuel', 'ouvrage']):
                if full_url not in [r['url'] for r in results]:
                    results.append({
                        'url': full_url,
                        'source': f"Studyrama",
                        'publisher': 'Studyrama'
                    })
        
        # Look for book/PDF content
        matches = re.findall(r'(?:ECN|EDN|Coll[èe]ge)[^<]{3,150}', html)
        for m in matches[:5]:
            print(f"    Content: {escape(m.strip())}")
    
    return results

# ============================================================
# DEEP PRODUCT SCRAPE
# ============================================================
def scrape_product_details(url, publisher):
    """Scrape details from a specific product page."""
    print(f"  Scraping: {url}")
    html = curl_get(url)
    if not html or len(html) < 100:
        return None
    
    details = {
        'url': url,
        'publisher': publisher,
        'title': None,
        'price': None,
        'isbn': None,
        'year': None,
        'specialty': None,
        'format': None,
        'pdf_available': False,
    }
    
    # Extract title
    title_m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    if title_m:
        details['title'] = title_m.group(1).strip()
    
    # Also try meta title
    if not details['title']:
        title_m = re.search(r'<title>([^<]+)</title>', html)
        if title_m:
            details['title'] = title_m.group(1).strip()
    
    # Price
    price = extract_price(html)
    if price:
        details['price'] = price
    
    # ISBN
    isbn = extract_isbn(html)
    if isbn:
        details['isbn'] = isbn
    
    # Year
    years = extract_edition_year(html)
    if years:
        details['year'] = years[-1]  # latest year
    
    # Look for PDF/download links
    pdf_links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', html)
    if pdf_links:
        details['pdf_available'] = True
        details['pdf_links'] = pdf_links
    
    # Look for download buttons
    dl_patterns = [
        r't[eé]l[eé]charger',
        r'download',
        r'pdf',
        r'version num[eé]rique',
        r'ebook',
        r'num[eé]rique',
    ]
    for pat in dl_patterns:
        if re.search(pat, html, re.IGNORECASE):
            details['pdf_available'] = True
            details['format'] = 'PDF/Numérique'
    
    # Determine specialty from title or content
    specialties_db = [
        'Allergologie', 'Anatomie', 'Anesthésie-Réanimation', 'Biologie Médicale',
        'Cardiologie', 'Chirurgie Générale', 'Chirurgie Orthopédique', 'Chirurgie Pédiatrique',
        'Chirurgie Plastique', 'Chirurgie Thoracique', 'Chirurgie Vasculaire',
        'Dermatologie', 'Endocrinologie', 'Gastro-Entérologie', 'Génétique Médicale',
        'Gériatrie', 'Gynécologie Médicale', 'Gynécologie Obstétrique', 'Hématologie',
        'Hépatologie', 'Infectiologie', 'Médecine Générale', 'Médecine Intensive',
        'Médecine Interne', 'Médecine Légale', 'Médecine Nucléaire', 'Médecine Physique',
        'Médecine du Travail', 'Néphrologie', 'Neurochirurgie', 'Neurologie',
        'Nutrition', 'Oncologie', 'Ophtalmologie', 'ORL', 'Pédiatrie',
        'Pharmacologie', 'Physiologie', 'Pneumologie', 'Psychiatrie', 'Radiologie',
        'Rhumatologie', 'Santé Publique', 'Stomatologie', 'Urgences', 'Urologie',
    ]
    
    if details['title']:
        title_lower = details['title'].lower()
        for spec in specialties_db:
            if spec.lower() in title_lower:
                details['specialty'] = spec
                break
    
    return details


# ============================================================
# MAIN
# ============================================================
def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("ECN/EDN French Medical Textbook Research Scraper")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Output dir: {output_dir}")
    print("=" * 80)
    
    # Phase 1: Discovery - find product URLs from each publisher
    all_products = {}
    
    print("\n\n>>> PHASE 1: DISCOVERY <<<\n")
    
    print("\n>>> Searching Elsevier-Masson...")
    all_products['elsevier_masson'] = search_elsevier_masson()
    
    print("\n>>> Searching Vernazobres-Grégo...")
    all_products['vg_livres'] = search_vg_livres()
    
    print("\n>>> Searching S-Éditions...")
    all_products['s_editions'] = search_s_editions()
    
    print("\n>>> Searching Decarre...")
    all_products['decarre'] = search_decarre()
    
    print("\n>>> Searching Studyrama...")
    all_products['studyrama'] = search_studyrama()
    
    # Save discovery results
    with open(os.path.join(output_dir, 'discovery_results.json'), 'w') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    
    # Phase 2: Deep scrape top products
    print("\n\n>>> PHASE 2: DEEP SCRAPE <<<\n")
    
    deep_results = []
    seen_urls = set()
    
    for publisher, products in all_products.items():
        print(f"\n--- Deep scraping {len(products)} products from {publisher} ---")
        for i, product in enumerate(products[:30]):  # Limit to 30 per publisher
            url = product['url']
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            details = scrape_product_details(url, product['publisher'])
            if details:
                deep_results.append(details)
                print(f"    Title: {details.get('title', 'N/A')[:80]}")
                print(f"    Price: {details.get('price', 'N/A')}€ | Year: {details.get('year', 'N/A')}")
                print(f"    ISBN: {details.get('isbn', 'N/A')} | PDF: {details.get('pdf_available', False)}")
                print()
    
    # Save deep results
    with open(os.path.join(output_dir, 'deep_results.json'), 'w') as f:
        json.dump(deep_results, f, indent=2, ensure_ascii=False)
    
    # Phase 3: Summary
    print("\n\n>>> SUMMARY <<<\n")
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'publishers': {}
    }
    
    total_products = 0
    for publisher, products in all_products.items():
        count = len(products)
        total_products += count
        print(f"{publisher}: {count} URLs found")
        
        summary['publishers'][publisher] = {
            'url_count': count,
            'sample_urls': [p['url'] for p in products[:10]]
        }
    
    # Count deep results with prices
    priced = [d for d in deep_results if d.get('price')]
    with_year = [d for d in deep_results if d.get('year')]
    with_isbn = [d for d in deep_results if d.get('isbn')]
    pdf_available = [d for d in deep_results if d.get('pdf_available')]
    
    print(f"\nTotal unique URLs discovered: {total_products}")
    print(f"Deep scraped: {len(deep_results)}")
    print(f"  With prices: {len(priced)}")
    print(f"  With edition years: {len(with_year)}")
    print(f"  With ISBN: {len(with_isbn)}")
    print(f"  With PDF/numerique: {len(pdf_available)}")
    
    summary['deep_scrape'] = {
        'total': len(deep_results),
        'with_price': len(priced),
        'with_year': len(with_year),
        'with_isbn': len(with_isbn),
        'pdf_available': len(pdf_available),
        'products': deep_results
    }
    
    with open(os.path.join(output_dir, 'final_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_dir}")
    print("=" * 80)
    print("DONE")

if __name__ == "__main__":
    main()

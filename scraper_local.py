#!/usr/bin/env python3
"""
ECN/EDN French Medical Textbook Research Scraper - RUN LOCALLY IN /opt/data
"""
import subprocess, json, re, os, sys
from urllib.parse import urljoin
from html import escape
from datetime import datetime

def curl_get(url, timeout=30):
    try:
        r = subprocess.run(['curl', '-s', '-L', '--max-time', str(timeout),
             '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
             '-H', 'Accept-Language: fr-FR,fr;q=0.9',
             url], capture_output=True, text=True, timeout=timeout+5)
        return r.stdout
    except: return ""

def extract_price(html):
    for p in [r'(\d+[.,]\d{2})\s*[€€]', r'[€€]\s*(\d+[.,]\d{2})', r'prix[:\s]*(\d+[.,]\d{2})', r'class="price"[^>]*>(\d+[.,]\d{2})']:
        m = re.search(p, html)
        if m: return m.group(1).replace(',','.')
    return None

def extract_years(html):
    ys = set()
    for p in [r'(\d{4})[èe]me?\s*édition', r'[ée]dition\s*(\d{4})', r'EDN\s*(\d{4})', r'ECN\s*(\d{4})']:
        for m in re.findall(p, html, re.I):
            if m.isdigit() and 2010 <= int(m) <= 2030: ys.add(m)
    return sorted(ys)

def extract_isbn(html):
    m = re.search(r'ISBN[:\s]*((?:\d[-\s]?){10,17})', html, re.I)
    return m.group(1).strip() if m else None

def search_site(name, urls, base_url, publisher, kw_check=None):
    results = []
    for label, url in urls:
        print(f"\n--- {name}: {label}")
        print(f"    URL: {url}")
        html = curl_get(url)
        if not html or len(html) < 100:
            print(f"    Failed ({len(html)} bytes)")
            continue
        print(f"    Got {len(html)} bytes")
        title_m = re.search(r'<title>([^<]+)</title>', html)
        if title_m: print(f"    Title: {title_m.group(1)[:80]}")

        # Extract all links
        for link in re.findall(r'href=["\']([^"\']+)["\']', html):
            full = urljoin(base_url, link) if not link.startswith('http') else link
            if kw_check and not any(k in full.lower() for k in kw_check): continue
            if full not in [r['url'] for r in results]:
                results.append({'url': full, 'source': label, 'publisher': publisher})

        # Show matches
        for m in re.findall(r'(?:ECN|EDN|Coll[èe]ge)[^<]{3,120}', html)[:5]:
            print(f"    Match: {escape(m.strip()[:100])}")

        price = extract_price(html)
        if price: print(f"    Price: {price}€")
        years = extract_years(html)
        if years: print(f"    Years: {', '.join(years)}")
        isbn = extract_isbn(html)
        if isbn: print(f"    ISBN: {isbn}")
    return results

def scrape_product(url, publisher):
    html = curl_get(url)
    if not html or len(html) < 100: return None
    d = {'url': url, 'publisher': publisher, 'title': None, 'price': None, 'isbn': None, 'year': None, 'specialty': None, 'pdf': False}
    m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    if m: d['title'] = m.group(1).strip()
    if not d['title']:
        m = re.search(r'<title>([^<]+)</title>', html)
        if m: d['title'] = m.group(1).strip()
    d['price'] = extract_price(html)
    d['isbn'] = extract_isbn(html)
    yrs = extract_years(html)
    if yrs: d['year'] = yrs[-1]
    if re.search(r'(t[eé]l[eé]charger|pdf|version num[eé]rique|ebook|num[eé]rique)', html, re.I):
        d['pdf'] = True
    specs = ['Allergologie','Anatomie','Anesthésie-Réanimation','Biologie Médicale','Cardiologie',
        'Chirurgie Générale','Chirurgie Orthopédique','Chirurgie Pédiatrique','Chirurgie Plastique',
        'Chirurgie Thoracique','Chirurgie Vasculaire','Dermatologie','Endocrinologie',
        'Gastro-Entérologie','Génétique Médicale','Gériatrie','Gynécologie Médicale',
        'Gynécologie Obstétrique','Hématologie','Hépatologie','Infectiologie','Médecine Générale',
        'Médecine Intensive','Médecine Interne','Médecine Légale','Médecine Nucléaire',
        'Médecine Physique','Médecine du Travail','Néphrologie','Neurochirurgie','Neurologie',
        'Nutrition','Oncologie','Ophtalmologie','ORL','Pédiatrie','Pharmacologie','Physiologie',
        'Pneumologie','Psychiatrie','Radiologie','Rhumatologie','Santé Publique','Stomatologie',
        'Urgences','Urologie']
    if d['title']:
        tl = d['title'].lower()
        for s in specs:
            if s.lower() in tl: d['specialty'] = s; break
    return d

def main():
    output_dir = "/opt/data"
    print(f"ECN/EDN Scraper - Output: {output_dir}")
    print("="*80)

    kw = ['ecn','edn','colleg','medecin','livre','ouvrage','produit','manuel','referentiel','specialite']

    # 1. ELSEVIER-MASSON
    em_urls = [
        ("Collèges search", "https://www.elsevier-masson.fr/recherche/?q=collection+des+coll%C3%A8ges"),
        ("EDN search", "https://www.elsevier-masson.fr/recherche/?q=coll%C3%A8ge+EDN"),
        ("ECN search", "https://www.elsevier-masson.fr/recherche/?q=coll%C3%A8ge+ECN"),
        ("Catalogue Méd", "https://www.elsevier-masson.fr/catalogue/medecine/"),
        ("Collèges cat", "https://www.elsevier-masson.fr/catalogue/medecine/colleges/"),
    ]
    em = search_site("Elsevier-Masson", em_urls, "https://www.elsevier-masson.fr", "Elsevier-Masson", kw)

    # 2. VERNAZOBRES-GRÉGO
    vg_urls = [
        ("ECN/EDN cat", "https://www.vg-livres.com/104-edn-ecn"),
        ("Référentiels", "https://www.vg-livres.com/recherche?controller=search&s=r%C3%A9f%C3%A9rentiel"),
        ("Collège", "https://www.vg-livres.com/recherche?controller=search&s=coll%C3%A8ge"),
        ("ECN", "https://www.vg-livres.com/recherche?controller=search&s=ECN"),
        ("EDN", "https://www.vg-livres.com/recherche?controller=search&s=EDN"),
        ("Médecine", "https://www.vg-livres.com/recherche?controller=search&s=m%C3%A9decine"),
    ]
    vg = search_site("Vernazobres-Grégo", vg_urls, "https://www.vg-livres.com", "Vernazobres-Grégo", kw)

    # 3. S-ÉDITIONS
    se_domains = ["https://www.s-editions.com", "https://editions-s.com", "https://www.editions-s.com"]
    se = []
    for d in se_domains:
        se_urls = [(d, d)]
        se += search_site(f"S-Éditions({d})", se_urls, d, "S-Éditions", kw)

    # 4. DECARRE
    de_urls = [
        ("Home", "https://www.decarre.fr/"),
        ("Médecine", "https://www.decarre.fr/medecine/"),
        ("ECN", "https://www.decarre.fr/recherche/?q=ECN"),
        ("EDN", "https://www.decarre.fr/recherche/?q=EDN"),
        ("Collège", "https://www.decarre.fr/recherche/?q=coll%C3%A8ge"),
    ]
    de = search_site("Decarre", de_urls, "https://www.decarre.fr", "Decarre", kw)

    # 5. STUDYRAMA
    st_urls = [
        ("Médecine", "https://www.studyrama.com/revision/medecine/"),
        ("ECN", "https://www.studyrama.com/?s=ECN"),
        ("EDN", "https://www.studyrama.com/?s=EDN"),
        ("Collège", "https://www.studyrama.com/?s=coll%C3%A8ge+m%C3%A9decine"),
    ]
    st = search_site("Studyrama", st_urls, "https://www.studyrama.com", "Studyrama", kw)

    all_products = {
        'elsevier_masson': em,
        'vg_livres': vg,
        's_editions': se,
        'decarre': de,
        'studyrama': st
    }

    # Save discovery
    with open(os.path.join(output_dir, 'discovery_results.json'), 'w') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"\nDiscovery results saved ({sum(len(v) for v in all_products.values())} total URLs)")

    # Deep scrape
    print("\n>>> DEEP SCRAPE <<<")
    deep = []
    seen = set()
    for pub, prods in all_products.items():
        print(f"\n{pub}: deep scraping up to {min(20, len(prods))} products")
        for p in prods[:20]:
            if p['url'] in seen: continue
            seen.add(p['url'])
            d = scrape_product(p['url'], p['publisher'])
            if d:
                deep.append(d)
                print(f"  {d.get('title','N/A')[:60]} | {d.get('price','N/A')}€ | yr:{d.get('year','?')} | PDF:{d.get('pdf',False)}")

    with open(os.path.join(output_dir, 'deep_results.json'), 'w') as f:
        json.dump(deep, f, indent=2, ensure_ascii=False)
    print(f"\nDeep results saved ({len(deep)} products)")

    # Summary
    print("\n>>> SUMMARY <<<")
    for pub, prods in all_products.items():
        print(f"  {pub}: {len(prods)} URLs")
    print(f"  Deep scraped: {len(deep)} products")
    print(f"  With prices: {sum(1 for d in deep if d.get('price'))}")
    print(f"  With years: {sum(1 for d in deep if d.get('year'))}")
    print(f"  With ISBN: {sum(1 for d in deep if d.get('isbn'))}")
    print(f"  With PDF: {sum(1 for d in deep if d.get('pdf'))}")
    print(f"  Unique specialties found: {len(set(d.get('specialty') for d in deep if d.get('specialty')))}")
    print("\nDone!")

if __name__ == "__main__":
    main()

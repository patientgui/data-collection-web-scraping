import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re 

from selenium import webdriver

# ============================================================
# PARAMÈTRES GÉNÉRAUX
# ============================================================

def get_random_headers():
    """Fournit des headers aléatoires pour masquer le bot."""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20101010 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Connection": "keep-alive"
    }

MAX_PAGES_LI_SL = 25     
MAX_PAGES_ORPI = 10    


# ============================================================
# FONCTIONS UTILITAIRES D'EXTRACTION ET DE NETTOYAGE
# ============================================================

def normalize_spaces(text: str) -> str:
    """Remplace les espaces spéciaux par des espaces normaux."""
    return (
        text.replace("\u00a0", " ")
            .replace("\u202f", " ")
    )

def clean_city_name(city_name):
    """Normalise une chaîne de ville."""
    if not city_name: return None
    city_name = str(city_name).upper().strip()
    city_name = re.sub(r'[\d\W_]', ' ', city_name) 
    city_name = re.sub(r'\s+', ' ', city_name).strip()
    return city_name if len(city_name) > 1 else None

def find_code_postal(text):
    """Extrait le premier code postal (5 chiffres d'affilée) dans un texte."""
    if not isinstance(text, str): return None
    txt = normalize_spaces(text)
    cp_match = re.search(r"(\d{5})", txt)
    return cp_match.group(1) if cp_match else None

def extract_city_from_text(text, cp):
    """Ville = premier mot juste après le code postal dans le texte."""
    if not isinstance(text, str) or cp is None: return None
    txt = normalize_spaces(text)
    idx = txt.find(cp)
    if idx == -1: return None
    after = txt[idx + len(cp):].strip()
    tokens = after.split()
    if not tokens: return None
    return clean_city_name(tokens[0])

def extract_price(text):
    """Extrait le prix en euros."""
    if pd.isna(text): return None
    text = str(text)
    matches = re.findall(r"([\d\s\u202f\u00a0]+)\s*€", text)
    if not matches: return None
    raw_num = matches[0]
    clean_num = re.sub(r"[^\d]", "", raw_num)
    return float(clean_num) if clean_num else None

def extract_surface(text):
    """Extrait la surface en m²."""
    if pd.isna(text): return None
    text = str(text)
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*m", text)
    if not matches: return None
    num = matches[0].replace(",", ".")
    try: return float(num)
    except ValueError: return None

def extract_rooms(text):
    """Extrait le nombre de pièces."""
    if pd.isna(text): return None
    text = str(text).lower()
    matches = re.findall(r"(\d+)\s*(?:pièce|pièces|p)", text)
    if not matches: return None
    try: return int(matches[0])
    except ValueError: return None


# ============================================================
# LISTES D'URL LOGIC-IMMO & SELOGER (Inchangées)
# ============================================================

SEARCHES_LOGICIMMO = [
    {
        "region": "Hauts-de-France",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR16&m=homepage_relaunch_my_last_search_classified_search_result",
    },
    {
        "region": "Île-de-France",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR5",
    },
    {
        "region": "Normandie",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR14",
    },
    {
        "region": "Bretagne",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR22",
    },
    {
        "region": "Pays de la Loire",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR21",
    },
    {
        "region": "Centre-Val de Loire",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR10",
    },
    {
        "region": "Bourgogne-Franche-Comté",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR13",
    },
    {
        "region": "Grand Est",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR20",
    },
    {
        "region": "Nouvelle-Aquitaine",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR27",
    },
    {
        "region": "Occitanie",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR28",
    },
    {
        "region": "Auvergne-Rhône-Alpes",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR31",
    },
    {
        "region": "Provence-Alpes-Côte d'Azur",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR33",
    },
    {
        "region": "Corse",
        "url": "https://www.logic-immo.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR34",
    },
]

SEARCHES_SELOGER = [
    {
        "region": "Hauts-de-France",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy,Buy_Auction,Compulsory_Auction&estateTypes=House,Apartment&locations=AD04FR16&order=Default&m=homepage_new_search_classified_search_result",
    },
    {
        "region": "Île-de-France",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR5",
    },
    {
        "region": "Normandie",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR14",
    },
    {
        "region": "Bretagne",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR22",
    },
    {
        "region": "Pays de la Loire",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR21",
    },
    {
        "region": "Centre-Val de Loire",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR10",
    },
    {
        "region": "Bourgogne-Franche-Comté",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR13",
    },
    {
        "region": "Grand Est",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR20",
    },
    {
        "region": "Nouvelle-Aquitaine",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR27",
    },
    {
        "region": "Occitanie",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR28",
    },
    {
        "region": "Auvergne-Rhône-Alpes",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR31",
    },
    {
        "region": "Provence-Alpes-Côte d'Azur",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR33",
    },
    {
        "region": "Corse",
        "url": "https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=House,Apartment&locations=AD04FR34",
    },
]


# URL ORPI (PAR GRANDES VILLES - Inchangées)
ORPI_URLS = {
    "Île-de-France": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=paris",
    "Auvergne-Rhône-Alpes": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=lyon-3&locations%5B0%5D%5Blabel%5D=Lyon%203%20%2869003%29&locations%5B0%5D%5Blatitude%5D=45.7516&locations%5B0%5D%5Blongitude%5D=4.8681&sort=date-down&layoutType=list",
    "Provence-Alpes-Côte d'Azur": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=marseille&locations%5B0%5D%5Blabel%5D=Marseille%20-%20M%C3%A9tropole&locations%5B0%5D%5Blatitude%5D=43.2939&locations%5B0%5D%5Blongitude%5D=5.4048&sort=date-down&layoutType=list",
    "Nouvelle-Aquitaine": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=bordeaux&locations%5B0%5D%5Blabel%5D=Bordeaux%20%2833000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=44.862&locations%5B0%5D%5Blongitude%5D=-0.625728&sort=date-down&layoutType=list",
    "Occitanie": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=toulouse&locations%5B0%5D%5Blabel%5D=Toulouse%20%2831000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=43.6007&locations%5B0%5D%5Blongitude%5D=1.42924&sort=date-down&layoutType=list",
    "Hauts-de-France": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=lille&locations%5B0%5D%5Blabel%5D=Lille%20-%20Ville&locations%5B0%5D%5Blatitude%5D=50.6311&locations%5B0%5D%5Blongitude%5D=3.04663&sort=date-down&layoutType=list",
    "Grand Est": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=strasbourg&locations%5B0%5D%5Blabel%5D=Strasbourg%20%2867000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=48.5703&locations%5B0%5D%5Blongitude%5D=7.75625&sort=date-down&layoutType=list",
    "Bretagne": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=rennes&locations%5B0%5D%5Blabel%5D=Rennes%20%2835000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=48.1143&locations%5B0%5D%5Blongitude%5D=-1.68803&sort=date-down&layoutType=list",
    "Normandie": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=rouen&locations%5B0%5D%5Blabel%5D=Rouen%20%2876000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=49.4406&locations%5B0%5D%5Blongitude%5D=1.09106&sort=date-down&layoutType=list",
    "Pays de la Loire": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=nantes&locations%5B0%5D%5Blabel%5D=Nantes%20%2844000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=47.2363&locations%5B0%5D%5Blongitude%5D=-1.56302&sort=date-down&layoutType=list",
    "Centre-Val de Loire": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=orleans&locations%5B0%5D%5Blabel%5D=Orl%C3%A9ans%20%2845000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=47.8735&locations%5B0%5D%5Blongitude%5D=1.91959&sort=date-down&layoutType=list",
    "Bourgogne-Franche-Comté": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=dijon&locations%5B0%5D%5Blabel%5D=Dijon%20%2821000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=47.3334&locations%5B0%5D%5Blongitude%5D=5.03074&sort=date-down&layoutType=list",
    "Corse": "https://www.orpi.com/recherche/buy?transaction=buy&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=ajaccio&locations%5B0%5D%5Blabel%5D=Ajaccio%20%2820000%29%20-%20Ville&locations%5B0%5D%5Blatitude%5D=41.9284&locations%5B0%5D%5Blongitude%5D=8.70431&sort=date-down&layoutType=list",
}


# ============================================================
# LOGIC-IMMO & SELOGER 
# ============================================================

def get_page_html(url, page, site_name):
    headers = get_random_headers()
    params = {"page": page} if page > 1 else {}
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
    except Exception as e:
        print(f"   - Erreur réseau {site_name} :", e)
        return None

    if r.status_code != 200:
        print(f"   - ÉCHEC HTTP {site_name}. Statut : {r.status_code}. (Possible blocage)")
        return None

    return r.text


def parse_page_li_sl(html, region, source_name):
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    for img in soup.find_all("img", alt=True):
        alt = img["alt"].strip()
        t = alt.lower()

        if "appartement" not in t and "maison" not in t:
            continue

        prix_num = extract_price(alt)
        surface_m2_num = extract_surface(alt)
        rooms_num = extract_rooms(alt)

        rows.append({
            "raw_alt": alt,
            "region": region,
            "source": source_name,
            "titre": None,
            "prix": prix_num, 
            "localisation": None, 
            "code_postal": None, 
            "ville": None, 
            "surface_m2": surface_m2_num,
            "rooms": rooms_num,
        })

    return rows


def scrape_site_li_sl(searches, source_name):
    all_rows = []

    for s in searches:
        region = s["region"]
        url = s["url"]
        print(f"\n=== {source_name} – Région : {region} ===")

        for page in range(1, MAX_PAGES_LI_SL + 1):
            print(f"Page {page}")
            html = get_page_html(url, page, source_name)
            if html is None:
                if page == 1:
                    print("   -> Échec à la première page, arrêt de la région.")
                break

            page_rows = parse_page_li_sl(html, region, source_name)
            print("   ->", len(page_rows), "annonces trouvées.")

            if not page_rows:
                break

            all_rows.extend(page_rows)
            time.sleep(random.uniform(1, 2))

    if not all_rows:
        print(f"\nAucune annonce récupérée pour {source_name}.")
        return pd.DataFrame()

    return pd.DataFrame(all_rows)


# ============================================================
# ORPI (Fonction corrigée pour éviter "CLICHY")
# ============================================================

def get_orpi_details(driver, url_detail):
    """
    Va sur la page détail ORPI et récupère (code_postal, ville).
    CORRECTION : Limite la recherche du CP aux premiers caractères pour éviter les CPs parasites.
    """
    if not url_detail: return None, None

    try:
        driver.get(url_detail)
        time.sleep(2)

        html = driver.page_source
        soup = BeautifulSoup(html, "lxml")

        # --- CORRECTION ICI ---
        # On prend le texte entier mais on le tronque aux 500 premiers caractères.
        # Cette zone contient l'adresse et évite le footer/bandeaux parasites.
        full_text = soup.get_text(" ", strip=True)
        text_to_search = full_text[:500] 
        # ----------------------

        cp = find_code_postal(text_to_search)
        ville = extract_city_from_text(text_to_search, cp) 

        return cp, ville

    except Exception as e:
        print(f"   -> Erreur get_orpi_details ({url_detail}) :", e)
        return None, None


def scrape_orpi():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    all_rows = []

    for region, base_url in ORPI_URLS.items():
        for page_num in range(1, MAX_PAGES_ORPI + 1):
            if page_num == 1:
                full_url = base_url
            else:
                full_url = base_url + f"&page={page_num}"

            print(f"\n=== ORPI – {region} – page {page_num} ===")
            driver.get(full_url)
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "lxml")
            annonces = soup.find_all("article")
            print("   ->", len(annonces), "annonces trouvées")

            for ann in annonces:
                titre_el = ann.find("div", class_="c-estate-thumb__infos__estate")
                prix_el = ann.find("span", class_="c-estate-thumb__price-tag__price")
                loc_el = ann.find("span", class_="c-estate-thumb__infos__location")
                link_el = ann.find("a", href=True)

                titre = titre_el.get_text(strip=True) if titre_el else None
                prix_brut = prix_el.get_text(strip=True) if prix_el else None
                localisation = loc_el.get_text(strip=True) if loc_el else None

                if link_el:
                    href = link_el["href"]
                    # L'url est nécessaire pour la fonction get_orpi_details
                    url_detail = "https://www.orpi.com" + href if not href.startswith("http") else href
                else:
                    url_detail = None

                cp, ville_detail = get_orpi_details(driver, url_detail)

                raw_alt_parts = [titre, prix_brut, localisation, cp, ville_detail]
                raw_alt = " ".join(str(x) for x in raw_alt_parts if x)

                prix_num = extract_price(prix_brut)
                surface_m2 = extract_surface(raw_alt)
                rooms = extract_rooms(raw_alt)

                all_rows.append({
                    "raw_alt": raw_alt,
                    "region": region,
                    "source": "orpi",
                    "titre": titre,
                    "prix": prix_num,
                    "localisation": localisation,
                    "code_postal": cp,
                    "ville": ville_detail,
                    "surface_m2": surface_m2,
                    "rooms": rooms,
                })

    driver.quit()
    if not all_rows:
        print("\nAucune annonce ORPI récupérée.")
        return pd.DataFrame()

    return pd.DataFrame(all_rows)


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("=== DÉMARRAGE SCRAPING 3 SITES ===\n")

    print(">>> Scraping Logic-Immo...")
    df_logic = scrape_site_li_sl(SEARCHES_LOGICIMMO, "logicimmo")
    print("Logic-Immo :", len(df_logic), "annonces\n")

    print(">>> Scraping SeLoger...")
    df_seloger = scrape_site_li_sl(SEARCHES_SELOGER, "seloger")
    print("SeLoger :", len(df_seloger), "annonces\n")

    print(">>> Scraping ORPI (avec pages détail pour CP)...")
    df_orpi = scrape_orpi()
    print("ORPI :", len(df_orpi), "annonces\n")

    dfs = []
    if not df_logic.empty:
        dfs.append(df_logic)
    if not df_seloger.empty:
        dfs.append(df_seloger)
    if not df_orpi.empty:
        dfs.append(df_orpi)

    if not dfs:
        print("Aucune annonce récupérée, fin du script.")
        return

    df_all = pd.concat(dfs, ignore_index=True)

    # Colonnes finales unifiées
    output_cols = [
        "raw_alt", "region", "source", "titre", 
        "prix", "surface_m2", "rooms", 
        "localisation", "code_postal", "ville"
    ]
    
    df_all = df_all[[col for col in output_cols if col in df_all.columns]]

    output_file = "scraping_raw.csv"
    df_all.to_csv(output_file, index=False, encoding="utf-8-sig")

    print("======================================")
    print(f"CSV créé : {output_file}")
    print("Nombre total d'annonces :", len(df_all))
    print("Répartition par source :")
    print(df_all["source"].value_counts())
    print("======================================")


if __name__ == "__main__":
    main()
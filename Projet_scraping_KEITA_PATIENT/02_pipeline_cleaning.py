import pandas as pd
import re
import numpy as np
from pathlib import Path

# ============================================================
# CHEMINS (tous les fichiers dans le dossier data/)
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "scraping_raw.csv"
OUTPUT_FILE = DATA_DIR / "scraping_clean.csv"
COMMUNES_FILE = DATA_DIR / "insee_referentiel.csv"  # code postal + nom commune (+ idéalement code_insee)

# ============================================================
# RÉFÉRENTIEL DE RATTRAPAGE (fallback) POUR CP MANQUANTS
# ============================================================
CP_FALLBACK_MAP = {
    'ALATA': '20167', 'GROSSETO': '20128', 'BASTELICACCIA': '20129',
    'PARIS': '75001', 'MARSEILLE': '13001', 'LYON': '69001', 'TOULOUSE': '31000',
    'NICE': '06000', 'NANTES': '44000', 'STRASBOURG': '67000', 'MONTPELLIER': '34000',
    'BORDEAUX': '33000',
    'LILLE': '59000', 'RENNES': '35000', 'REIMS': '51100', 'TOULON': '83000',
    'ORLÉANS': '45000', 'ORLEANS': '45000', 'ROUEN': '76000', 'AJACCIO': '20000',
    'SAINT': '42000', 'GRENOBLE': '38000', 'DIJON': '21000', 'LE': '76600',
    'ANGERS': '49000', 'NIMES': '30000', 'VILLEURBANNE': '69100',
    'CLERMONT': '63000', 'AIX': '13100', 'BREST': '29200',
    'FENAIN': '59179', 'BEAUVOIS': '59157', 'OISY': '59195'
}

# ============================================================
# ✅ NEUF / ANCIEN : règle simple
# - si "neuf" détecté -> neuf
# - sinon -> ancien
# ============================================================

def _norm_text(s: str) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s).replace("\u00a0", " ").replace("\u202f", " ")
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

NEUF_PATTERNS = [
    r"\bneuf\b",
    r"\bprogramme\b",
    r"\bprogramme neuf\b",
    r"\bvefa\b",
    r"\bfrais de notaire r[ée]duits?\b",
    r"\brt ?2012\b",
    r"\bre ?2020\b",
    r"\bpinel\b",
    r"\bconstruction (neuve|r[ée]cente)\b",
    r"\bjamais habit[ée]e?\b",
    r"\bnormes?\b",
]

RE_NEUF = re.compile("|".join(NEUF_PATTERNS), flags=re.IGNORECASE)

def detect_neuf_ancien_default_ancien(title: str, fallback_text: str | None = None) -> str:
    """Renvoie TOUJOURS 'neuf' ou 'ancien'."""
    text = (_norm_text(title) + " " + _norm_text(fallback_text or "")).strip()
    if RE_NEUF.search(text):
        return "neuf"
    return "ancien"

# ============================================================
# ✅ OPTION A : VILLE AGRÉGÉE (Paris/Lyon/Marseille sans arrond.)
# ============================================================

RE_ARR = re.compile(r"\s+\d{1,2}\s*(?:ER|E|EME|ÈME)?\b.*$", flags=re.IGNORECASE)

def agg_city(name: str) -> str | float:
    """
    Transforme 'PARIS 15E ARRONDISSEMENT' -> 'PARIS'
    'LYON 3E' -> 'LYON'
    'MARSEILLE 8EME' -> 'MARSEILLE'
    Laisse les autres villes inchangées.
    """
    if pd.isna(name) or str(name).strip() == "":
        return np.nan

    s = str(name).upper().strip()

    # supprime code postal éventuel en fin
    s = re.sub(r"\s*\(?\d{5}\)?$", "", s).strip()

    # garde uniquement pour PARIS/LYON/MARSEILLE
    if s.startswith("PARIS") or s.startswith("LYON") or s.startswith("MARSEILLE"):
        s = RE_ARR.sub("", s).strip()

    return s if s else np.nan

# ============================================================
# OUTILS GÉNÉRAUX
# ============================================================

def normalize_spaces(text: str) -> str:
    if pd.isna(text):
        return ""
    return str(text).replace("\u00a0", " ").replace("\u202f", " ")

def clean_city_name(city_name):
    """Normalise une chaîne ville (MAJ, suppression chiffres/parasites)."""
    if not city_name:
        return None
    city_name = str(city_name).upper().strip()
    city_name = re.sub(r'[\d\W_]', ' ', city_name)
    city_name = re.sub(r'\s+', ' ', city_name).strip()
    return city_name if len(city_name) > 1 else None

def normalize_cp(x):
    """Extrait strictement 5 chiffres d'un champ CP (robuste aux floats type 59000.0)."""
    if x is None:
        return None
    s = str(x)
    m = re.search(r"(\d{5})", s)
    return m.group(1) if m else None

def find_code_postal_strict(text):
    """Extrait un CP (5 chiffres) entouré d'espaces (Logic-Immo/SeLoger)."""
    txt = normalize_spaces(text)
    cp_match = re.search(r"\s(\d{5})\s", " " + txt + " ")
    return cp_match.group(1) if cp_match else None

def find_code_postal_loose(text):
    """Extrait le premier CP (5 chiffres) consécutifs (fallback ORPI)."""
    txt = normalize_spaces(text)
    cp_match = re.search(r"(\d{5})", txt)
    return cp_match.group(1) if cp_match else None

def extract_price(text):
    text = normalize_spaces(text)
    matches = re.findall(r"([\d\s\u202f\u00a0]+)\s*€", text)
    if not matches:
        return None
    clean_num = re.sub(r"[^\d]", "", matches[0])
    return float(clean_num) if clean_num else None

def extract_surface(text):
    text = normalize_spaces(text)
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*m", text)
    if not matches:
        return None
    num = matches[0].replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None

def extract_rooms(text):
    text = normalize_spaces(text).lower()
    matches = re.findall(r"(\d+)\s*(?:pièce|pièces|p)\b", text)
    if not matches:
        return None
    try:
        return int(matches[0])
    except ValueError:
        return None

def get_city_from_text_before_cp(raw_alt, cp):
    """Tente d'extraire le mot juste avant le CP dans raw_alt."""
    if not raw_alt or not cp:
        return None
    alt = normalize_spaces(raw_alt)
    match = re.search(f"\\s{cp}\\s", alt)
    idx_cp = (match.start() + 1) if match else alt.find(cp)
    if idx_cp == -1:
        return None
    text_before_cp = alt[:idx_cp].strip()
    tokens = text_before_cp.split()
    if tokens:
        return clean_city_name(tokens[-1])
    return None

def get_first_word_city(city_name):
    """Règle du 'premier mot' (ex: 'AIX EN PROVENCE' -> 'AIX')."""
    if pd.isna(city_name) or city_name is None or city_name == '':
        return None
    tokens = str(city_name).split()
    return tokens[0] if tokens else None

# ============================================================
# RÉFÉRENTIEL COMMUNES (INSEE/La Poste/etc.) -> CP -> Commune
# ============================================================

def _read_csv_robust(path: Path) -> pd.DataFrame:
    """Lit un CSV avec essai encodage + séparateur."""
    if not path.exists():
        raise FileNotFoundError(f"Référentiel introuvable: {path}")

    encodings_to_try = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    seps_to_try = [";", ",", "\t"]

    last_err = None
    for enc in encodings_to_try:
        for sep in seps_to_try:
            try:
                df = pd.read_csv(path, sep=sep, dtype=str, encoding=enc)
                if df.shape[1] <= 1:
                    continue
                return df
            except Exception as e:
                last_err = e
    raise last_err

def load_communes_ref(path: Path) -> pd.DataFrame:
    """
    Charge un référentiel avec au minimum:
      - code_postal
      - nom_commune
    Optionnel:
      - code_insee
      - libelle_acheminement
    Retourne 1 ligne par code_postal.
    """
    ref = _read_csv_robust(path)
    ref.columns = [c.strip() for c in ref.columns]

    rename = {}
    for c in ref.columns:
        cl = c.lower()

        if cl in {"code_postal", "cp", "postal_code"} or "code postal" in cl or "code_postal" in cl:
            rename[c] = "code_postal"
        if "postcode" in cl:
            rename[c] = "code_postal"

        if ("nom" in cl and "commune" in cl) or cl in {"nom_commune", "commune", "libelle_commune"}:
            rename[c] = "nom_commune"
        if "libell" in cl and "commune" in cl:
            rename[c] = "nom_commune"

        if "insee" in cl:
            rename[c] = "code_insee"

        if "libelle" in cl and "acheminement" in cl:
            rename[c] = "libelle_acheminement"

    ref = ref.rename(columns=rename)

    if "code_postal" not in ref.columns or "nom_commune" not in ref.columns:
        raise ValueError(
            "Référentiel invalide: il manque code_postal et/ou nom_commune. "
            f"Colonnes trouvées: {list(ref.columns)}"
        )

    ref["code_postal"] = ref["code_postal"].apply(normalize_cp)
    ref["nom_commune"] = ref["nom_commune"].astype(str).str.strip()

    keep = ["code_postal", "nom_commune"]
    if "code_insee" in ref.columns:
        keep.append("code_insee")
    if "libelle_acheminement" in ref.columns:
        keep.append("libelle_acheminement")

    ref = ref[keep].dropna(subset=["code_postal", "nom_commune"]).copy()

    agg = {"nom_commune": "first"}
    if "code_insee" in ref.columns:
        agg["code_insee"] = "first"
    if "libelle_acheminement" in ref.columns:
        agg["libelle_acheminement"] = "first"

    return ref.groupby("code_postal", as_index=False).agg(agg)

def add_commune_from_cp(df: pd.DataFrame, ref_cp: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute 'commune_from_cp' via jointure CP -> commune,
    et 'ville_finale' = commune_from_cp sinon ville_extracted_cleaned.
    """
    d = df.copy()
    d["code_postal_extracted"] = d["code_postal_extracted"].apply(normalize_cp)

    cols = ["code_postal", "nom_commune"]
    if "code_insee" in ref_cp.columns:
        cols.append("code_insee")
    if "libelle_acheminement" in ref_cp.columns:
        cols.append("libelle_acheminement")

    d = d.merge(
        ref_cp[cols],
        left_on="code_postal_extracted",
        right_on="code_postal",
        how="left"
    )

    d["commune_from_cp"] = d["nom_commune"]
    d["ville_finale"] = d["commune_from_cp"].fillna(d.get("ville_extracted_cleaned", np.nan))

    return d

# ============================================================
# EXTRACTION PAR LIGNE
# ============================================================

def process_row_extraction(row):
    """Extrait les métriques + CP + ville depuis raw_alt/localisation."""
    alt = row.get('raw_alt', '')
    source = row.get('source', '')

    prix_extracted = extract_price(alt)
    surface_m2_extracted = extract_surface(alt)
    rooms_extracted = extract_rooms(alt)

    cp_final = None
    ville_final = None

    if source in ['logicimmo', 'seloger']:
        cp_from_alt = find_code_postal_strict(alt)
        cp_final = cp_from_alt
        ville_final = get_city_from_text_before_cp(alt, cp_from_alt)

    elif source == 'orpi':
        cp_final = find_code_postal_loose(alt)
        ville_brute = row.get('localisation', None)
        if ville_brute and str(ville_brute).strip():
            ville_final = clean_city_name(ville_brute)
        else:
            ville_final = get_city_from_text_before_cp(alt, cp_final)

    return pd.Series({
        'prix_extracted': prix_extracted,
        'surface_m2_extracted': surface_m2_extracted,
        'rooms_extracted': rooms_extracted,
        'code_postal_extracted': cp_final,
        'ville_extracted': ville_final
    })

# ============================================================
# FALLBACK CP À PARTIR DE LA VILLE (si CP manquant)
# ============================================================

def fallback_cp_from_city(df, cp_map):
    print("-> 5/10 : Rattrapage des Codes Postaux manquants (fallback map)...")
    cp_norm = df["code_postal_extracted"].apply(normalize_cp)
    mask_missing = cp_norm.isna()
    recovered = df.loc[mask_missing, "ville_cleaned"].apply(lambda x: cp_map.get(x, None))
    df.loc[recovered.dropna().index, "code_postal_extracted"] = recovered.dropna()
    print(f"-> {recovered.dropna().size} Codes Postaux récupérés via fallback map.")
    return df

# ============================================================
# PIPELINE DE NETTOYAGE
# ============================================================

def clean_raw_data(input_file: Path, output_file: Path, cp_map: dict, communes_file: Path):
    if not input_file.exists():
        print(f"ERREUR : Le fichier d'entrée est introuvable : {input_file}")
        return

    df = pd.read_csv(input_file)
    df.fillna('', inplace=True)

    print(f"Fichier chargé : {len(df)} lignes.")
    print(f"INPUT_FILE   : {input_file}")
    print(f"COMMUNES_FILE: {communes_file}")
    print(f"OUTPUT_FILE  : {output_file}")

    # 1) Extraction initiale
    print("-> 1/10 : Extraction initiale (prix/surface/pièces/CP/ville)...")
    df_extracted = df.apply(process_row_extraction, axis=1)
    df = pd.concat([df.reset_index(drop=True), df_extracted], axis=1)

    # 2) Détection neuf/ancien (défaut ancien)
    print("-> 2/10 : Détection Neuf/Ancien (défaut = ancien si non mentionné)...")
    if "titre" in df.columns:
        df["marche_neuf_ancien"] = df.apply(
            lambda r: detect_neuf_ancien_default_ancien(
                r.get("titre", ""),
                r.get("raw_alt", "") if "raw_alt" in df.columns else None
            ),
            axis=1
        )
    else:
        df["marche_neuf_ancien"] = "ancien"

    print(df["marche_neuf_ancien"].value_counts(dropna=False))

    # 3) Nettoyage Ville (premier mot)
    print("-> 3/10 : Nettoyage de la Ville (règle 'Premier Mot')...")
    df["ville_cleaned"] = df["ville_extracted"].apply(get_first_word_city)

    # 4) Normalisation CP (avant fallback)
    print("-> 4/10 : Normalisation des Codes Postaux...")
    df["code_postal_extracted"] = df["code_postal_extracted"].apply(normalize_cp)

    # 5) Fallback CP
    df = fallback_cp_from_city(df, cp_map)

    # 6) Re-normalisation CP
    df["code_postal_extracted"] = df["code_postal_extracted"].apply(normalize_cp)

    # 7) Calcul du prix/m²
    print("-> 6/10 : Calcul du prix au mètre carré...")
    df["prix_extracted"] = pd.to_numeric(df["prix_extracted"], errors="coerce")
    df["surface_m2_extracted"] = pd.to_numeric(df["surface_m2_extracted"], errors="coerce")

    df["surface_m2_safe"] = np.where(df["surface_m2_extracted"] > 0, df["surface_m2_extracted"], np.nan)
    df["price_m2"] = df["prix_extracted"] / df["surface_m2_safe"]
    df = df.drop(columns=["surface_m2_safe"])

    # 8) Harmonisation colonne ville
    print("-> 7/10 : Harmonisation des noms de colonnes ville...")
    df = df.rename(columns={"ville_cleaned": "ville_extracted_cleaned"})

    # 9) Ajout commune_from_cp + ville_finale
    print("-> 8/10 : Ajout commune_from_cp via référentiel (CP -> commune)...")
    try:
        ref_cp = load_communes_ref(communes_file)
        df = add_commune_from_cp(df, ref_cp)
        print(f"-> CP reconnus : {df['code_postal_extracted'].notna().mean():.1%}")
        print(f"-> commune_from_cp remplie : {df['commune_from_cp'].notna().mean():.1%}")
    except Exception as e:
        print(f"⚠️ Référentiel non appliqué : {e}")
        if "nom_commune" not in df.columns:
            df["nom_commune"] = np.nan
        if "code_insee" not in df.columns:
            df["code_insee"] = np.nan
        df["commune_from_cp"] = np.nan
        df["ville_finale"] = df["ville_extracted_cleaned"]

    # ✅ 9bis) OPTION A : ville_agregee (Paris/Lyon/Marseille sans arrondissements)
    print("-> 9/10 : Création de ville_agregee (Paris/Lyon/Marseille sans arrondissements)...")
    df["ville_agregee"] = df["ville_finale"].apply(agg_city)

    # 10) Drop uniquement si nom_commune ET code_insee manquants
    print("-> 10/10 : Suppression des lignes sans nom_commune ET sans code_insee...")
    before = len(df)

    if "nom_commune" not in df.columns:
        df["nom_commune"] = np.nan
    if "code_insee" not in df.columns:
        df["code_insee"] = np.nan

    df = df.loc[~(df["nom_commune"].isna() & df["code_insee"].isna())].copy()
    after = len(df)
    print(f"-> Lignes supprimées : {before - after}")
    print(f"-> Lignes conservées : {after}")

    # Export final
    final_cols = [
        'region', 'source', 'raw_alt', 'titre', 'localisation', 'url',
        'prix_extracted', 'surface_m2_extracted', 'rooms_extracted',
        'code_postal_extracted',
        'ville_extracted_cleaned',
        'commune_from_cp',
        'ville_finale',
        'ville_agregee',            # ✅ ajoutée
        'marche_neuf_ancien',
        'price_m2',
        # colonnes issues du ref
        'code_postal', 'nom_commune', 'code_insee', 'libelle_acheminement'
    ]

    df_output = df[[c for c in final_cols if c in df.columns]].copy()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_output.to_csv(output_file, index=False, encoding="utf-8-sig")

    print("\n======================================")
    print("NETTOYAGE TERMINÉ (commune_from_cp + ville_finale + ville_agregee + neuf/ancien).")
    print(f"Fichier nettoyé enregistré sous : {output_file}")
    print("======================================")

if __name__ == "__main__":
    clean_raw_data(INPUT_FILE, OUTPUT_FILE, CP_FALLBACK_MAP, COMMUNES_FILE)

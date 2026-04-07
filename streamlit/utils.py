from pathlib import Path
import pandas as pd

def get_paths():
    base = Path(__file__).resolve().parents[1]
    data_dir = base / "data"
    return base, data_dir

def read_csv_safe(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin1"):
        for sep in (",", ";"):
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep)
                if df.shape[1] > 1:
                    return df
            except Exception:
                pass
    return pd.read_csv(path, sep=None, engine="python")

def load_data(prefer_geocoded: bool = True) -> pd.DataFrame:
    _, data_dir = get_paths()
    geo_path = data_dir / "annonces_clean_geocoded.csv"
    clean_path = data_dir / "scraping_clean.csv"

    path = geo_path if (prefer_geocoded and geo_path.exists()) else clean_path
    df = read_csv_safe(path)

    # conversions
    for c in ["prix_extracted", "surface_m2_extracted", "rooms_extracted", "price_m2", "code_postal_extracted", "lat", "lon"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # calc prix/m² si besoin
    if "price_m2" not in df.columns and {"prix_extracted","surface_m2_extracted"}.issubset(df.columns):
        df["price_m2"] = df["prix_extracted"] / df["surface_m2_extracted"]
    elif "price_m2" in df.columns and {"prix_extracted","surface_m2_extracted"}.issubset(df.columns):
        mask = (
            df["price_m2"].isna()
            & df["prix_extracted"].notna()
            & df["surface_m2_extracted"].notna()
            & (df["surface_m2_extracted"] > 0)
        )
        df.loc[mask, "price_m2"] = df.loc[mask, "prix_extracted"] / df.loc[mask, "surface_m2_extracted"]

    return df

import pandas as pd
import numpy as np


def filter_df(df: pd.DataFrame,
              regions=None,
              sources=None,
              price_range=None,
              surface_range=None,
              rooms_range=None,
              city_substring: str | None = None):
    d = df.copy()

    if regions and "region" in d.columns:
        d = d[d["region"].isin(regions)]
    if sources and "source" in d.columns:
        d = d[d["source"].isin(sources)]

    # ✅ ville: on privilégie ville_finale si dispo (plus fiable), sinon ville_extracted_cleaned
    if city_substring:
        s = city_substring.strip().lower()
        city_col = "ville_finale" if "ville_finale" in d.columns else "ville_extracted_cleaned"
        if city_col in d.columns:
            d = d[d[city_col].astype(str).str.lower().str.contains(s, na=False)]

    if price_range and "prix_extracted" in d.columns:
        d = d[(d["prix_extracted"] >= price_range[0]) & (d["prix_extracted"] <= price_range[1])]
    if surface_range and "surface_m2_extracted" in d.columns:
        d = d[(d["surface_m2_extracted"] >= surface_range[0]) & (d["surface_m2_extracted"] <= surface_range[1])]
    if rooms_range and "rooms_extracted" in d.columns:
        d = d[(d["rooms_extracted"] >= rooms_range[0]) & (d["rooms_extracted"] <= rooms_range[1])]

    return d

def kpis(df: pd.DataFrame) -> dict:
    out = {"n": len(df)}
    if "prix_extracted" in df.columns:
        out["prix_med"] = float(df["prix_extracted"].median(skipna=True))
    if "price_m2" in df.columns:
        out["pm2_med"] = float(df["price_m2"].median(skipna=True))
    if "surface_m2_extracted" in df.columns:
        out["surf_med"] = float(df["surface_m2_extracted"].median(skipna=True))
    return out

def price_m2_by_region(df: pd.DataFrame) -> pd.DataFrame:
    if "region" not in df.columns or "price_m2" not in df.columns:
        return pd.DataFrame()
    return (df.groupby("region")
              .agg(n=("price_m2","size"),
                   price_m2_median=("price_m2","median"),
                   price_m2_mean=("price_m2","mean"))
              .sort_values("price_m2_median", ascending=False)
              .reset_index())

def top_cities(df: pd.DataFrame, min_n: int = 10) -> pd.DataFrame:
    # ✅ ville: on privilégie ville_finale si dispo
    city_col = "ville_finale" if "ville_finale" in df.columns else "ville_extracted_cleaned"
    if city_col not in df.columns or "price_m2" not in df.columns or "region" not in df.columns:
        return pd.DataFrame()

    g = (df.groupby(["region", city_col])
           .agg(n=("price_m2","size"),
                price_m2_median=("price_m2","median"),
                price_m2_mean=("price_m2","mean"))
           .reset_index()
           .rename(columns={city_col: "ville"}))

    return g[g["n"] >= min_n].sort_values("price_m2_median", ascending=False)

def corr_price_surface(df: pd.DataFrame) -> float:
    if not {"prix_extracted","surface_m2_extracted"}.issubset(df.columns):
        return float("nan")
    tmp = df[["prix_extracted","surface_m2_extracted"]].dropna()
    if len(tmp) < 3:
        return float("nan")
    return float(tmp["prix_extracted"].corr(tmp["surface_m2_extracted"], method="pearson"))


# ============================================================
# ✅ NEUF / ANCIEN (compat: marche_neuf_ancien en priorité)
# ============================================================

# --- Helpers: détecter la colonne "neuf/ancien" et normaliser ---
CANDIDATE_MARKET_COLS = ["marche_neuf_ancien", "etat", "neuf_ancien", ...]


def _detect_market_col(df: pd.DataFrame) -> str | None:
    """Trouve une colonne probable qui encode neuf/ancien (marche_neuf_ancien prioritaire)."""
    if "marche_neuf_ancien" in df.columns:
        return "marche_neuf_ancien"
    for c in CANDIDATE_MARKET_COLS:
        if c in df.columns:
            return c
    return None

def _norm_market_series(s: pd.Series) -> pd.Series:
    """Normalise les valeurs vers 'neuf' / 'ancien' quand possible."""
    x = s.astype(str).str.lower().str.strip()

    mapping = {
        "neuf": "neuf",
        "nouveau": "neuf",
        "new": "neuf",
        "brand new": "neuf",
        "construction neuve": "neuf",
        "programme neuf": "neuf",
        "vefa": "neuf",
        "ancien": "ancien",
        "old": "ancien",
        "existing": "ancien",
        "second hand": "ancien",
        "a renover": "ancien",
        "à rénover": "ancien",
        "a rénover": "ancien",
    }

    return x.map(lambda v: mapping.get(v, v))

def _market_ready_df(df: pd.DataFrame,
                     region_col: str,
                     city_col: str,
                     price_m2_col: str) -> tuple[pd.DataFrame, str | None]:
    """Retourne df filtré + nom de la colonne marché."""
    market_col = _detect_market_col(df)
    if market_col is None:
        return pd.DataFrame(), None

    d = df.copy()
    d[market_col] = _norm_market_series(d[market_col])

    d = d[d[market_col].isin(["neuf", "ancien"])]

    needed = [price_m2_col]
    if region_col in d.columns: needed.append(region_col)
    if city_col in d.columns: needed.append(city_col)
    d = d.dropna(subset=needed)

    return d, market_col

# --- Comparaison NEUF vs ANCIEN par région ---
def neuf_ancien_by_region(df: pd.DataFrame,
                          region_col: str = "region",
                          city_col: str = "ville_finale",
                          price_m2_col: str = "price_m2",
                          min_n: int = 5) -> pd.DataFrame:
    d, market_col = _market_ready_df(df, region_col, city_col, price_m2_col)
    if d.empty or market_col is None or region_col not in d.columns:
        return pd.DataFrame()

    # pivot médian
    pivot = (
        d.groupby([region_col, market_col])[price_m2_col]
         .median()
         .unstack(market_col)
    )

    # counts
    counts = (
        d.groupby([region_col, market_col]).size()
         .unstack(market_col)
    )

    # ✅ s'assurer que les 2 colonnes existent
    for col in ["neuf", "ancien"]:
        if col not in pivot.columns:
            pivot[col] = np.nan
        if col not in counts.columns:
            counts[col] = 0

    out = pivot.rename(columns={"neuf": "pm2_neuf", "ancien": "pm2_ancien"}).reset_index()
    counts = counts.rename(columns={"neuf": "n_neuf", "ancien": "n_ancien"}).reset_index()
    out = out.merge(counts, on=region_col, how="left")

    # ✅ robustesse
    out = out[(out["n_neuf"] >= min_n) & (out["n_ancien"] >= min_n)]
    if out.empty:
        return pd.DataFrame()

    out["ecart_eur"] = out["pm2_neuf"] - out["pm2_ancien"]
    out["ecart_pct"] = (out["ecart_eur"] / out["pm2_ancien"]) * 100

    return out.sort_values("ecart_eur", ascending=False)


def neuf_ancien_by_city(df: pd.DataFrame,
                        city_col: str = "ville_finale",
                        region_col: str = "region",
                        price_m2_col: str = "price_m2",
                        min_n: int = 5) -> pd.DataFrame:
    d, market_col = _market_ready_df(df, region_col, city_col, price_m2_col)
    if d.empty or market_col is None or city_col not in d.columns:
        return pd.DataFrame()

    pivot = (
        d.groupby([city_col, market_col])[price_m2_col]
         .median()
         .unstack(market_col)
    )

    counts = (
        d.groupby([city_col, market_col]).size()
         .unstack(market_col)
    )

    # ✅ s'assurer que les 2 colonnes existent
    for col in ["neuf", "ancien"]:
        if col not in pivot.columns:
            pivot[col] = np.nan
        if col not in counts.columns:
            counts[col] = 0

    out = pivot.rename(columns={"neuf": "pm2_neuf", "ancien": "pm2_ancien"}).reset_index()
    counts = counts.rename(columns={"neuf": "n_neuf", "ancien": "n_ancien"}).reset_index()
    out = out.merge(counts, on=city_col, how="left")

    out = out[(out["n_neuf"] >= min_n) & (out["n_ancien"] >= min_n)]
    if out.empty:
        return pd.DataFrame()

    out["ecart_eur"] = out["pm2_neuf"] - out["pm2_ancien"]
    out["ecart_pct"] = (out["ecart_eur"] / out["pm2_ancien"]) * 100

    # rattacher région (mode)
    if region_col in d.columns:
        city_region = (
            d.groupby(city_col)[region_col]
             .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
             .reset_index()
        )
        out = out.merge(city_region, on=city_col, how="left")

    return out.sort_values("ecart_eur", ascending=False)

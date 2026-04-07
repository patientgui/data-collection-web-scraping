import streamlit as st

from utils import load_data
from analysis import filter_df

st.set_page_config(page_title="Carte", layout="wide")
st.title("🗺️ Carte des annonces (géolocalisation)")

df = load_data(prefer_geocoded=True)

if not {"lat","lon"}.issubset(df.columns):
    st.warning("Pas de colonnes lat/lon. Exécute la géolocalisation puis exporte `annonces_clean_geocoded.csv` dans /data.")
    st.stop()

pts = df.dropna(subset=["lat","lon"]).copy()
if pts.empty:
    st.warning("Aucun point géocodé dans le fichier.")
    st.stop()

st.sidebar.header("Filtres carte")
regions = sorted(pts["region"].dropna().unique().tolist()) if "region" in pts.columns else []
sel_regions = st.sidebar.multiselect("Régions", regions, default=regions[:3] if len(regions) >= 3 else regions)

sources = sorted(pts["source"].dropna().unique().tolist()) if "source" in pts.columns else []
sel_sources = st.sidebar.multiselect("Sources", sources, default=sources)

pts_f = filter_df(pts, regions=sel_regions if sel_regions else None, sources=sel_sources if sel_sources else None)

st.caption(f"Points affichés (échantillon) : {min(800, len(pts_f))} / {len(pts_f)}")

import folium
from streamlit_folium import st_folium

m = folium.Map(location=[46.5, 2.5], zoom_start=5)
sample = pts_f.sample(n=min(800, len(pts_f)), random_state=42)

for _, r in sample.iterrows():
    popup = f"{r.get('ville_extracted_cleaned','')} — {r.get('prix_extracted','')} € — {round(r.get('price_m2', 0), 0)} €/m²"
    folium.CircleMarker(
        location=[r["lat"], r["lon"]],
        radius=3,
        popup=popup
    ).add_to(m)

st_folium(m, use_container_width=True, height=560)

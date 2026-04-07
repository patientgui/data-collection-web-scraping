import streamlit as st

from utils import load_data
from analysis import filter_df

st.set_page_config(page_title="Données", layout="wide")
st.title("🧾 Données — Table & export")

df = load_data(prefer_geocoded=True)

st.sidebar.header("Filtres export")
regions = sorted(df["region"].dropna().unique().tolist()) if "region" in df.columns else []
sel_regions = st.sidebar.multiselect("Régions", regions, default=[])

sources = sorted(df["source"].dropna().unique().tolist()) if "source" in df.columns else []
sel_sources = st.sidebar.multiselect("Sources", sources, default=[])

df_f = filter_df(df,
                 regions=sel_regions if sel_regions else None,
                 sources=sel_sources if sel_sources else None)

st.write("Lignes :", len(df_f))
st.dataframe(df_f.head(2000), use_container_width=True)

csv = df_f.to_csv(index=False).encode("utf-8")
st.download_button("📥 Télécharger les données filtrées (CSV)", data=csv, file_name="export_filtre.csv", mime="text/csv")

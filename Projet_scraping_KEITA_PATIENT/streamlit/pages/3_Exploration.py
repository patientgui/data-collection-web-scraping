import streamlit as st
import plotly.express as px

from utils import load_data

st.set_page_config(page_title="Exploration", layout="wide")
st.title("🔎 Exploration — Qualité & distributions")

df = load_data(prefer_geocoded=True)

st.subheader("Aperçu des données")
st.write("Dimensions :", df.shape)
st.dataframe(df.head(30), use_container_width=True)

st.divider()

st.subheader("Valeurs manquantes (%)")
na = (df.isna().mean() * 100).sort_values(ascending=False).round(2)
st.dataframe(na.to_frame("% NA"), use_container_width=True)

st.divider()

st.subheader("Distributions")
cols = [c for c in ["prix_extracted","surface_m2_extracted","rooms_extracted","price_m2"] if c in df.columns]
col_choice = st.selectbox("Variable", cols)

fig = px.histogram(df.dropna(subset=[col_choice]), x=col_choice, nbins=50)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Relation prix ↔ surface")

if {"prix_extracted", "surface_m2_extracted"}.issubset(df.columns):
    tmp = df.dropna(subset=["prix_extracted", "surface_m2_extracted"])
    if len(tmp) > 3000:
        tmp = tmp.sample(3000, random_state=42)

    corr = tmp["prix_extracted"].corr(tmp["surface_m2_extracted"])
    st.caption(f"Corrélation de Pearson : {corr:.3f}")

    fig = px.scatter(
        tmp,
        x="surface_m2_extracted",
        y="prix_extracted",
        opacity=0.5,
        labels={
            "surface_m2_extracted": "Surface (m²)",
            "prix_extracted": "Prix (€)"
        }
    )
    st.plotly_chart(fig, use_container_width=True)


st.divider()
st.subheader("Focus — Sélection d’une ville")

if "ville_finale" in df.columns:
    cities = sorted(df["ville_finale"].dropna().unique())
    city = st.selectbox("Choisir une ville", cities)

    sub = df[df["ville_finale"] == city]
    if len(sub) > 0:
        fig = px.histogram(sub, x="price_m2", nbins=30)
        st.plotly_chart(fig, use_container_width=True)

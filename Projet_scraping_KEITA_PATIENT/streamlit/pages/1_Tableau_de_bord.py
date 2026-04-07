import streamlit as st
import plotly.express as px
import pandas as pd


from utils import load_data
from analysis import (
    filter_df, kpis, price_m2_by_region, top_cities, corr_price_surface,
    neuf_ancien_by_region, neuf_ancien_by_city
)

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Dashboard — Vue synthétique")

df = load_data(prefer_geocoded=True)

# Sidebar filtres
st.sidebar.header("Filtres")
regions = sorted(df["region"].dropna().unique().tolist()) if "region" in df.columns else []
sel_regions = st.sidebar.multiselect(
    "Régions",
    regions,
    default=regions[:3] if len(regions) >= 3 else regions
)

sources = sorted(df["source"].dropna().unique().tolist()) if "source" in df.columns else []
sel_sources = st.sidebar.multiselect("Sources", sources, default=sources)

city_q = st.sidebar.text_input("Filtrer par ville (contient)", "")

def slider_num(col, label):
    if col not in df.columns:
        return None
    s = df[col].dropna()
    if s.empty:
        return None
    mn, mx = float(s.min()), float(s.max())
    return st.sidebar.slider(label, mn, mx, (mn, mx))

price_rng = slider_num("prix_extracted", "Prix (€)")
surf_rng  = slider_num("surface_m2_extracted", "Surface (m²)")

rooms_rng = None
if "rooms_extracted" in df.columns:
    s = df["rooms_extracted"].dropna()
    if not s.empty:
        rooms_rng = st.sidebar.slider(
            "Pièces",
            int(s.min()), int(s.max()),
            (int(s.min()), int(s.max()))
        )

df_f = filter_df(
    df,
    regions=sel_regions if sel_regions else None,
    sources=sel_sources if sel_sources else None,
    price_range=price_rng,
    surface_range=surf_rng,
    rooms_range=rooms_rng,
    city_substring=city_q if city_q.strip() else None
)

# KPIs
k = kpis(df_f)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Annonces", f"{k.get('n',0):,}".replace(",", " "))
if "prix_med" in k: c2.metric("Prix médian", f"{k['prix_med']:,.0f} €".replace(",", " "))
if "surf_med" in k: c3.metric("Surface médiane", f"{k['surf_med']:.0f} m²")
if "pm2_med" in k: c4.metric("Prix/m² médian", f"{k['pm2_med']:,.0f} €".replace(",", " "))

st.caption(f"Corrélation prix ↔ surface (Pearson) : {corr_price_surface(df_f):.3f}")

st.divider()

# ---------------------------
# 🏙️ Focus — Sélection d’une ville (sans année)
# ---------------------------
st.subheader("🏙️ Focus — Sélection d’une ville")

city_col = "ville_agregee"
price_m2_col = "price_m2"
surface_col = "surface_m2_extracted"
price_col = "prix_extracted"

selected_city = None  # important

if city_col not in df_f.columns:
    st.info(f"Colonne ville absente : '{city_col}'")
else:
    city_list = (
        df_f[city_col]
        .dropna()
        .astype(str)
        .str.strip()
        .sort_values()
        .unique()
        .tolist()
    )

    if not city_list:
        st.info("Aucune ville disponible avec les filtres actuels.")
    else:
        selected_city = st.selectbox("Choisir une ville (1 seule)", city_list, index=0)
        df_city = df_f[df_f[city_col].astype(str).str.strip() == str(selected_city)].copy()

        if df_city.empty:
            st.info("Pas de données pour cette ville avec les filtres actuels.")
        else:
            # KPIs ville
            a, b, c = st.columns(3)
            a.metric("Annonces (ville)", f"{len(df_city):,}".replace(",", " "))

            if price_m2_col in df_city.columns and df_city[price_m2_col].notna().any():
                b.metric("Prix/m² médian", f"{df_city[price_m2_col].median():,.0f} €".replace(",", " "))

            if surface_col in df_city.columns and df_city[surface_col].notna().any():
                c.metric("Surface médiane", f"{df_city[surface_col].median():.0f} m²")

            # Diagrammes
            col1, col2 = st.columns(2)

            if price_m2_col in df_city.columns and df_city[price_m2_col].notna().any():
                with col1:
                    fig_hist = px.histogram(
                        df_city.dropna(subset=[price_m2_col]),
                        x=price_m2_col,
                        nbins=30,
                        title=f"Distribution du prix au m² — {selected_city}"
                    )
                    fig_hist.update_layout(xaxis_title="€/m²", yaxis_title="Nombre d'annonces")
                    st.plotly_chart(fig_hist, use_container_width=True)

                with col2:
                    fig_box = px.box(
                        df_city.dropna(subset=[price_m2_col]),
                        y=price_m2_col,
                        title=f"Dispersion (boxplot) du prix au m² — {selected_city}"
                    )
                    fig_box.update_layout(yaxis_title="€/m²")
                    st.plotly_chart(fig_box, use_container_width=True)

            # Scatter surface ↔ prix (ou surface ↔ prix/m²)
            if surface_col in df_city.columns and df_city[surface_col].notna().any():
                y_col = price_col if (price_col in df_city.columns and df_city[price_col].notna().any()) else price_m2_col
                y_label = "Prix total (€)" if y_col == price_col else "Prix au m² (€/m²)"

                if y_col in df_city.columns and df_city[y_col].notna().any():
                    df_sc = df_city.dropna(subset=[surface_col, y_col])
                    if len(df_sc) > 2500:
                        df_sc = df_sc.sample(2500, random_state=42)

                    fig_scatter = px.scatter(
                        df_sc,
                        x=surface_col,
                        y=y_col,
                        title=f"Relation surface ↔ {y_label} — {selected_city}",
                        hover_data=[c for c in ["region", "source"] if c in df_sc.columns]
                    )
                    fig_scatter.update_layout(xaxis_title="Surface (m²)", yaxis_title=y_label)
                    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# ---------------------------
# 🏗️ Neuf vs Ancien — par région
# ---------------------------
st.subheader("🏗️ Neuf vs Ancien — par région (prix/m² médian)")

reg_na = neuf_ancien_by_region(df_f, region_col="region", price_m2_col="price_m2")

if reg_na.empty:
    st.info("Comparaison Neuf/Ancien indisponible (colonne neuf/ancien absente ou pas assez de données).")
else:
    st.dataframe(reg_na, use_container_width=True, hide_index=True)

    long_reg = reg_na.melt(
        id_vars=["region", "n_neuf", "n_ancien"],
        value_vars=["pm2_neuf", "pm2_ancien"],
        var_name="marché",
        value_name="prix_m2_median"
    )
    long_reg["marché"] = long_reg["marché"].replace({"pm2_neuf": "Neuf", "pm2_ancien": "Ancien"})

    fig = px.bar(
        long_reg,
        x="region",
        y="prix_m2_median",
        color="marché",
        barmode="group",
        title="Neuf vs Ancien — Prix/m² médian par région"
    )
    fig.update_layout(xaxis_title="", yaxis_title="€/m² (médian)")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------
# 🏘️ Neuf vs Ancien — pour la ville sélectionnée
# ---------------------------
st.subheader("🏘️ Neuf vs Ancien — pour la ville sélectionnée")

if selected_city is None:
    st.info("Sélectionne une ville dans le bloc 'Focus' pour afficher la comparaison Neuf/Ancien.")
else:
    city_na = neuf_ancien_by_city(
        df_f,
        city_col="ville_extracted_cleaned",
        region_col="region",
        price_m2_col="price_m2",
        min_n=5
    )

    if city_na.empty:
        st.info("Pas assez de données Neuf/Ancien par ville (ou colonne absente).")
    else:
        row = city_na[city_na["ville_extracted_cleaned"].astype(str) == str(selected_city)]

        if row.empty:
            st.info("Pas assez de données Neuf/Ancien pour cette ville (seuil min_n non atteint).")
        else:
            r = row.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Neuf (médian €/m²)", f"{r['pm2_neuf']:,.0f} €".replace(",", " "))
            c2.metric("Ancien (médian €/m²)", f"{r['pm2_ancien']:,.0f} €".replace(",", " "))
            c3.metric("Écart (€ / m²)", f"{r['ecart_eur']:,.0f} €".replace(",", " "))
            c4.metric("Écart (%)", f"{r['ecart_pct']:.1f}%")

            df_plot = pd.DataFrame({
                "marché": ["Neuf", "Ancien"],
                "prix_m2_median": [r["pm2_neuf"], r["pm2_ancien"]],
                "effectif": [r["n_neuf"], r["n_ancien"]],
            })
            fig = px.bar(
                df_plot,
                x="marché",
                y="prix_m2_median",
                text="effectif",
                title=f"Neuf vs Ancien — {selected_city} (texte = effectifs)"
            )
            fig.update_layout(xaxis_title="", yaxis_title="€/m² (médian)")
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------
# Prix/m² par région (ton bloc existant)
# ---------------------------
st.subheader("Prix/m² par région")
reg = price_m2_by_region(df_f)
if reg.empty:
    st.info("Pas assez de données ou colonnes manquantes.")
else:
    fig = px.bar(
        reg,
        x="price_m2_median",
        y="region",
        orientation="h",
        hover_data=["n", "price_m2_mean"]
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Scatter prix vs surface + hist prix/m²
left, right = st.columns(2)

with left:
    st.subheader("Distribution prix/m²")
    if "price_m2" in df_f.columns:
        fig = px.histogram(df_f.dropna(subset=["price_m2"]), x="price_m2", nbins=40)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Colonne price_m2 absente.")

with right:
    st.subheader("Prix vs Surface")
    if {"prix_extracted", "surface_m2_extracted"}.issubset(df_f.columns):
        sample = df_f.dropna(subset=["prix_extracted", "surface_m2_extracted"])
        if len(sample) > 3000:
            sample = sample.sample(3000, random_state=42)
        fig = px.scatter(
            sample,
            x="surface_m2_extracted",
            y="prix_extracted",
            hover_data=[c for c in ["region", "ville_extracted_cleaned", "source"] if c in sample.columns]
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Colonnes prix/surface absentes.")

st.divider()

st.subheader("Top villes (prix/m² médian)")
cities = top_cities(df_f, min_n=10)
if cities.empty:
    st.info("Pas assez de données par ville, ou colonne ville manquante.")
else:
    st.dataframe(cities.head(30), use_container_width=True)




st.divider()
st.subheader("🔥 Heatmap — Indicateurs par région")

required = {"region", "price_m2"}
if not required.issubset(df_f.columns):
    st.info("Colonnes manquantes pour la heatmap (region, price_m2).")
else:
    # Agrégation régionale
    agg = df_f.groupby("region").agg(
        n=("price_m2", "size"),
        pm2_median=("price_m2", "median"),
        pm2_mean=("price_m2", "mean"),
    )

    if "prix_extracted" in df_f.columns:
        agg["prix_median"] = df_f.groupby("region")["prix_extracted"].median()
    if "surface_m2_extracted" in df_f.columns:
        agg["surf_median"] = df_f.groupby("region")["surface_m2_extracted"].median()

    agg = agg.reset_index()

    # Choix des métriques à afficher (tu peux en enlever/ajouter)
    metric_cols = [c for c in ["pm2_median", "pm2_mean", "prix_median", "surf_median"] if c in agg.columns]

    # Format long -> heatmap
    heat_long = agg.melt(
        id_vars=["region", "n"],
        value_vars=metric_cols,
        var_name="métrique",
        value_name="valeur"
    )

    # Renommages jolis
    pretty = {
        "pm2_median": "Prix/m² (médian)",
        "pm2_mean": "Prix/m² (moyen)",
        "prix_median": "Prix (médian)",
        "surf_median": "Surface (médiane)",
    }
    heat_long["métrique"] = heat_long["métrique"].map(lambda x: pretty.get(x, x))

    # Option : trier les régions par prix/m² médian décroissant si dispo
    if "pm2_median" in agg.columns:
        order_regions = agg.sort_values("pm2_median", ascending=False)["region"].tolist()
    else:
        order_regions = sorted(agg["region"].unique().tolist())

    heat_long["region"] = pd.Categorical(heat_long["region"], categories=order_regions, ordered=True)

    # Pivot pour Plotly heatmap (matrix)
    heat = heat_long.pivot_table(index="region", columns="métrique", values="valeur", aggfunc="first")

    fig = px.imshow(
        heat,
        aspect="auto",
        labels=dict(x="Indicateur", y="Région", color="Valeur"),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption("Couleur = valeur de l'indicateur. Les régions sont triées par prix/m² médian (si disponible).")

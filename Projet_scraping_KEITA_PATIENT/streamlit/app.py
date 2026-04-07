import streamlit as st

st.title("🏠 Analyse du marché immobilier français — Web Scraping & Data Analysis")
st.markdown(
    "*Application interactive de collecte, nettoyage et analyse d’annonces immobilières issues du web.*"
)

st.divider()

st.subheader("🎯 Objectifs du projet")
st.markdown("""
Cette application a été développée dans le cadre d’un **projet Python avancé**.
Elle vise à :
- collecter automatiquement des annonces immobilières via **web scraping**,
- nettoyer et enrichir les données (prix, surface, localisation, type de bien),
- analyser les **disparités du marché immobilier en France**,
- proposer une **exploration interactive** via Streamlit.
""")

st.subheader("🧩 Fonctionnalités principales")
st.markdown("""
- Statistiques descriptives : prix, surface, pièces, prix au m²  
- Comparaisons géographiques : régions et villes  
- Analyse **Neuf vs Ancien** (lorsque détectable)  
- Visualisations interactives (graphiques, tableaux, cartes)  
- Filtres dynamiques pour affiner l’analyse
""")

st.subheader("🧭 Navigation")
st.markdown("""
Utilise le **menu latéral** pour accéder aux différentes sections :
- **Dashboard** : vue synthétique du marché  
- **Carte** : visualisation géographique des annonces  
- **Exploration** : analyse détaillée des distributions  
- **Données** : aperçu du jeu de données nettoyé
""")

st.subheader("ℹ️ Informations techniques")
st.markdown("""
- Données collectées par **web scraping multi-sources**  
- Traitement réalisé en **Python (Pandas, Regex, Feature Engineering)**  
- Application développée avec **Streamlit**
""")

st.info(
    "💡 Astuce : si le fichier `annonces_clean_geocoded.csv` est présent dans le dossier `/data`, "
    "la page Carte s’active automatiquement."
)
st.divider()

st.markdown(
    """
    <div style="text-align: center; color: #6b7280; font-size: 0.9em;">
        Projet réalisé par <b>Constance KEITA</b> et <b>Guillaume PATIENT</b><br>
        Formation : Sorbonne Data Analytics 2025–2026
    </div>
    """,
    unsafe_allow_html=True
)

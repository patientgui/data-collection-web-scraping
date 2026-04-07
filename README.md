📁 Structure du projet
.
├── data/
│   ├── scraping_raw.csv              # Données brutes issues du scraping
│   ├── scraping_clean.csv            # Données nettoyées
│   ├── annonces_clean_geocoded.csv   # Données nettoyées + géocodées
│   ├── geocode_cache.csv             # Cache Nominatim (limite API)
│   └── insee_referentiel.csv          # Référentiel communes / codes postaux
│
├── streamlit/
│   ├── app.py                         # Page d’accueil
│   ├── analysis.py                   # Fonctions analytiques (KPIs, agrégations)
│   ├── utils.py                      # Fonctions utilitaires
│   └── pages/
│       ├── 1_Tableau_de_bord.py       # Dashboard principal
│       ├── 2_Carte.py                # Carte interactive (géocodage)
│       ├── 3_Exploration.py          # Analyse exploratoire
│       └── 4_Données.py              # Table des données
│
├── exploration.ipynb                  # Notebook d’analyse exploratoire
├── 01_scraping.py                        # Script de scraping
├── 02_pipeline_cleaning.py               # Pipeline nettoyage & enrichissement
├── requirements.txt                  # Dépendances Python
└── README.md

⚙️ Environnement Python (conda)

Le projet a été développé avec conda dans un environnement nommé immo.

1️⃣ Création de l’environnement
conda create -n immo python=3.11 -y
conda activate immo

2️⃣ Installation des dépendances
pip install -r requirements.txt

📦 requirements.txt


💡 Remarques

geopy + Nominatim sont utilisés pour la géolocalisation

streamlit-folium permet l’affichage de cartes interactives

scikit-learn est utilisé pour certaines analyses statistiques

▶️ Lancer l’application Streamlit

Depuis la racine du projet :

conda activate immo
streamlit run streamlit/app.py


L’application sera accessible à l’adresse :

http://localhost:8501

🗺️ Géocodage & API Nominatim

Le géocodage repose sur Nominatim (OpenStreetMap) via geopy

Un cache local (geocode_cache.csv) est utilisé pour :

limiter les appels API

respecter les conditions d’utilisation

accélérer les traitements

📊 Fonctionnalités principales

Analyse descriptive des annonces (prix, surface, pièces, €/m²)

Comparaisons régionales et par ville

Comparaison neuf / ancien

Carte interactive des annonces géocodées

Exploration libre via filtres dynamiques

🚧 Limites connues

Données issues du scraping → biais de représentativité possibles

Géocodage incomplet pour certaines annonces

Absence de dimension temporelle (instantané du marché)

🔮 Pistes d’amélioration

Intégration de données temporelles

Modèles prédictifs de prix

Croisement avec données socio-économiques (INSEE)

Déploiement cloud (Streamlit Cloud / Docker)

👤 Auteurs

Projet réalisé par :

Constance KEITA / Guillaume PATIENT

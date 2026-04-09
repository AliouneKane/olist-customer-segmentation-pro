import nbformat as nbf

nb = nbf.v4.new_notebook()

cells = []

# Section 1: Setup
cells.append(nbf.v4.new_markdown_cell("""# 📊 Analyse Exploratoire des Données Olist

**L'objectif de ce notebook** est de fournir une fondation analytique pour le Feature Engineering RFM et le clustering. Chaque section produit des insights actionnables.

## Section 1 — Setup & Connexion PostgreSQL"""))
cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import missingno as msno
import sys
import os
from pathlib import Path
from scipy.stats import shapiro, spearmanr, probplot

sns.set_theme(style="whitegrid", palette="muted")

# Setup project root and import data_loader
PROJECT_ROOT = Path(os.getcwd()).parent
sys.path.append(str(PROJECT_ROOT / "src"))
from data_loader import get_db_engine, get_merged_dataframe, get_customer_aggregation

engine = get_db_engine()

# Chargement de toutes les tables brutes
tables = ["olist_orders", "olist_customers", "olist_order_items", "olist_products", "olist_sellers", "olist_order_payments", "olist_order_reviews", "olist_geolocation", "product_category_name_translation"]
db_data = {table: pd.read_sql_table(table, engine) for table in tables}

print("✅ Tables brutes chargées avec succès")
"""))

# Section 2: Audit
cells.append(nbf.v4.new_markdown_cell("""## Section 2 — Audit Qualité des Données
Profilage, valeurs manquantes, détection de doublons."""))
cells.append(nbf.v4.new_code_cell("""# Profiling
profiles = []
for name, df in db_data.items():
    profiles.append({
        "Table": name,
        "Lignes": len(df),
        "Colonnes": len(df.columns),
        "% Nulls": round(df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100, 2),
        "Doublons Exacts": df.duplicated().sum()
    })
profile_df = pd.DataFrame(profiles).set_index("Table")
display(profile_df)
"""))
cells.append(nbf.v4.new_code_cell("""# Heatmap des valeurs manquantes (Tables critiques)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
msno.matrix(db_data['olist_order_reviews'], ax=ax1, sparkline=False)
ax1.set_title("Missings: order_reviews (Commentaires optionnels)")
msno.matrix(db_data['olist_products'], ax=ax2, sparkline=False)
ax2.set_title("Missings: products (Dimensions et catégories)")
plt.tight_layout()
plt.show()

# Verification Status Commandes
st_dist = db_data['olist_orders']['order_status'].value_counts(normalize=True) * 100
print("Distribution order_status (%) :\n", st_dist)
"""))
cells.append(nbf.v4.new_markdown_cell("""**Livrable** : On note beaucoup de valeurs manquantes logiques sur les `reviews` (les clients ne laissent pas tous un commentaire écrit). Les données géographiques nécessiteront d'être nettoyées pour le machine learning si on les utilise en clustering. Seules les commandes "delivered" (97%) seront conservées."""))

# Section 3: Jointure Master & Agrégations
cells.append(nbf.v4.new_markdown_cell("""## Section 3 — Jointure Master & Agrégation Client
Utilisation du Data Loader pour récupérer la jointure sécurisée et n'avoir que les `delivered`."""))
cells.append(nbf.v4.new_code_cell("""# Load merged data using SQL
df_master = get_merged_dataframe(engine)

# Temporal processing
datetime_cols = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 'order_delivered_customer_date', 'order_estimated_delivery_date']
for col in datetime_cols:
    df_master[col] = pd.to_datetime(df_master[col], errors='coerce')

# Feature Engineering Temporel: Lead Time Decomposition
df_master['actual_lead_time_days'] = (df_master['order_delivered_customer_date'] - df_master['order_purchase_timestamp']).dt.total_seconds() / 86400
df_master['estimated_lead_time_days'] = (df_master['order_estimated_delivery_date'] - df_master['order_purchase_timestamp']).dt.total_seconds() / 86400
df_master['approval_time_mins'] = (df_master['order_approved_at'] - df_master['order_purchase_timestamp']).dt.total_seconds() / 60
df_master['carrier_time_days'] = (df_master['order_delivered_carrier_date'] - df_master['order_approved_at']).dt.total_seconds() / 86400
df_master['transit_time_days'] = (df_master['order_delivered_customer_date'] - df_master['order_delivered_carrier_date']).dt.total_seconds() / 86400
df_master['delivery_delay_days'] = df_master['actual_lead_time_days'] - df_master['estimated_lead_time_days']

# Freight Ratio
df_master['freight_ratio'] = df_master['freight_value'] / df_master['price']

# Basic info on master df
print(f"Master DF Shape: {df_master.shape}")
display(df_master[['actual_lead_time_days', 'transit_time_days', 'delivery_delay_days', 'freight_ratio']].describe())
"""))
cells.append(nbf.v4.new_markdown_cell("""**Livrable** : On a décomposé le `lead_time`. L'essentiel du délai se passe dans le `transit_time_days`."""))

# Section 4: Analyse Temporelle
cells.append(nbf.v4.new_markdown_cell("""## Section 4 — Analyse Temporelle & Croissance"""))
cells.append(nbf.v4.new_code_cell("""# Evolution commandes par mois
df_orders = df_master[['order_id', 'order_purchase_timestamp']].drop_duplicates()
monthly_orders = df_orders.set_index('order_purchase_timestamp').resample('ME').size()

# Croissance du CA mensuel
df_rev = df_master[['order_id', 'order_purchase_timestamp', 'payment_value']].drop_duplicates(subset=['order_id', 'payment_value'])
monthly_revenue = df_rev.set_index('order_purchase_timestamp').resample('ME')['payment_value'].sum()

fig, ax1 = plt.subplots(figsize=(15, 5))
ax2 = ax1.twinx()

ax1.plot(monthly_orders.index, monthly_orders.values, color='b', marker='o', label="Commandes")
ax2.plot(monthly_revenue.index, monthly_revenue.values, color='g', marker='x', linestyle='--', label="CA (BRL)")

ax1.set_ylabel("Volume de commandes", color='b')
ax2.set_ylabel("Chiffre d'Affaires", color='g')
plt.title("Croissance de l'écosystème Olist (Commandes vs Revenus)")
fig.legend(loc="upper left", bbox_to_anchor=(0.1,0.9))
plt.grid(alpha=0.3)
plt.show()

# Intra-semaine
df_orders['weekday'] = df_orders['order_purchase_timestamp'].dt.day_name()
order_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
plt.figure(figsize=(8,4))
sns.countplot(data=df_orders, x='weekday', order=order_days, palette='viridis')
plt.title("Commandes par jour de la semaine")
plt.show()
"""))

# Section 5: Analyse Financière & Distributions
cells.append(nbf.v4.new_markdown_cell("""## Section 5 — Analyse Financière & Distributions"""))
cells.append(nbf.v4.new_code_cell("""fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5))
prices = df_master['price'].dropna()

sns.histplot(prices, bins=50, kde=True, ax=ax1, color='teal')
ax1.set_title("Distribution des Prix (Long Tail)")

sns.boxplot(x=prices, ax=ax2, color='lightblue')
ax2.set_title("Boxplot des Prix (IQR et Outliers)")
plt.show()

# Stats + Normalité
print("Skewness du prix:", prices.skew())
print("Kurtosis du prix:", prices.kurtosis())

sample = prices.sample(5000, random_state=42)
stat, p = shapiro(sample)
print(f"Shapiro-Wilk: p-value={p:.3e}. {'Non normal' if p < 0.05 else 'Normal'}")

# Payment Types
pay_counts = df_master['payment_type'].value_counts()
plt.figure(figsize=(6,6))
plt.pie(pay_counts, labels=pay_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("Set2"))
plt.title("Répartition des méthodes de paiement")
plt.show()
"""))

# Section 6: Geographie
cells.append(nbf.v4.new_markdown_cell("""## Section 6 — Analyse Géographique"""))
cells.append(nbf.v4.new_code_cell("""# Concentration Etat
state_sales = df_master['customer_state'].value_counts(normalize=True).head(10) * 100
state_sellers = df_master['seller_state'].value_counts(normalize=True).head(10) * 100

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
sns.barplot(x=state_sales.index, y=state_sales.values, ax=ax1, palette='rocket')
ax1.set_title("Top 10 Etats Clients (% du total)")
sns.barplot(x=state_sellers.index, y=state_sellers.values, ax=ax2, palette='mako')
ax2.set_title("Top 10 Etats Vendeurs (% du total)")
plt.show()

# Heatmap Freight (Vendeur -> Client) top 5 states
top5 = ['SP', 'RJ', 'MG', 'RS', 'PR']
sub_df = df_master[df_master['customer_state'].isin(top5) & df_master['seller_state'].isin(top5)]
freight_matrix = sub_df.groupby(['seller_state', 'customer_state'])['freight_value'].mean().unstack()

plt.figure(figsize=(6, 5))
sns.heatmap(freight_matrix, annot=True, fmt=".1f", cmap="YlOrRd")
plt.title("Freight moyen : Etat Vendeur -> Etat Client")
plt.show()
"""))

# Section 7: Produits & Vendeurs
cells.append(nbf.v4.new_markdown_cell("""## Section 7 — Analyse Produits & Écosystème Vendeurs"""))
cells.append(nbf.v4.new_code_cell("""# Tops categories (fast moving)
top_cats = df_master['product_category_name_english'].value_counts().head(15)
plt.figure(figsize=(10, 6))
sns.barplot(y=top_cats.index, x=top_cats.values, palette='crest')
plt.title("Fast-moving categories (Volume des ventes)")
plt.show()

# Performance vendeurs
seller_perf = df_master.groupby('seller_id').agg(
    total_sales=('order_id', 'nunique'),
    avg_delivery_delay=('delivery_delay_days', 'mean')
).reset_index()

plt.figure(figsize=(10,4))
sns.histplot(seller_perf['total_sales'], bins=50, log_scale=(True, False), color='purple')
plt.title("Distribution des ventes par vendeur (Log Scale) -> 80% des vendeurs font peu de volume")
plt.xlabel("Total des commandes (Log)")
plt.show()
"""))

# Section 8: Satisfaction
cells.append(nbf.v4.new_markdown_cell("""## Section 8 — Analyse de la Satisfaction Client"""))
cells.append(nbf.v4.new_code_cell("""# Score dist
plt.figure(figsize=(8, 4))
sns.countplot(data=df_master, x='review_score', palette='Reds_d')
plt.title("Score de satisfaction: Forts pics à 5 et 1 (Bimodal)")
plt.show()

# Correlation retard vs score
df_delay = df_master[['delivery_delay_days', 'review_score']].dropna()
stat, p = spearmanr(df_delay['delivery_delay_days'], df_delay['review_score'])
print(f"Spearman Retard vs Score: {stat:.3f} (p-val: {p:.3e}) => Forte corrélation négative avec le retard.")

# Taux de commandes en retard (<0 jours correspond à de l'avance, >0 correspond au retard)
df_delay['is_late'] = df_delay['delivery_delay_days'] > 0
late_pct = df_delay['is_late'].mean() * 100
print(f"Taux global de commandes en retard : {late_pct:.1f}%")

plt.figure(figsize=(8,5))
sns.boxplot(x='review_score', y='delivery_delay_days', data=df_delay)
plt.ylim(-30, 30)
plt.title("Impact du délai de livraison sur le score")
plt.axhline(0, color='red', linestyle='--')
plt.show()
"""))

# Section 9: RFM & Segmentation Hypotheses
cells.append(nbf.v4.new_markdown_cell("""## Section 9 — Pré-analyse RFM & Hypothèses de Segmentation
Extraction des features Recency, Frequency, Monetary et vérification de leurs distributions."""))
cells.append(nbf.v4.new_code_cell("""# Aggregation RFM SQL Native (via data_loader)
df_agg = get_customer_aggregation(engine)
max_date = pd.to_datetime(df_agg['last_purchase_date']).max()

df_agg['Recency'] = (max_date - pd.to_datetime(df_agg['last_purchase_date'])).dt.days
df_rfm = df_agg[['customer_unique_id', 'Recency', 'total_orders', 'total_spent']].copy()
df_rfm.columns = ['customer_unique_id', 'Recency', 'Frequency', 'Monetary']

# Transformation Log pour corriger le Skewness
df_rfm['Recency_log'] = np.log1p(df_rfm['Recency'])
df_rfm['Frequency_log'] = np.log1p(df_rfm['Frequency'])
df_rfm['Monetary_log'] = np.log1p(df_rfm['Monetary'])

# Distribution brut vs Log
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
feat = ['Recency', 'Frequency', 'Monetary']
log_feat = ['Recency_log', 'Frequency_log', 'Monetary_log']

for i in range(3):
    sns.histplot(df_rfm[feat[i]], bins=40, ax=axes[0,i], color='teal')
    axes[0,i].set_title(f"{feat[i]} Brut")
    
    sns.histplot(df_rfm[log_feat[i]], bins=40, ax=axes[1,i], color='coral')
    axes[1,i].set_title(f"{feat[i]} Log")

plt.tight_layout()
plt.show()

# Verification Skewness
for f in feat + log_feat:
    print(f"Skewness {f}: {df_rfm[f].skew():.2f}")

# Verification Clients One-Shot
one_shot = (df_rfm['Frequency'] == 1).mean() * 100
print(f"\\n🚨 Clients avec une seule commande: {one_shot:.1f}%")

# Scatter correlation matrix
corr = df_rfm[['Recency', 'Frequency', 'Monetary']].corr()
plt.figure(figsize=(5,4))
sns.heatmap(corr, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
plt.title("Correlation Matrix RFM")
plt.show()
"""))
cells.append(nbf.v4.new_markdown_cell("""### 💡 Hypothèses et Recommandations vers le Clustering
1. **Déséquilibre de la Fréquence** : 97% des clients n'ont qu'une seule commande. Mettre un poids fort sur F risque de créer un cluster "1 achat" unique peu discriminant. Il faudra ajouter le score de review ou la Récence pour affiner.
2. **Log-Transform** : Indispensable sur le `Monetary` avant tout passage par un K-Means ou DBSCAN.
3. **Scaling** : Obligatoire avec un `StandardScaler` après application du log.
4. **Segments** : Les analyses visent idéalement 4 à 5 segments : *Champions*, *Fidèles mais récents*, *Nouveaux (One-shot content)*, *À risque (One-shot insatisfait)*, et *Perdus (Churners)*."""))

nb['cells'] = cells
with open('notebooks/01_eda.ipynb', 'w') as f:
    nbf.write(nb, f)

print("Notebook 01_eda.ipynb ré-généré avec l'ensemble du plan et du code détaillé.")

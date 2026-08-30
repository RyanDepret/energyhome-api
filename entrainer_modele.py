import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# ── CHARGEMENT DES DONNÉES ────────────────────────────────────────────────────
df1 = pd.read_csv('dpe_dataset.csv')
df2 = pd.read_csv('dpe_dataset_fg.csv')
df = pd.concat([df1, df2], ignore_index=True)
df = df.drop_duplicates()

# Conversion de la surface en numérique (au cas où il y aurait des valeurs textuelles)
df['surface_habitable_logement'] = pd.to_numeric(df['surface_habitable_logement'], errors='coerce')
df = df.dropna()  # on supprime les lignes avec des valeurs manquantes après conversion

print(f"Dataset final : {len(df)} lignes")

# ── ENCODAGE DES VARIABLES CATÉGORIELLES (One-Hot Encoding) ───────────────────
colonnes_categorielles = ['periode_construction', 'type_batiment', 'type_energie_principale_chauffage', 'zone_climatique']
df_encode = pd.get_dummies(df, columns=colonnes_categorielles)

# ── SÉPARATION FEATURES (X) / CIBLE (y) ────────────────────────────────────────
X = df_encode.drop(columns=['etiquette_dpe', 'code_postal_ban'])
y = df_encode['etiquette_dpe']

# On garde la liste des colonnes finales — indispensable pour que /predict
# sache reconstruire exactement les mêmes colonnes plus tard
colonnes_modele = list(X.columns)
print(f"Nombre de colonnes après encodage : {len(colonnes_modele)}")

# ── SPLIT TRAIN / TEST ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── RECHERCHE DES MEILLEURS HYPERPARAMÈTRES (GridSearchCV) ─────────────────────
grille_parametres = {
    'n_estimators': [200, 300, 400],
    'max_depth': [8, 10, 12],
    'min_samples_leaf': [4, 5, 6, 8]
}

modele_base = RandomForestClassifier(class_weight='balanced', random_state=42)

recherche = GridSearchCV(
    modele_base,
    grille_parametres,
    cv=3,                # validation croisée en 3 parties
    scoring='f1_macro',  # optimise le f1-score moyen sur toutes les classes, pas juste l'accuracy
    n_jobs=-1            # utilise tous les cœurs du processeur pour aller plus vite
)

print("\nRecherche des meilleurs hyperparamètres en cours (peut prendre plusieurs minutes)...")
recherche.fit(X_train, y_train)

print(f"\nMeilleurs paramètres trouvés : {recherche.best_params_}")
modele = recherche.best_estimator_

# ── ÉVALUATION ──────────────────────────────────────────────────────────────
y_pred = modele.predict(X_test)

print("\n=== Rapport de classification (précision, rappel, f1-score par classe) ===")
print(classification_report(y_test, y_pred))

print("\n=== Feature importance (top 10) ===")
importances = pd.Series(modele.feature_importances_, index=colonnes_modele)
print(importances.sort_values(ascending=False).head(10))

print("\n=== Matrice de confusion ===")
labels = sorted(y.unique())
matrice = confusion_matrix(y_test, y_pred, labels=labels)

print("Prédit ->  " + "  ".join(labels))
for vraie_classe, ligne in zip(labels, matrice):
    print(f"Vrai {vraie_classe}   : " + "  ".join(f"{v:3d}" for v in ligne))

# ── EXPORT DU MODÈLE ─────────────────────────────────────────────────────────
joblib.dump(modele, 'modele_dpe_v2.pkl')
joblib.dump(colonnes_modele, 'colonnes_modele_v2.pkl')  # on sauvegarde aussi la structure des colonnes

print("\nModèle exporté : modele_dpe_v2.pkl")
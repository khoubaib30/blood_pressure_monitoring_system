# ==============================
# IMPORT DES LIBRAIRIES
# ==============================

# Manipulation des données (tableaux, CSV…)
import pandas as pd

# Calculs numériques (math, matrices…)
import numpy as np

# Modèle de Machine Learning utilisé (Random Forest)
from sklearn.ensemble import RandomForestRegressor

# Pour séparer les données en train / test
from sklearn.model_selection import train_test_split

# Métriques pour évaluer le modèle
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Visualisation
import matplotlib.pyplot as plt
import seaborn as sns

# Sauvegarde du modèle
import joblib

# Gestion des fichiers
import os
import sys


# ==============================
# CONFIGURATION DES GRAPHIQUES
# ==============================

# On essaie d’appliquer un style visuel (sinon fallback)
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except:
    try:
        plt.style.use('seaborn-darkgrid')
    except:
        plt.style.use('ggplot')

# Palette de couleurs
sns.set_palette("husl")


# ==============================
# 1. CHARGEMENT DES DONNÉES
# ==============================

def load_data():
    """
    Charge les données depuis un fichier CSV
    """
    data_path = "data/ml_training_data.csv"

    # Vérifie si le fichier existe
    if not os.path.exists(data_path):
        print(f"ERREUR: Fichier {data_path} introuvable!", file=sys.stderr)
        sys.exit(1)

    # Lecture du CSV
    return pd.read_csv(data_path)


# ==============================
# 2. PRÉPARATION DES DONNÉES
# ==============================

def prepare_data(df):
    """
    Sépare les features (X) et les targets (y)
    """

    # On sélectionne toutes les colonnes qui commencent par 'obs_'
    # → ce sont les variables d'entrée (features)
    feature_cols = [col for col in df.columns if col.startswith('obs_')]

    # X = variables explicatives
    X = df[feature_cols].values

    # y = variables à prédire (risque à 1h, 6h, 24h)
    y = df[['critical_risk_1h', 'critical_risk_6h', 'critical_risk_24h']].values

    return X, y


# ==============================
# 3. ENTRAÎNEMENT DU MODÈLE
# ==============================

def train_model(X_train, y_train):
    """
    Entraîne le modèle Random Forest
    """

    # Création du modèle avec des paramètres choisis
    model = RandomForestRegressor(
        n_estimators=100,       # nombre d’arbres
        max_depth=20,           # profondeur maximale
        min_samples_split=5,    # minimum pour split
        min_samples_leaf=2,     # minimum dans une feuille
        random_state=42,        # reproductibilité
        n_jobs=-1               # utilise tous les CPU
    )

    # Entraînement du modèle
    model.fit(X_train, y_train)

    return model


# ==============================
# 4. ÉVALUATION DU MODÈLE
# ==============================

def evaluate_model(model, X_test, y_test):
    """
    Évalue les performances du modèle
    """

    # Prédictions du modèle
    y_pred = model.predict(X_test)

    # On "aplatit" les matrices pour calcul global
    y_test_flat = y_test.flatten()
    y_pred_flat = y_pred.flatten()

    # Calcul des métriques globales
    overall_mae = mean_absolute_error(y_test_flat, y_pred_flat)
    overall_rmse = np.sqrt(mean_squared_error(y_test_flat, y_pred_flat))
    overall_r2 = r2_score(y_test_flat, y_pred_flat)

    # Dictionnaire pour stocker les résultats par horizon
    metrics = {}

    # On calcule les métriques pour chaque horizon (1h, 6h, 24h)
    for i, target_name in enumerate(['critical_risk_1h', 'critical_risk_6h', 'critical_risk_24h']):
        
        y_true = y_test[:, i]
        y_pred_target = y_pred[:, i]

        mae = mean_absolute_error(y_true, y_pred_target)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred_target))
        r2 = r2_score(y_true, y_pred_target)

        metrics[target_name] = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2
        }

    return metrics, y_pred


# ==============================
# 5. VISUALISATION DES RÉSULTATS
# ==============================

def plot_predictions(y_test, y_pred, output_dir="models"):
    """
    Génère des graphiques pour comparer prédictions vs réalité
    """

    # Création du dossier si nécessaire
    os.makedirs(output_dir, exist_ok=True)

    target_names = ['critical_risk_1h', 'critical_risk_6h', 'critical_risk_24h']
    target_labels = ['Risque 1h', 'Risque 6h', 'Risque 24h']

    # ==========================
    # SCATTER PLOTS (réel vs prédiction)
    # ==========================

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('Prédictions vs Valeurs Réelles - Random Forest')

    for idx, (target_name, target_label) in enumerate(zip(target_names, target_labels)):

        y_true = y_test[:, idx]
        y_pred_target = y_pred[:, idx]

        ax = axes[idx]

        # Nuage de points
        ax.scatter(y_true, y_pred_target, alpha=0.5)

        # Ligne parfaite (idéal)
        ax.plot([y_true.min(), y_true.max()],
                [y_true.min(), y_true.max()],
                'r--')

        ax.set_xlabel('Valeur Réelle')
        ax.set_ylabel('Valeur Prédite')
        ax.set_title(target_label)

        # Affichage du score R²
        r2 = r2_score(y_true, y_pred_target)
        ax.text(0.05, 0.95, f'R² = {r2:.3f}', transform=ax.transAxes)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'random_forest_predictions_scatter.png'))
    plt.close()


# ==============================
# 6. PIPELINE PRINCIPAL
# ==============================

def main():
    """
    Pipeline complet du projet
    """

    # 1. Charger les données
    df = load_data()

    # 2. Préparer les données
    X, y = prepare_data(df)

    # 3. Séparer train / test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 4. Entraîner le modèle
    model = train_model(X_train, y_train)

    # 5. Évaluer le modèle
    metrics, y_pred = evaluate_model(model, X_test, y_test)

    # 6. Générer les graphiques
    plot_predictions(y_test, y_pred)

    # 7. Sauvegarder le modèle
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/random_forest_regression.pkl")


# ==============================
# LANCEMENT DU SCRIPT
# ==============================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR: {e}", file=sys.stderr)
        sys.exit(1)
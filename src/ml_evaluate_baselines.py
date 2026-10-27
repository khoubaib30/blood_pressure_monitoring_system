"""
Évaluation du modèle de risque : comparaison de XGBoost à des baselines simples
en validation croisée à 5 plis (une séquence = un patient, donc découpage par patient).

Usage : python src/ml_evaluate_baselines.py [data/ml_training_data.csv]
"""
import sys

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold

TARGETS = ["critical_risk_1h", "critical_risk_6h", "critical_risk_24h"]
HORIZONS = ["1 h", "6 h", "24 h"]


def main(path):
    df = pd.read_csv(path)
    features = [c for c in df.columns if c.startswith("obs_")]
    X, y = df[features].values, df[TARGETS].values

    # Baseline naïve : dernière mesure + moyenne des 5 dernières mesures
    sys_cols = [f"obs_{i}_systolic" for i in range(26, 31)]
    dia_cols = [f"obs_{i}_diastolic" for i in range(26, 31)]
    s, d = df[sys_cols].values, df[dia_cols].values
    X_simple = np.c_[s[:, -1], d[:, -1], s.mean(1), d.mean(1)]

    models = ["Moyenne (sans modèle)", "Linéaire sur les dernières mesures", "Random Forest", "XGBoost"]
    r2 = {m: [[] for _ in TARGETS] for m in models}
    mae = {m: [[] for _ in TARGETS] for m in models}

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    for train, test in kf.split(X):
        for name in models:
            if name.startswith("Moyenne"):
                pred = np.tile(y[train].mean(0), (len(test), 1))
            elif name.startswith("Linéaire"):
                pred = LinearRegression().fit(X_simple[train], y[train]).predict(X_simple[test])
            elif name == "Random Forest":
                rf = RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42)
                pred = rf.fit(X[train], y[train]).predict(X[test])
            else:
                model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, subsample=0.8,
                                         colsample_bytree=0.8, random_state=42, n_jobs=-1, verbosity=0)
                pred = model.fit(X[train], y[train]).predict(X[test])
            pred = np.clip(pred, 0, 1)
            for j in range(len(TARGETS)):
                r2[name][j].append(r2_score(y[test, j], pred[:, j]))
                mae[name][j].append(mean_absolute_error(y[test, j], pred[:, j]))

    print("| Modèle | " + " | ".join(f"MAE {h}" for h in HORIZONS) + " | R² (1 h / 6 h / 24 h) |")
    print("|---|" + "---|" * (len(HORIZONS) + 1))
    for name in models:
        maes = " | ".join(f"{np.mean(v):.3f}" for v in mae[name])
        r2s = " / ".join(f"{np.mean(v):.2f}" for v in r2[name])
        print(f"| {name} | {maes} | {r2s} |")

    base = [np.mean(v) for v in mae["Linéaire sur les dernières mesures"]]
    best = [np.mean(v) for v in mae["XGBoost"]]
    gains = ", ".join(f"{h} : -{100 * (b - x) / b:.0f} %" for h, b, x in zip(HORIZONS, base, best))
    print(f"\nRéduction de la MAE de XGBoost par rapport à la baseline linéaire : {gains}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/ml_training_data.csv")

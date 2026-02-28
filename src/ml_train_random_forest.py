import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
import sys

try:
    plt.style.use('seaborn-v0_8-darkgrid')
except:
    try:
        plt.style.use('seaborn-darkgrid')
    except:
        plt.style.use('ggplot')
sns.set_palette("husl")


def load_data():
    data_path = "data/ml_training_data.csv"
    if not os.path.exists(data_path):
        print(f"ERREUR: Fichier {data_path} introuvable!", file=sys.stderr)
        sys.exit(1)
    return pd.read_csv(data_path)


def prepare_data(df):
    feature_cols = [col for col in df.columns if col.startswith('obs_')]
    X = df[feature_cols].values
    y = df[['critical_risk_1h', 'critical_risk_6h', 'critical_risk_24h']].values
    return X, y


def train_model(X_train, y_train):
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    
    y_test_flat = y_test.flatten()
    y_pred_flat = y_pred.flatten()
    
    overall_mae = mean_absolute_error(y_test_flat, y_pred_flat)
    overall_rmse = np.sqrt(mean_squared_error(y_test_flat, y_pred_flat))
    overall_r2 = r2_score(y_test_flat, y_pred_flat)
    
    metrics = {}
    for i, target_name in enumerate(['critical_risk_1h', 'critical_risk_6h', 'critical_risk_24h']):
        y_true = y_test[:, i]
        y_pred_target = y_pred[:, i]
        
        mae = mean_absolute_error(y_true, y_pred_target)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred_target))
        r2 = r2_score(y_true, y_pred_target)
        
        metrics[target_name] = {'mae': mae, 'rmse': rmse, 'r2': r2}
    
    return metrics, y_pred


def plot_predictions(y_test, y_pred, output_dir="models"):
    os.makedirs(output_dir, exist_ok=True)
    
    target_names = ['critical_risk_1h', 'critical_risk_6h', 'critical_risk_24h']
    target_labels = ['Risque 1h', 'Risque 6h', 'Risque 24h']
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('Prédictions vs Valeurs Réelles - Random Forest', fontsize=16, fontweight='bold')
    
    for idx, (target_name, target_label) in enumerate(zip(target_names, target_labels)):
        y_true = y_test[:, idx]
        y_pred_target = y_pred[:, idx]
        
        ax = axes[idx]
        ax.scatter(y_true, y_pred_target, alpha=0.5, s=30, color='#A23B72')
        ax.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 
                'r--', lw=2, label='Ligne parfaite')
        ax.set_xlabel('Valeur Réelle', fontsize=11)
        ax.set_ylabel('Valeur Prédite', fontsize=11)
        ax.set_title(f'{target_label}', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        r2 = r2_score(y_true, y_pred_target)
        ax.text(0.05, 0.95, f'R² = {r2:.3f}', transform=ax.transAxes, 
                fontsize=11, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'random_forest_predictions_scatter.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    metrics_data = []
    for target_name in target_names:
        y_true = y_test[:, target_names.index(target_name)]
        y_pred_target = y_pred[:, target_names.index(target_name)]
        metrics_data.append({
            'target': target_name.replace('critical_risk_', ''),
            'MAE': mean_absolute_error(y_true, y_pred_target),
            'RMSE': np.sqrt(mean_squared_error(y_true, y_pred_target)),
            'R²': r2_score(y_true, y_pred_target)
        })
    
    df_metrics = pd.DataFrame(metrics_data)
    x = np.arange(len(df_metrics))
    width = 0.25
    
    ax.bar(x - width, df_metrics['MAE'], width, label='MAE', color='#FF6B6B', alpha=0.8)
    ax.bar(x, df_metrics['RMSE'], width, label='RMSE', color='#4ECDC4', alpha=0.8)
    ax2 = ax.twinx()
    ax2.bar(x + width, df_metrics['R²'], width, label='R²', color='#95E1D3', alpha=0.8)
    
    ax.set_xlabel('Horizon Temporel', fontsize=12, fontweight='bold')
    ax.set_ylabel('MAE / RMSE', fontsize=12, fontweight='bold')
    ax2.set_ylabel('R² Score', fontsize=12, fontweight='bold')
    ax.set_title('Métriques par Target - Random Forest', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(df_metrics['target'])
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'random_forest_metrics_by_target.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()


def main():
    df = load_data()
    X, y = prepare_data(df)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    model = train_model(X_train, y_train)
    metrics, y_pred = evaluate_model(model, X_test, y_test)
    
    plot_predictions(y_test, y_pred)
    
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/random_forest_regression.pkl")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR: {e}", file=sys.stderr)
        sys.exit(1)

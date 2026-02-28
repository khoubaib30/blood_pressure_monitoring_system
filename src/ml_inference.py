"""
Module d'inférence ML pour prédire les risques de crise hypertensive
Utilise les modèles XGBoost entraînés
"""

import os
import pandas as pd
import joblib
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Configuration
SEQUENCE_LENGTH = 30
# Support pour Docker et local
MODELS_DIR = "/app/models" if os.path.exists("/app/models") else "models"
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "data"

class MLPredictor:
    """Classe pour faire des prédictions ML sur les données de patients"""
    
    def __init__(self):
        """Initialise le prédicteur en chargeant le modèle de régression"""
        self.model_regression = None
        self.models_loaded = False
        self._load_models()
    
    def _load_models(self):
        """Charge le modèle XGBoost de régression depuis les fichiers"""
        try:
            regression_path = os.path.join(MODELS_DIR, "xgboost_regression.pkl")
            
            if not os.path.exists(regression_path):
                return
            
            self.model_regression = joblib.load(regression_path)
            self.models_loaded = True
        except Exception as e:
            self.models_loaded = False
    
    def get_patient_observations(self, patient_id: str, limit: int = None) -> List[Dict]:
        """
        Récupère les observations d'un patient depuis le CSV
        
        Args:
            patient_id: ID du patient
            limit: Nombre maximum d'observations à récupérer (None = toutes)
        
        Returns:
            Liste d'observations triées par timestamp (plus anciennes en premier)
        """
        csv_file = os.path.join(DATA_DIR, "blood_pressure_data.csv")
        
        if not os.path.exists(csv_file):
            return []
        
        try:
            df = pd.read_csv(csv_file)
            
            # Filtrer par patient_id
            patient_data = df[df['patient_id'] == patient_id].copy()
            
            if len(patient_data) == 0:
                return []
            
            # Convertir timestamp en datetime et trier
            patient_data['timestamp'] = pd.to_datetime(patient_data['timestamp'])
            patient_data = patient_data.sort_values('timestamp')
            
            # Limiter si nécessaire
            if limit:
                patient_data = patient_data.tail(limit)
            
            # Convertir en liste de dictionnaires
            observations = []
            for _, row in patient_data.iterrows():
                obs = {
                    'timestamp': row['timestamp'],
                    'systolic': int(row['systolic']),
                    'diastolic': int(row['diastolic']),
                    'heart_rate': int(row['heart_rate'])
                }
                observations.append(obs)
            
            return observations
        except Exception as e:
            return []
    
    def prepare_features(self, observations: List[Dict]) -> Optional[np.ndarray]:
        """
        Prépare les features pour le modèle à partir des observations
        
        Args:
            observations: Liste de 30 observations (ou plus, on prend les 30 dernières)
        
        Returns:
            Array numpy de shape (1, 120) ou None si pas assez d'observations
        """
        if len(observations) < SEQUENCE_LENGTH:
            return None
        
        # Prendre les 30 dernières observations
        last_30 = observations[-SEQUENCE_LENGTH:]
        
        # Créer le vecteur de features
        features = []
        
        for obs in last_30:
            # Extraire l'heure du jour
            timestamp = obs['timestamp']
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            hour_of_day = timestamp.hour + timestamp.minute / 60.0
            
            # Ajouter les 4 features de cette observation
            features.extend([
                obs['systolic'],
                obs['diastolic'],
                obs['heart_rate'],
                hour_of_day
            ])
        
        # Convertir en array numpy
        features_array = np.array(features).reshape(1, -1)
        
        return features_array
    
    def predict(self, patient_id: str) -> Optional[Dict]:
        """
        Fait une prédiction pour un patient
        
        Args:
            patient_id: ID du patient
        
        Returns:
            Dictionnaire avec les prédictions ou None si impossible
        """
        if not self.models_loaded:
            return None
        
        # Récupérer les observations du patient
        observations = self.get_patient_observations(patient_id)
        
        if len(observations) < SEQUENCE_LENGTH:
            return None
        
        # Préparer les features
        features = self.prepare_features(observations)
        
        if features is None:
            return None
        
        try:
            # Prédictions de régression (probabilités)
            regression_pred = self.model_regression.predict(features)[0]
            # Forcer les valeurs entre 0 et 1 (probabilités ne peuvent pas être négatives)
            critical_risk_1h = max(0.0, min(1.0, float(regression_pred[0])))
            critical_risk_6h = max(0.0, min(1.0, float(regression_pred[1])))
            critical_risk_24h = max(0.0, min(1.0, float(regression_pred[2])))
            
            # Déterminer le niveau d'alerte
            alert_level = self._get_alert_level(critical_risk_6h)
            
            return {
                'patient_id': patient_id,
                'critical_risk_1h': round(critical_risk_1h, 3),
                'critical_risk_6h': round(critical_risk_6h, 3),
                'critical_risk_24h': round(critical_risk_24h, 3),
                'alert_level': alert_level,
                'timestamp': datetime.now().isoformat(),
                'observations_count': len(observations)
            }
        except Exception as e:
            return None
    
    def _get_alert_level(self, critical_risk_6h: float) -> str:
        """
        Détermine le niveau d'alerte basé sur critical_risk_6h
        
        Seuils:
        - critical: >= 60%
        - high: >= 40%
        - medium: >= 20%
        - low: < 20%
        
        Returns:
            'critical', 'high', 'medium', ou 'low'
        """
        if critical_risk_6h >= 0.60:
            return 'critical'
        elif critical_risk_6h >= 0.40:
            return 'high'
        elif critical_risk_6h >= 0.20:
            return 'medium'
        else:
            return 'low'
    
    def predict_all_patients(self) -> List[Dict]:
        """
        Fait des prédictions pour tous les patients disponibles
        
        Returns:
            Liste de prédictions pour tous les patients
        """
        csv_file = os.path.join(DATA_DIR, "blood_pressure_data.csv")
        
        if not os.path.exists(csv_file):
            return []
        
        try:
            df = pd.read_csv(csv_file)
            patient_ids = sorted(df['patient_id'].unique())
            
            predictions = []
            for patient_id in patient_ids:
                prediction = self.predict(patient_id)
                if prediction:
                    predictions.append(prediction)
            
            return predictions
        except Exception as e:
            return []


# Instance globale du prédicteur
_predictor_instance = None

def get_predictor() -> MLPredictor:
    """Retourne l'instance globale du prédicteur"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = MLPredictor()
    return _predictor_instance

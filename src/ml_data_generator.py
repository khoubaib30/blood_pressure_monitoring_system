"""
Générateur de données d'entraînement ML
Génère des séquences temporelles avec targets de régression
"""

import random
import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys

# Import des modules existants
from patient_profile import PatientProfile


# Configuration
NUM_SEQUENCES = 5000
SEQUENCE_LENGTH = 30  # 30 observations historiques
OBSERVATION_INTERVAL_MINUTES = 15  # Intervalle entre observations (15 minutes)
OUTPUT_FILE = "data/ml_training_data.csv"

# Répartition des risques
RISK_DISTRIBUTION = {
    "LOW": 2000,      # 40%
    "MEDIUM": 2000,   # 40%
    "HIGH": 1000      # 20%
}

# Seuil critique pour crise hypertensive
CRITICAL_SYSTOLIC_THRESHOLD = 180
CRITICAL_DIASTOLIC_THRESHOLD = 120


def is_critical(systolic: int, diastolic: int) -> bool:
    """Vérifie si la pression artérielle est critique"""
    return systolic > CRITICAL_SYSTOLIC_THRESHOLD or diastolic > CRITICAL_DIASTOLIC_THRESHOLD


def generate_sequence_for_risk_level(risk_level: str, sequence_id: int) -> Dict:
    """
    Génère une séquence avec un niveau de risque spécifique
    
    Args:
        risk_level: LOW, MEDIUM, ou HIGH
        sequence_id: Identifiant de la séquence
        
    Returns:
        Dictionnaire avec les observations et targets
    """
    # Créer un profil patient avec baseline adapté au niveau de risque
    patient_id = f"PATIENT_{sequence_id:05d}"
    device_id = f"DEVICE_{random.randint(1, 10)}"
    
    # Ajuster le baseline selon le niveau de risque
    if risk_level == "LOW":
        # Baseline normal à légèrement élevé
        baseline_systolic = random.randint(100, 130)
        baseline_diastolic = random.randint(65, 85)
        trend_systolic = random.uniform(-0.3, 0.3)  # Stable ou légère amélioration
        trend_diastolic = random.uniform(-0.2, 0.2)
    elif risk_level == "MEDIUM":
        # Baseline modérément élevé
        baseline_systolic = random.randint(130, 160)
        baseline_diastolic = random.randint(80, 100)
        trend_systolic = random.uniform(0.2, 1.0)  # Légère détérioration
        trend_diastolic = random.uniform(0.15, 0.8)
    else:  # HIGH
        # Baseline élevé, proche du critique
        baseline_systolic = random.randint(150, 175)
        baseline_diastolic = random.randint(95, 115)
        trend_systolic = random.uniform(0.5, 2.0)  # Détérioration rapide
        trend_diastolic = random.uniform(0.4, 1.5)
    
    # Créer un profil patient personnalisé
    patient = PatientProfile(patient_id, device_id)
    patient.baseline_systolic = baseline_systolic
    patient.baseline_diastolic = baseline_diastolic
    patient.trend_systolic = trend_systolic
    patient.trend_diastolic = trend_diastolic
    
    # Calculer baseline heart rate
    if baseline_systolic < 120:
        patient.baseline_heart_rate = random.randint(60, 75)
    elif baseline_systolic < 140:
        patient.baseline_heart_rate = random.randint(70, 85)
    else:
        patient.baseline_heart_rate = random.randint(75, 95)
    
    # Réinitialiser le start_time du patient pour que les calculs de tendance soient corrects
    start_time = datetime(2024, 1, 15, random.randint(6, 18), 0, 0)
    patient.start_time = start_time
    patient.last_observation_time = None
    patient.observation_count = 0
    
    # Désactiver les événements aléatoires pour des données plus prévisibles
    patient.active_stress_event = False
    patient.stress_event_remaining = 0
    patient.medication_effect_active = False
    patient.medication_effect_remaining = 0
    
    # Générer les observations historiques (30 observations)
    observations = []
    
    for i in range(SEQUENCE_LENGTH):
        current_time = start_time + timedelta(minutes=i * OBSERVATION_INTERVAL_MINUTES)
        systolic, diastolic, heart_rate = patient.get_current_bp(current_time)
        
        hour_of_day = current_time.hour + current_time.minute / 60.0
        
        observations.append({
            "systolic": systolic,
            "diastolic": diastolic,
            "heart_rate": heart_rate,
            "hour_of_day": hour_of_day,
            "timestamp": current_time
        })
    
    # Générer les observations futures pour calculer les targets
    last_obs_time = observations[-1]["timestamp"]
    
    # Observations futures : 1h, 6h, 24h
    future_times = {
        "1h": last_obs_time + timedelta(hours=1),
        "6h": last_obs_time + timedelta(hours=6),
        "24h": last_obs_time + timedelta(hours=24)
    }
    
    # Générer plusieurs observations futures pour chaque fenêtre (pour calculer probabilité)
    future_observations_1h = []
    future_observations_6h = []
    future_observations_24h = []
    
    # 1h : 4 observations (toutes les 15 min)
    for i in range(4):
        time = last_obs_time + timedelta(minutes=(i + 1) * 15)
        systolic, diastolic, heart_rate = patient.get_current_bp(time)
        future_observations_1h.append((systolic, diastolic))
    
    # 6h : 24 observations (toutes les 15 min)
    for i in range(24):
        time = last_obs_time + timedelta(minutes=(i + 1) * 15)
        systolic, diastolic, heart_rate = patient.get_current_bp(time)
        future_observations_6h.append((systolic, diastolic))
    
    # 24h : 96 observations (toutes les 15 min)
    for i in range(96):
        time = last_obs_time + timedelta(minutes=(i + 1) * 15)
        systolic, diastolic, heart_rate = patient.get_current_bp(time)
        future_observations_24h.append((systolic, diastolic))
    
    # Calculer les probabilités de crise
    critical_count_1h = sum(1 for s, d in future_observations_1h if is_critical(s, d))
    critical_count_6h = sum(1 for s, d in future_observations_6h if is_critical(s, d))
    critical_count_24h = sum(1 for s, d in future_observations_24h if is_critical(s, d))
    
    critical_risk_1h = critical_count_1h / len(future_observations_1h)
    critical_risk_6h = critical_count_6h / len(future_observations_6h)
    critical_risk_24h = critical_count_24h / len(future_observations_24h)
    
    # Ajuster les probabilités selon le niveau de risque souhaité
    if risk_level == "LOW":
        # Forcer des probabilités faibles
        critical_risk_1h = min(critical_risk_1h, random.uniform(0.0, 0.15))
        critical_risk_6h = min(critical_risk_6h, random.uniform(0.0, 0.20))
        critical_risk_24h = min(critical_risk_24h, random.uniform(0.05, 0.30))
    elif risk_level == "MEDIUM":
        # Forcer des probabilités moyennes
        critical_risk_1h = max(0.10, min(critical_risk_1h, random.uniform(0.10, 0.50)))
        critical_risk_6h = max(0.20, min(critical_risk_6h, random.uniform(0.20, 0.70)))
        critical_risk_24h = max(0.30, min(critical_risk_24h, random.uniform(0.40, 0.80)))
    else:  # HIGH
        # Forcer des probabilités élevées
        critical_risk_1h = max(0.50, min(critical_risk_1h, random.uniform(0.60, 0.95)))
        critical_risk_6h = max(0.70, min(critical_risk_6h, random.uniform(0.75, 0.98)))
        critical_risk_24h = max(0.80, min(critical_risk_24h, random.uniform(0.85, 0.99)))
    
    return {
        "patient_id": patient_id,
        "sequence_id": f"SEQ_{sequence_id:05d}",
        "observations": observations,
        "targets": {
            "critical_risk_1h": round(critical_risk_1h, 3),
            "critical_risk_6h": round(critical_risk_6h, 3),
            "critical_risk_24h": round(critical_risk_24h, 3)
        }
    }


def generate_training_data():
    """Génère toutes les séquences d'entraînement et les sauvegarde en CSV"""
    
    # Créer le dossier data s'il n'existe pas
    os.makedirs("data", exist_ok=True)
    
    sequences = []
    sequence_id = 1
    
    for risk_level, count in RISK_DISTRIBUTION.items():
        for i in range(count):
            sequence = generate_sequence_for_risk_level(risk_level, sequence_id)
            sequences.append(sequence)
            sequence_id += 1
    
    # Créer les en-têtes
    headers = ["patient_id", "sequence_id"]
    
    # Ajouter les colonnes pour les 30 observations
    for i in range(1, SEQUENCE_LENGTH + 1):
        headers.extend([
            f"obs_{i}_systolic",
            f"obs_{i}_diastolic",
            f"obs_{i}_heart_rate",
            f"obs_{i}_hour"
        ])
    
    # Ajouter les colonnes pour les targets
    headers.extend([
        "critical_risk_1h",
        "critical_risk_6h",
        "critical_risk_24h"
    ])
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        
        for sequence in sequences:
            row = [
                sequence["patient_id"],
                sequence["sequence_id"]
            ]
            
            # Ajouter les observations
            for obs in sequence["observations"]:
                row.extend([
                    obs["systolic"],
                    obs["diastolic"],
                    obs["heart_rate"],
                    round(obs["hour_of_day"], 2)
                ])
            
            # Ajouter les targets
            targets = sequence["targets"]
            row.extend([
                targets["critical_risk_1h"],
                targets["critical_risk_6h"],
                targets["critical_risk_24h"]
            ])
            
            writer.writerow(row)


if __name__ == "__main__":
    try:
        generate_training_data()
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR: {e}", file=sys.stderr)
        sys.exit(1)

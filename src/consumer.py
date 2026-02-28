"""
Consommateur Kafka pour les données de pression artérielle
Récupère les messages FHIR (Observation) de Kafka, les analyse et les traite
"""

import json
import os
import sys
from kafka import KafkaConsumer
from datetime import datetime
import pandas as pd

# Import des modules personnalisés
from fhir_utils import extract_data_from_fhir
from blood_pressure_categories import BloodPressureCategory
from elasticsearch_connector import ElasticsearchConnector

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'blood-pressure-data')

# Dossier pour sauvegarder les données
DATA_DIR = '/app/data' if os.path.exists('/app/data') else './data'
os.makedirs(DATA_DIR, exist_ok=True)

def create_consumer():
    """Crée et retourne un consommateur Kafka avec retry"""
    import time
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8') if isinstance(m, bytes) else m),
                key_deserializer=lambda k: k.decode('utf-8') if k and isinstance(k, bytes) else (k if k else None),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='blood-pressure-consumer-group',
                consumer_timeout_ms=5000
            )
            return consumer
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                print(f"ERROR: Kafka connection failed after {max_retries} attempts: {e}", file=sys.stderr)
                sys.exit(1)

def save_data_to_json(extracted_data):
    """
    Sauvegarde les données normales dans un fichier JSON (archivage officiel selon l'énoncé)
    
    Args:
        extracted_data: Données extraites de l'observation FHIR
    """
    json_file_path = os.path.join(DATA_DIR, 'blood_pressure_normal.json')
    
    # Préparer les données pour le JSON
    json_data = {
        'observation_id': extracted_data['observation_id'],
        'timestamp': extracted_data['timestamp'],
        'patient_id': extracted_data['patient_id'],
        'systolic': extracted_data['systolic'],
        'diastolic': extracted_data['diastolic'],
        'heart_rate': extracted_data['heart_rate'],
        'category': extracted_data['category'],
        'device_id': extracted_data['device_id']
    }
    
    # Lire les données existantes si le fichier existe
    existing_data = []
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = []
        except Exception:
            existing_data = []
    
    # Ajouter la nouvelle donnée
    existing_data.append(json_data)
    
    # Sauvegarder le fichier JSON
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        return json_file_path
    except Exception:
        return None

def save_data_to_csv_cache(extracted_data):
    """
    Sauvegarde les données dans un fichier CSV (cache temporaire pour le dashboard)
    Ce n'est PAS l'archivage officiel, juste un cache pratique
    
    Args:
        extracted_data: Données extraites de l'observation FHIR
    """
    file_path = os.path.join(DATA_DIR, 'blood_pressure_data.csv')
    
    # Préparer les données pour le CSV (format simplifié)
    # Utiliser 'status' pour compatibilité avec le dashboard
    csv_data = {
        'observation_id': extracted_data['observation_id'],
        'timestamp': extracted_data['timestamp'],
        'patient_id': extracted_data['patient_id'],
        'systolic': extracted_data['systolic'],
        'diastolic': extracted_data['diastolic'],
        'heart_rate': extracted_data['heart_rate'],
        'status': extracted_data['category'],  # Utiliser 'status' pour le dashboard
        'device_id': extracted_data['device_id']
    }
    
    # Créer un DataFrame avec les données
    df = pd.DataFrame([csv_data])
    
    # Vérifier si le fichier existe et lire le header pour maintenir la cohérence
    if os.path.exists(file_path):
        try:
            # Lire le header pour vérifier les colonnes
            existing_df = pd.read_csv(file_path, nrows=0)
            # Si le fichier n'a pas 'status', on doit le recréer avec le bon format
            if 'status' not in existing_df.columns:
                # Lire toutes les données existantes
                existing_df = pd.read_csv(file_path, on_bad_lines='skip', engine='python')
                # Ajouter la colonne 'status' à partir de 'category' si elle existe
                if 'category' in existing_df.columns:
                    existing_df['status'] = existing_df['category']
                elif 'status' not in existing_df.columns:
                    # Si ni category ni status n'existent, créer status vide
                    existing_df['status'] = 'NORMAL'
                # Réorganiser les colonnes dans le bon ordre
                columns_order = ['observation_id', 'timestamp', 'patient_id', 'systolic', 'diastolic', 'heart_rate', 'status', 'device_id']
                existing_df = existing_df[[col for col in columns_order if col in existing_df.columns]]
                # Sauvegarder avec le nouveau format
                existing_df.to_csv(file_path, mode='w', header=True, index=False)
        except Exception:
            pass
    
    # Ajouter au fichier CSV (créer ou append)
    if os.path.exists(file_path):
        df.to_csv(file_path, mode='a', header=False, index=False)
    else:
        df.to_csv(file_path, mode='w', header=True, index=False)
    
    return file_path


def analyze_data(extracted_data):
    """
    Analyse les données et détecte les alertes selon les catégories médicales
    
    Args:
        extracted_data: Données extraites de l'observation FHIR
        
    Returns:
        Liste des alertes détectées
    """
    alerts = []
    systolic = extracted_data['systolic']
    diastolic = extracted_data['diastolic']
    heart_rate = extracted_data['heart_rate']
    category = extracted_data['category']
    
    # Alertes basées sur la catégorie
    if category == BloodPressureCategory.HYPERTENSIVE_CRISIS:
        alerts.append("🚨 CRITIQUE: Crise hypertensive - Consultation médicale immédiate requise!")
    elif category == BloodPressureCategory.STAGE2_HYPERTENSION:
        alerts.append("⚠️  ALERTE: Hypertension Stade 2 détectée")
    elif category == BloodPressureCategory.STAGE1_HYPERTENSION:
        alerts.append("⚠️  ATTENTION: Hypertension Stade 1 détectée")
    elif category == BloodPressureCategory.ELEVATED:
        alerts.append("ℹ️  INFORMATION: Pression artérielle élevée")
    
    # Alertes sur le rythme cardiaque
    if heart_rate > 100:
        alerts.append("⚠️  ALERTE: Tachycardie détectée (rythme > 100 bpm)")
    elif heart_rate < 60:
        alerts.append("⚠️  ALERTE: Bradycardie détectée (rythme < 60 bpm)")
    
    return alerts

def main():
    """Fonction principale du consommateur"""
    consumer = create_consumer()
    es_connector = ElasticsearchConnector()
    message_count = 0
    category_stats = {}
    
    try:
        for message in consumer:
            # Récupérer l'observation FHIR
            fhir_observation = message.value
            patient_id = message.key if message.key else "UNKNOWN"  # Déjà décodé par key_deserializer
            
            # Extraire les données de l'observation FHIR
            extracted_data = extract_data_from_fhir(fhir_observation)
            
            message_count += 1
            category = extracted_data['category']
            category_stats[category] = category_stats.get(category, 0) + 1
            
            if category == BloodPressureCategory.NORMAL:
                save_data_to_json(extracted_data)
            else:
                if es_connector.is_connected():
                    es_connector.index_observation(extracted_data)
            
            save_data_to_csv_cache(extracted_data)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        consumer.close()

if __name__ == "__main__":
    main()

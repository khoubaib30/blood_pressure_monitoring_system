"""
Producteur Kafka pour les données de pression artérielle
Génère des messages FHIR (Observation) en format JSON et les envoie à Kafka
"""

import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer
import os
import sys

# Import des modules personnalisés
from fhir_utils import create_fhir_observation
from blood_pressure_categories import BloodPressureCategory
from patient_profile import PatientProfile

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'blood-pressure-data')

# Configuration de génération
GENERATION_INTERVAL = float(os.getenv('GENERATION_INTERVAL', '15.0'))  # secondes
NUM_PATIENTS = 50  # Nombre de patients actifs

# Stockage des profils patients
patient_profiles = {}
current_patient_index = 0

def initialize_patients():
    """Initialise les profils de patients avec distribution de risque"""
    global patient_profiles
    patient_profiles = {}
    
    for i in range(1, NUM_PATIENTS + 1):
        patient_id = f"PATIENT_{i:04d}"
        device_id = f"DEVICE_{random.randint(1, 10)}"
        patient = PatientProfile(patient_id, device_id)
        
        # Distribution de risque pour générer des alertes critiques
        # 10% patients à risque critique, 20% risque élevé, 30% risque moyen, 40% risque faible
        risk_distribution = random.random()
        
        if risk_distribution < 0.10:  # 10% - Risque critique
            # Baseline très élevé, tendance détériorante rapide
            patient.baseline_systolic = random.randint(160, 180)
            patient.baseline_diastolic = random.randint(100, 120)
            patient.trend_systolic = random.uniform(1.0, 2.5)  # Détérioration rapide
            patient.trend_diastolic = random.uniform(0.8, 2.0)
            patient.baseline_heart_rate = random.randint(85, 105)
        elif risk_distribution < 0.30:  # 20% - Risque élevé
            # Baseline élevé, tendance détériorante
            patient.baseline_systolic = random.randint(145, 165)
            patient.baseline_diastolic = random.randint(90, 110)
            patient.trend_systolic = random.uniform(0.5, 1.5)
            patient.trend_diastolic = random.uniform(0.4, 1.2)
            patient.baseline_heart_rate = random.randint(75, 95)
        elif risk_distribution < 0.60:  # 30% - Risque moyen
            # Baseline modéré, tendance variable
            patient.baseline_systolic = random.randint(130, 150)
            patient.baseline_diastolic = random.randint(80, 95)
            patient.trend_systolic = random.uniform(-0.2, 0.8)
            patient.trend_diastolic = random.uniform(-0.15, 0.6)
            patient.baseline_heart_rate = random.randint(70, 85)
        else:  # 40% - Risque faible
            # Baseline normal, tendance stable ou améliorante
            patient.baseline_systolic = random.randint(100, 130)
            patient.baseline_diastolic = random.randint(65, 85)
            patient.trend_systolic = random.uniform(-0.5, 0.3)
            patient.trend_diastolic = random.uniform(-0.4, 0.2)
            patient.baseline_heart_rate = random.randint(60, 75)
        
        patient_profiles[patient_id] = patient


def get_next_patient():
    """Retourne le prochain patient dans la rotation (round-robin)"""
    global current_patient_index
    patient_ids = list(patient_profiles.keys())
    patient_id = patient_ids[current_patient_index]
    current_patient_index = (current_patient_index + 1) % len(patient_ids)
    return patient_id


def generate_fhir_observation():
    """
    Génère un message FHIR Observation pour la pression artérielle
    Utilise les profils patients pour générer des données cohérentes
    
    Returns:
        Tuple (fhir_observation, category, description, patient_id)
    """
    # Sélectionner le prochain patient (round-robin)
    patient_id = get_next_patient()
    patient = patient_profiles[patient_id]
    
    # Obtenir les valeurs BP actuelles basées sur le profil patient
    current_time = datetime.now()
    systolic, diastolic, heart_rate = patient.get_current_bp(current_time)
    
    # Catégoriser selon les standards médicaux
    category, description = BloodPressureCategory.categorize(systolic, diastolic)
    
    # Créer l'observation FHIR
    fhir_observation = create_fhir_observation(
        patient_id=patient_id,
        systolic=systolic,
        diastolic=diastolic,
        heart_rate=heart_rate,
        device_id=patient.device_id,
        category=category
    )
    
    return fhir_observation, category, description, patient_id


def create_producer():
    """Crée et retourne un producteur Kafka avec retry"""
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k and isinstance(k, str) else (k if k else None),
                api_version=(0, 10, 1),
                request_timeout_ms=5000
            )
            # Test connection by sending a metadata request
            # Producer will connect on first send, so we just return it
            return producer
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                print(f"ERROR: Kafka connection failed after {max_retries} attempts: {e}", file=sys.stderr)
                sys.exit(1)


def main():
    """Fonction principale du producteur"""
    # Initialiser les profils patients
    initialize_patients()
    
    producer = create_producer()
    
    try:
        message_count = 0
        while True:
            # Générer une observation FHIR avec profil patient cohérent
            fhir_observation, category, description, patient_id = generate_fhir_observation()
            
            # Extraire les valeurs pour l'affichage
            systolic = fhir_observation['component'][0]['valueQuantity']['value']
            diastolic = fhir_observation['component'][1]['valueQuantity']['value']
            heart_rate = fhir_observation['component'][2]['valueQuantity']['value']
            patient = patient_profiles[patient_id]
            
            # Envoyer à Kafka (format FHIR JSON)
            future = producer.send(
                KAFKA_TOPIC,
                key=patient_id,
                value=fhir_observation
            )
            
            # Attendre la confirmation
            record_metadata = future.get(timeout=10)
            message_count += 1
            
            time.sleep(GENERATION_INTERVAL)
            time.sleep(GENERATION_INTERVAL)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        producer.close()

if __name__ == "__main__":
    main()

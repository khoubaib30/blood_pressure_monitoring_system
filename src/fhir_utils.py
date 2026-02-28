"""
Utilitaires pour la génération de messages FHIR (Observation)
Format standard pour les données de santé
"""

from datetime import datetime
from typing import Dict, Any
import uuid


def create_fhir_observation(
    patient_id: str,
    systolic: int,
    diastolic: int,
    heart_rate: int,
    device_id: str,
    category: str
) -> Dict[str, Any]:
    """
    Crée un message FHIR Observation pour la pression artérielle
    
    Args:
        patient_id: Identifiant du patient
        systolic: Pression systolique (mmHg)
        diastolic: Pression diastolique (mmHg)
        heart_rate: Rythme cardiaque (bpm)
        device_id: Identifiant de l'appareil
        category: Catégorie de pression artérielle
        
    Returns:
        Dictionnaire représentant une Observation FHIR en format JSON
    """
    observation_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    fhir_observation = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel with all children optional"
                }
            ],
            "text": "Blood Pressure"
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
            "display": patient_id
        },
        "effectiveDateTime": timestamp,
        "performer": [
            {
                "display": device_id
            }
        ],
        "component": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure"
                        }
                    ],
                    "text": "Systolic Blood Pressure"
                },
                "valueQuantity": {
                    "value": systolic,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic blood pressure"
                        }
                    ],
                    "text": "Diastolic Blood Pressure"
                },
                "valueQuantity": {
                    "value": diastolic,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8867-4",
                            "display": "Heart rate"
                        }
                    ],
                    "text": "Heart Rate"
                },
                "valueQuantity": {
                    "value": heart_rate,
                    "unit": "beats/min",
                    "system": "http://unitsofmeasure.org",
                    "code": "/min"
                }
            }
        ],
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": _get_interpretation_code(category),
                        "display": category.upper()
                    }
                ],
                "text": category
            }
        ],
        "note": [
            {
                "text": f"Blood pressure category: {category}"
            }
        ]
    }
    
    return fhir_observation


def _get_interpretation_code(category: str) -> str:
    """Retourne le code d'interprétation FHIR selon la catégorie"""
    category_codes = {
        "NORMAL": "N",
        "ELEVATED": "H",
        "STAGE1_HYPERTENSION": "HH",
        "STAGE2_HYPERTENSION": "HHH",
        "HYPERTENSIVE_CRISIS": "HU"
    }
    return category_codes.get(category.upper(), "N")


def extract_data_from_fhir(fhir_observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les données simplifiées d'une Observation FHIR
    
    Args:
        fhir_observation: Observation FHIR au format JSON
        
    Returns:
        Dictionnaire avec les données extraites
    """
    # Extraire les valeurs des composants
    systolic = None
    diastolic = None
    heart_rate = None
    
    for component in fhir_observation.get("component", []):
        code_text = component.get("code", {}).get("text", "")
        value = component.get("valueQuantity", {}).get("value")
        
        if "Systolic" in code_text:
            systolic = int(value)
        elif "Diastolic" in code_text:
            diastolic = int(value)
        elif "Heart Rate" in code_text or "Heart rate" in code_text:
            heart_rate = int(value)
    
    # Extraire la catégorie
    category = "NORMAL"
    if fhir_observation.get("interpretation"):
        category = fhir_observation["interpretation"][0].get("text", "NORMAL")
    
    # Extraire le patient ID
    patient_ref = fhir_observation.get("subject", {}).get("reference", "")
    patient_id = patient_ref.replace("Patient/", "") if "Patient/" in patient_ref else ""
    
    # Extraire le device ID
    device_id = ""
    if fhir_observation.get("performer"):
        device_id = fhir_observation["performer"][0].get("display", "")
    
    return {
        "observation_id": fhir_observation.get("id"),
        "patient_id": patient_id,
        "systolic": systolic,
        "diastolic": diastolic,
        "heart_rate": heart_rate,
        "category": category,
        "device_id": device_id,
        "timestamp": fhir_observation.get("effectiveDateTime"),
        "fhir_resource": fhir_observation  # Garder la ressource complète
    }

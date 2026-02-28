"""
Script pour vérifier le nombre d'observations par patient
"""

import pandas as pd
import os
from collections import Counter

def check_observations_per_patient():
    """Vérifie le nombre d'observations par patient"""
    
    csv_file = "data/blood_pressure_data.csv"
    
    if not os.path.exists(csv_file):
        print(f"Fichier {csv_file} introuvable")
        return
    
    # Lire le CSV
    df = pd.read_csv(csv_file)
    
    # Compter les observations par patient
    patient_counts = df['patient_id'].value_counts().sort_index()
    
    # Statistiques
    total_patients = len(patient_counts)
    patients_with_30_plus = (patient_counts >= 30).sum()
    patients_with_less_30 = (patient_counts < 30).sum()
    
    min_obs = patient_counts.min()
    max_obs = patient_counts.max()
    avg_obs = patient_counts.mean()
    
    print("=" * 60)
    print("STATISTIQUES DES OBSERVATIONS PAR PATIENT")
    print("=" * 60)
    print(f"\nNombre total de patients: {total_patients}")
    print(f"Patients avec >= 30 observations: {patients_with_30_plus} ({patients_with_30_plus/total_patients*100:.1f}%)")
    print(f"Patients avec < 30 observations: {patients_with_less_30} ({patients_with_less_30/total_patients*100:.1f}%)")
    print(f"\nMinimum d'observations: {min_obs}")
    print(f"Maximum d'observations: {max_obs}")
    print(f"Moyenne d'observations: {avg_obs:.1f}")
    
    print("\n" + "=" * 60)
    print("DÉTAIL PAR PATIENT")
    print("=" * 60)
    
    # Afficher tous les patients
    for patient_id, count in patient_counts.items():
        status = "[OK]" if count >= 30 else "[X]"
        print(f"{status} {patient_id}: {count} observations")
    
    print("\n" + "=" * 60)
    print("PATIENTS AVEC < 30 OBSERVATIONS")
    print("=" * 60)
    
    patients_need_more = patient_counts[patient_counts < 30]
    if len(patients_need_more) > 0:
        for patient_id, count in patients_need_more.items():
            needed = 30 - count
            print(f"  {patient_id}: {count} observations (besoin de {needed} de plus)")
    else:
        print("  Aucun - Tous les patients ont >= 30 observations!")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_observations_per_patient()

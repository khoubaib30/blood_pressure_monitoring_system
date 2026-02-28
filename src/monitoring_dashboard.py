"""
Tableau de bord de monitoring pour les données de pression artérielle
Interface web Flask pour visualiser les données en temps réel
"""

import os
import json
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
from kafka import KafkaConsumer
import threading
from fhir_utils import extract_data_from_fhir
from auth import verify_password, login_required, get_current_user
from ml_inference import get_predictor

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)  # Clé secrète pour les sessions

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'blood-pressure-data')

# Dossier pour les données
DATA_DIR = '/app/data' if os.path.exists('/app/data') else './data'
os.makedirs(DATA_DIR, exist_ok=True)

# Stockage en mémoire pour les dernières données
latest_data = []
max_data_points = 100

def load_data_from_file():
    """Charge les données depuis le fichier CSV"""
    file_path = os.path.join(DATA_DIR, 'blood_pressure_data.csv')
    if os.path.exists(file_path):
        try:
            # Lire le CSV avec gestion d'erreurs
            df = pd.read_csv(file_path, on_bad_lines='skip', engine='python')
            
            # Si 'status' n'existe pas mais 'category' existe, créer 'status' à partir de 'category'
            if 'status' not in df.columns and 'category' in df.columns:
                df['status'] = df['category']
            
            # Si 'category' n'existe pas mais 'status' existe, créer 'category' à partir de 'status'
            if 'category' not in df.columns and 'status' in df.columns:
                df['category'] = df['status']
            
            return df.to_dict('records')
        except Exception:
            return []
    return []

def get_statistics_from_data(data_list):
    """
    Calcule les statistiques à partir d'une liste de données
    
    Args:
        data_list: Liste de dictionnaires contenant les données
    
    Returns:
        Dictionnaire avec les statistiques
    """
    if not data_list or len(data_list) == 0:
        return {
            'total_readings': 0,
            'avg_systolic': 0,
            'avg_diastolic': 0,
            'avg_heart_rate': 0,
            'normal_count': 0,
            'elevated_count': 0,
            'hypertension_count': 0
        }
    
    try:
        # Convertir en DataFrame pour faciliter les calculs
        df = pd.DataFrame(data_list)
        
        # Si 'status' n'existe pas mais 'category' existe, utiliser 'category' comme 'status'
        if 'status' not in df.columns and 'category' in df.columns:
            df['status'] = df['category']
        
        # Nettoyer les valeurs de status
        if 'status' in df.columns:
            df['status'] = df['status'].astype(str).str.strip().str.upper()
        
        stats = {
            'total_readings': len(df),
            'avg_systolic': float(df['systolic'].mean()) if 'systolic' in df.columns else 0,
            'avg_diastolic': float(df['diastolic'].mean()) if 'diastolic' in df.columns else 0,
            'avg_heart_rate': float(df['heart_rate'].mean()) if 'heart_rate' in df.columns else 0,
            'normal_count': int((df['status'] == 'NORMAL').sum()) if 'status' in df.columns else 0,
            'elevated_count': int((df['status'] == 'ELEVATED').sum()) if 'status' in df.columns else 0,
            'hypertension_count': int((df['status'].isin(['STAGE1_HYPERTENSION', 'STAGE2_HYPERTENSION', 'HYPERTENSIVE_CRISIS']).sum())) if 'status' in df.columns else 0
        }
        return stats
    except Exception:
        return {
            'total_readings': 0,
            'avg_systolic': 0,
            'avg_diastolic': 0,
            'avg_heart_rate': 0,
            'normal_count': 0,
            'elevated_count': 0,
            'hypertension_count': 0
        }

def get_statistics():
    """Calcule les statistiques de toutes les données (sans filtre)"""
    file_path = os.path.join(DATA_DIR, 'blood_pressure_data.csv')
    if not os.path.exists(file_path):
        return {
            'total_readings': 0,
            'avg_systolic': 0,
            'avg_diastolic': 0,
            'avg_heart_rate': 0,
            'normal_count': 0,
            'elevated_count': 0,
            'hypertension_count': 0
        }
    
    data = load_data_from_file()
    return get_statistics_from_data(data)

def kafka_consumer_thread():
    """Thread pour consommer les données Kafka en arrière-plan"""
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8') if isinstance(m, bytes) else m),
            auto_offset_reset='latest',  # Lire seulement les nouvelles données après démarrage
            enable_auto_commit=True,
            group_id='monitoring-dashboard-group',
            consumer_timeout_ms=5000
        )
        
        from fhir_utils import extract_data_from_fhir
        while True:
            try:
                message_batch = consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        fhir_observation = message.value
                        extracted_data = extract_data_from_fhir(fhir_observation)
                        
                        dashboard_data = {
                            'timestamp': extracted_data['timestamp'],
                            'patient_id': extracted_data['patient_id'],
                            'systolic': extracted_data['systolic'],
                            'diastolic': extracted_data['diastolic'],
                            'heart_rate': extracted_data['heart_rate'],
                            'status': extracted_data['category'],
                            'device_id': extracted_data['device_id']
                        }
                        
                        latest_data.append(dashboard_data)
                        if len(latest_data) > max_data_points:
                            latest_data.pop(0)
            except Exception:
                continue
                
    except Exception:
        pass

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if verify_password(email, password):
            session['user_email'] = email
            session['user_logged_in'] = True
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect', 'error')
    
    # Si déjà connecté, rediriger vers le dashboard
    if 'user_email' in session:
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Page principale du dashboard"""
    user = get_current_user()
    return render_template('dashboard.html', user=user)

@app.route('/api/data')
@login_required
def get_data():
    """API endpoint pour récupérer les données avec filtres optionnels"""
    from flask import request
    
    # Récupérer les paramètres de filtre
    patient_id_filter = request.args.get('patient_id', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    
    file_data = load_data_from_file()
    
    # Appliquer les filtres si fournis
    if patient_id_filter or date_from or date_to:
        filtered_data = []
        for item in file_data:
            # Filtre patient_id
            if patient_id_filter and item.get('patient_id', '').upper() != patient_id_filter.upper():
                continue
            
            # Filtre date
            if date_from or date_to:
                try:
                    item_timestamp = pd.to_datetime(item.get('timestamp', ''))
                    if date_from:
                        from_date = pd.to_datetime(date_from)
                        if item_timestamp < from_date:
                            continue
                    if date_to:
                        to_date = pd.to_datetime(date_to)
                        if item_timestamp > to_date:
                            continue
                except:
                    continue
            
            filtered_data.append(item)
        file_data = filtered_data
    
    if latest_data and len(latest_data) > 0:
        realtime_data = latest_data[-10:]
    else:
        if not (patient_id_filter or date_from or date_to):
            all_file_data = load_data_from_file()
            realtime_data = all_file_data[-10:] if len(all_file_data) > 0 else []
        else:
            realtime_data = file_data[-10:] if len(file_data) > 0 else []
    
    # Appliquer les filtres aux données temps réel aussi
    if patient_id_filter or date_from or date_to:
        filtered_realtime = []
        for item in realtime_data:
            if patient_id_filter and item.get('patient_id', '').upper() != patient_id_filter.upper():
                continue
            if date_from or date_to:
                try:
                    item_timestamp = pd.to_datetime(item.get('timestamp', ''))
                    if date_from:
                        from_date = pd.to_datetime(date_from)
                        if item_timestamp < from_date:
                            continue
                    if date_to:
                        to_date = pd.to_datetime(date_to)
                        if item_timestamp > to_date:
                            continue
                except:
                    continue
            filtered_realtime.append(item)
        realtime_data = filtered_realtime
    
    filtered_stats = get_statistics_from_data(file_data)
    
    return jsonify({
        'file_data': file_data[-50:] if len(file_data) > 0 else [],
        'realtime_data': realtime_data,
        'statistics': filtered_stats,
        'all_patients': sorted(list(set([item.get('patient_id', '') for item in load_data_from_file() if item.get('patient_id')])))
    })

@app.route('/api/statistics')
@login_required
def get_stats():
    """API endpoint pour les statistiques"""
    return jsonify(get_statistics())

@app.route('/api/realtime')
@login_required
def get_realtime():
    """API endpoint pour les données en temps réel"""
    return jsonify(latest_data[-20:])

@app.route('/predictions')
@login_required
def predictions_page():
    """Page des prédictions ML"""
    user = get_current_user()
    return render_template('predictions.html', user=user)

@app.route('/api/predictions')
@login_required
def get_predictions():
    """API endpoint pour récupérer les prédictions ML"""
    patient_id = request.args.get('patient_id', '').strip()
    
    predictor = get_predictor()
    
    if not predictor.models_loaded:
        return jsonify({
            'error': 'Modèles ML non chargés',
            'predictions': []
        }), 500
    
    if patient_id:
        # Prédiction pour un patient spécifique
        prediction = predictor.predict(patient_id)
        if prediction:
            return jsonify({
                'predictions': [prediction],
                'total': 1
            })
        else:
            return jsonify({
                'error': f'Pas assez d\'observations pour {patient_id} (besoin de {30} minimum)',
                'predictions': []
            }), 400
    else:
        # Prédictions pour tous les patients
        predictions = predictor.predict_all_patients()
        
        # Calculer les statistiques globales basées sur alert_level
        if predictions:
            critical_count = sum(1 for p in predictions if p['alert_level'] == 'critical')
            high_count = sum(1 for p in predictions if p['alert_level'] == 'high')
            medium_count = sum(1 for p in predictions if p['alert_level'] == 'medium')
            low_count = sum(1 for p in predictions if p['alert_level'] == 'low')
            critical_alerts = sum(1 for p in predictions if p['alert_level'] in ['critical', 'high'])
            
            stats = {
                'total_patients': len(predictions),
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
                'critical_alerts': critical_alerts
            }
        else:
            stats = {
                'total_patients': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'critical_alerts': 0
            }
        
        return jsonify({
            'predictions': predictions,
            'statistics': stats,
            'total': len(predictions)
        })

@app.route('/api/alerts')
@login_required
def get_alerts():
    """API endpoint pour récupérer les alertes (patients à risque élevé)"""
    predictor = get_predictor()
    
    if not predictor.models_loaded:
        return jsonify({'alerts': []})
    
    predictions = predictor.predict_all_patients()
    
    # Filtrer seulement les alertes critiques et élevées
    alerts = [
        p for p in predictions 
        if p['alert_level'] in ['critical', 'high']
    ]
    
    # Trier par risque décroissant
    alerts.sort(key=lambda x: x['critical_risk_6h'], reverse=True)
    
    return jsonify({
        'alerts': alerts,
        'total': len(alerts)
    })

if __name__ == '__main__':
    kafka_thread = threading.Thread(target=kafka_consumer_thread, daemon=True)
    kafka_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)

"""
Module d'authentification pour le dashboard
Gère l'authentification des utilisateurs avec fichier JSON
"""

import json
import os
import bcrypt
from functools import wraps
from flask import session, redirect, url_for, request

# Dossier pour les données
DATA_DIR = '/app/data' if os.path.exists('/app/data') else './data'
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, 'users.json')


def load_users():
    """Charge les utilisateurs depuis le fichier JSON"""
    if not os.path.exists(USERS_FILE):
        return {}
    
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convertir la liste en dictionnaire pour accès rapide
            users = {}
            for user in data.get('users', []):
                users[user['email']] = {
                    'username': user.get('username', user['email']),
                    'password_hash': user['password_hash'],
                    'role': user.get('role', 'user')
                }
            return users
    except Exception as e:
        pass  # Error loading users (silent)
        return {}


def verify_password(email, password):
    """
    Vérifie si l'email et le mot de passe correspondent
    
    Args:
        email: Email de l'utilisateur
        password: Mot de passe en clair
    
    Returns:
        True si les credentials sont corrects, False sinon
    """
    users = load_users()
    
    if email not in users:
        return False
    
    password_hash = users[email]['password_hash']
    
    # Vérifier le mot de passe avec bcrypt
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        pass  # Error verifying password (silent)
        return False


def hash_password(password):
    """
    Hash un mot de passe avec bcrypt
    
    Args:
        password: Mot de passe en clair
    
    Returns:
        Hash du mot de passe
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def login_required(f):
    """
    Décorateur pour protéger les routes nécessitant une authentification
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Retourne les informations de l'utilisateur connecté"""
    if 'user_email' not in session:
        return None
    
    users = load_users()
    email = session['user_email']
    
    if email in users:
        return {
            'email': email,
            'username': users[email]['username'],
            'role': users[email]['role']
        }
    
    return None

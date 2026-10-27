"""
Script pour créer le fichier users.json avec les utilisateurs
À exécuter une seule fois pour initialiser les utilisateurs
"""

import json
import bcrypt
import os

# Dossier pour les données
DATA_DIR = './data'
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# Comptes de démonstration (le mot de passe n'est jamais stocké dans le dépôt)
# Il est lu dans la variable d'environnement DEMO_PASSWORD, ou demandé au lancement.
from getpass import getpass

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD") or getpass("Mot de passe des comptes de démo : ")

users_data = [
    {"email": "admin@example.com", "username": "admin", "password": DEMO_PASSWORD, "role": "admin"},
    {"email": "user@example.com", "username": "user", "password": DEMO_PASSWORD, "role": "user"},
]

def hash_password(password):
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# Créer la structure avec les hashs
users_json = {
    "users": []
}

for user in users_data:
    users_json["users"].append({
        "email": user["email"],
        "username": user["username"],
        "password_hash": hash_password(user["password"]),
        "role": user["role"]
    })

# Sauvegarder dans le fichier JSON
with open(USERS_FILE, 'w', encoding='utf-8') as f:
    json.dump(users_json, f, indent=2, ensure_ascii=False)

print(f"Fichier users.json cree avec {len(users_data)} utilisateurs")
print(f"Fichier: {USERS_FILE}")
print("\nUtilisateurs crees:")
for user in users_data:
    print(f"  - {user['email']} ({user['username']}) - Role: {user['role']}")

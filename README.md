# 🖨 Maker Mind — Site d'Impression 3D

## Structure des fichiers

```
maker_mind/
├── app.py                  ← Routes Flask & logique admin
├── models.py               ← Base de données SQLAlchemy
├── requirements.txt        ← Dépendances Python
├── templates/
│   ├── index.html          ← Page d'accueil (responsive)
│   ├── admin_login.html    ← Page de connexion admin
│   └── admin.html          ← Dashboard administrateur
└── static/
    └── uploads/            ← Images produits & fichiers clients (auto-créé)
```

## 🚀 Installation & Lancement

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer le serveur
python app.py

# 3. Ouvrir dans le navigateur
# Site : http://localhost:5000
# Admin : http://localhost:5000/admin
```

## 🔐 Accès Admin

- **URL** : `http://localhost:5000/admin`
- **Identifiant** : `admin`
- **Mot de passe** : `makermind2024`

> Modifier ces valeurs dans `app.py` (lignes ADMIN_USERNAME / ADMIN_PASSWORD)

## ✨ Fonctionnalités

### Page d'accueil
- Grille produits responsive (2 cols mobile → 4 cols PC)
- Filtres par catégorie (Figurines, Porte-clefs, Trophées)
- Formulaire de commande personnalisée avec upload de fichier
- Suivi de commande par ID (en temps réel via fetch)

### Dashboard Admin
- Statistiques live (total, en attente, en impression, acceptées)
- Tableau des commandes avec actions : Accepter / Refuser / Mettre en impression / Terminer
- Gestion des produits (ajout + suppression)
- Recherche dans les tableaux
- Sidebar responsive avec menu mobile

## 🎨 Design

- **Couleurs** : Noir `#0a0a0a`, Blanc `#f5f5f5`, Violet électrique `#7c3aed`
- **Fonts** : Syne (titres) + DM Sans (corps)
- **Mobile-First** : Testé sur iPhone, Samsung, iPad, PC

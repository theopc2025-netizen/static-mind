from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'products'
    id          = db.Column(db.Integer, primary_key=True)
    nom         = db.Column(db.String(200), nullable=False)
    prix        = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, default='')
    categorie   = db.Column(db.String(100), default='Figurines')
    image       = db.Column(db.String(300), nullable=True)
    notes       = db.Column(db.Text, default='')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Product {self.nom}>'
class Categorie(db.Model):
    __tablename__ = 'categories'
    id   = db.Column(db.Integer, primary_key=True)
    nom  = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f'<Categorie {self.nom}>'
class Order(db.Model):
    __tablename__ = 'orders'
    id          = db.Column(db.Integer, primary_key=True)
    nom_client  = db.Column(db.String(200), nullable=False)
    email       = db.Column(db.String(200), nullable=True)
    details     = db.Column(db.Text, nullable=False)
    fichier     = db.Column(db.String(300), nullable=True)
    statut      = db.Column(db.String(50), default='En attente')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Order #{self.id} — {self.nom_client}>'

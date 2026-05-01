from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Product, Order, Categorie
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'static_mind_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///makermind.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'stl', 'obj', 'pdf'}
ADMIN_USERNAME = 'Theo'
ADMIN_PASSWORD = 'StaticMind2026'

db.init_app(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def create_tables():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─── PUBLIC ROUTES ───────────────────────────────────────────────

@app.route('/')
def index():
    products = Product.query.order_by(Product.id.desc()).all()
    categories = Categorie.query.order_by(Categorie.id).all()
    return render_template('index.html', products=products, categories=categories)

@app.route('/commande', methods=['POST'])
def passer_commande():
    nom = request.form.get('nom')
    email = request.form.get('email')
    details = request.form.get('details')
    fichier_path = None

    if 'fichier' in request.files:
        fichier = request.files['fichier']
        if fichier and fichier.filename and allowed_file(fichier.filename):
            filename = secure_filename(fichier.filename)
            fichier.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            fichier_path = filename

    order = Order(
        nom_client=nom,
        email=email,
        details=details,
        fichier=fichier_path,
        statut='En attente'
    )
    db.session.add(order)
    db.session.commit()
    flash(f'Commande #{order.id} soumise avec succès !', 'success')
    return redirect(url_for('index'))

@app.route('/suivi', methods=['POST'])
def suivi_commande():
    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)
    if order:
        return jsonify({
            'found': True,
            'id': order.id,
            'nom': order.nom_client,
            'statut': order.statut,
            'details': order.details
        })
    return jsonify({'found': False})

# ─── ADMIN ROUTES ────────────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Identifiants incorrects', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    orders = Order.query.order_by(Order.id.desc()).all()
    products = Product.query.order_by(Product.id.desc()).all()
    stats = {
        'total': Order.query.count(),
        'attente': Order.query.filter_by(statut='En attente').count(),
        'impression': Order.query.filter_by(statut='En impression').count(),
        'accepte': Order.query.filter_by(statut='Accepté').count(),
        'livraison': Order.query.filter_by(statut='En livraison').count(),
    }
    categories = Categorie.query.order_by(Categorie.id).all()
    return render_template('admin.html', orders=orders, products=products, stats=stats, categories=categories)

@app.route('/admin/commande/<int:order_id>/<action>')
def update_order(order_id, action):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    order = Order.query.get_or_404(order_id)
    statuts = {
        'accepter': 'Accepté',
        'refuser': 'Refusé',
        'imprimer': 'En impression',
        'terminer': 'Terminé',
        'delivery': 'En livraison',
        'attente': 'En attente'
    }
    if action == 'supprimer':
        db.session.delete(order)
        db.session.commit()
        flash(f'Commande #{order_id} supprimée.', 'success')
        return redirect(url_for('admin_dashboard'))
    if action in statuts:
        order.statut = statuts[action]
        db.session.commit()
        flash(f'Commande #{order_id} mise à jour : {statuts[action]}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/produit/ajouter', methods=['POST'])
def ajouter_produit():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    nom = request.form.get('nom')
    prix = request.form.get('prix')
    description = request.form.get('description')
    categorie = request.form.get('categorie')
    image_path = None

    if 'image' in request.files:
        image = request.files['image']
        if image and image.filename and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = filename

    product = Product(
        nom=nom,
        prix=float(prix),
        description=description,
        categorie=categorie,
        image=image_path
    )
    db.session.add(product)
    db.session.commit()
    flash(f'Produit "{nom}" ajouté avec succès !', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/produit/supprimer/<int:product_id>')
def supprimer_produit(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Produit supprimé.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))
@app.route('/admin/categorie/ajouter', methods=['POST'])
def ajouter_categorie():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    nom = request.form.get('nom')
    if nom and not Categorie.query.filter_by(nom=nom).first():
        db.session.add(Categorie(nom=nom))
        db.session.commit()
        flash(f'Catégorie "{nom}" ajoutée !', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/categorie/supprimer/<int:cat_id>')
def supprimer_categorie(cat_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    cat = Categorie.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    flash(f'Catégorie supprimée.', 'success')
    return redirect(url_for('admin_dashboard'))
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

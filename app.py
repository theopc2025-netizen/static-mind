from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Product, Order, Categorie
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'static_mind_secret_key_2026'
import os
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///makermind.db')
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

@app.route('/order', methods=['POST'])
def place_order():
    name = request.form.get('nom')
    email = request.form.get('email')
    details = request.form.get('details')
    file_path = None

    if 'fichier' in request.files:
        file = request.files['fichier']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_path = filename

    order = Order(
        nom_client=name,
        email=email,
        details=details,
        fichier=file_path,
        statut='Pending'
    )
    db.session.add(order)
    db.session.commit()
    flash(f'Order #{order.id} submitted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/track', methods=['POST'])
def track_order():
    order_id = request.form.get('order_id')
    order = Order.query.get(order_id)
    if order:
        return jsonify({
            'found': True,
            'id': order.id,
            'name': order.nom_client,
            'status': order.statut,
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
        flash('Incorrect credentials', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    orders = Order.query.order_by(Order.id.desc()).all()
    products = Product.query.order_by(Product.id.desc()).all()
    stats = {
        'total': Order.query.count(),
        'pending': Order.query.filter_by(statut='Pending').count(),
        'printing': Order.query.filter_by(statut='Printing').count(),
        'accepted': Order.query.filter_by(statut='Accepted').count(),
        'delivery': Order.query.filter_by(statut='Out for Delivery').count(),
    }
    categories = Categorie.query.order_by(Categorie.id).all()
    return render_template('admin.html', orders=orders, products=products, stats=stats, categories=categories)

@app.route('/admin/order/<int:order_id>/<action>')
def update_order(order_id, action):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    order = Order.query.get_or_404(order_id)
    statuses = {
        'accept':   'Accepted',
        'reject':   'Rejected',
        'print':    'Printing',
        'complete': 'Completed',
        'delivery': 'Out for Delivery',
        'pending':  'Pending'
    }
    if action == 'delete':
        db.session.delete(order)
        db.session.commit()
        flash(f'Order #{order_id} deleted.', 'success')
        return redirect(url_for('admin_dashboard'))
    if action in statuses:
        order.statut = statuses[action]
        db.session.commit()
        flash(f'Order #{order_id} updated: {statuses[action]}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/add', methods=['POST'])
def add_product():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    name = request.form.get('nom')
    price = request.form.get('prix')
    description = request.form.get('description')
    category = request.form.get('categorie')
    image_path = None

    if 'image' in request.files:
        image = request.files['image']
        if image and image.filename and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = filename

    product = Product(
        nom=name,
        prix=float(price),
        description=description,
        categorie=category,
        image=image_path
    )
    db.session.add(product)
    db.session.commit()
    flash(f'Product "{name}" added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/delete/<int:product_id>')
def delete_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/category/add', methods=['POST'])
def add_category():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    name = request.form.get('nom')
    if name and not Categorie.query.filter_by(nom=name).first():
        db.session.add(Categorie(nom=name))
        db.session.commit()
        flash(f'Category "{name}" added!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/category/delete/<int:cat_id>')
def delete_category(cat_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    cat = Categorie.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    flash('Category deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
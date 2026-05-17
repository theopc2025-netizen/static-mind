from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Product, Order, Categorie, Coupon, Avis, Filament
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_local')

database_url = os.environ.get('DATABASE_URL', 'sqlite:///makermind.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'stl', 'obj', 'pdf'}
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

def send_telegram(message):
    try:
        import urllib.request, json
        TOKEN = os.environ.get('TELEGRAM_TOKEN')
        CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
        data = json.dumps({'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req)
        print('Telegram sent!')
    except Exception as e:
        print(f'Telegram error: {e}')

def send_notification(order_id, name, details, email):
    send_telegram(
        f"🛒 <b>New Order #{order_id}!</b>\n"
        f"👤 <b>Name:</b> {name}\n"
        f"📞 <b>Contact:</b> {email or 'Not provided'}\n"
        f"📝 <b>Details:</b> {details[:200]}"
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

@app.before_request
def create_tables():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE products ADD COLUMN notes TEXT DEFAULT ''"))
            conn.commit()
    except:
        pass
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE products ADD COLUMN needs_text BOOLEAN DEFAULT FALSE"))
            conn.commit()
    except:
        pass
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE products ADD COLUMN double_color BOOLEAN DEFAULT FALSE"))
            conn.commit()
    except:
        pass
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE coupons ADD COLUMN one_time BOOLEAN DEFAULT FALSE"))
            conn.execute(db.text("ALTER TABLE coupons ADD COLUMN used BOOLEAN DEFAULT FALSE"))
            conn.execute(db.text("ALTER TABLE coupons ADD COLUMN product_id INTEGER REFERENCES products(id)"))
            conn.commit()
    except:
        pass

# ─── PUBLIC ROUTES ───────────────────────────────────────────────

@app.route('/')
def index():
    products = Product.query.order_by(Product.id.desc()).all()
    categories = Categorie.query.order_by(Categorie.id).all()
    avis = Avis.query.filter_by(approuve=True).order_by(Avis.id.desc()).all()
    colors = Filament.query.order_by(Filament.id).all()
    return render_template('index.html', products=products, categories=categories, avis=avis, colors=colors)

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

    import secrets
    order = Order(
        nom_client=name,
        email=email,
        details=details,
        fichier=file_path,
        statut='Pending',
        tracking_code=secrets.token_hex(4).upper() 
    )
    db.session.add(order)
    db.session.commit()
    order_id = order.id
    import threading
    threading.Thread(target=send_notification, args=(order_id, name, details, email)).start()
    order_id_display = str(order_id).zfill(3)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'order_id': order_id_display, 'tracking_code': order.tracking_code})
    flash(f'Order #{order_id_display} submitted successfully! Tracking code: {order.tracking_code}', 'success')
    return redirect(url_for('index'))

@app.route('/track', methods=['POST'])
def track_order():
    code = request.form.get('order_id', '').strip().upper()
    order = Order.query.filter_by(tracking_code=code).first()
    if not order:
        try:
            order = Order.query.get(int(code))
        except:
            pass
    if order:
        return jsonify({
            'found': True,
            'id': str(order.id).zfill(3),
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
    coupons = Coupon.query.order_by(Coupon.id.desc()).all()
    tous_avis = Avis.query.order_by(Avis.id.desc()).all()
    filaments = Filament.query.order_by(Filament.id).all()
    return render_template('admin.html', orders=orders, products=products, stats=stats, categories=categories, coupons=coupons, tous_avis=tous_avis, filaments=filaments)

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
        image=image_path,
        notes=request.form.get('notes', '')
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

@app.route('/admin/product/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    product = Product.query.get_or_404(product_id)
    product.nom = request.form.get('nom')
    product.prix = float(request.form.get('prix'))
    product.description = request.form.get('description')
    product.categorie = request.form.get('categorie')
    product.notes = request.form.get('notes')
    product.needs_text = request.form.get('needs_text') == 'on'
    db.session.commit()
    flash(f'Product updated!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/category/edit/<int:cat_id>', methods=['POST'])
def edit_category(cat_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    cat = Categorie.query.get_or_404(cat_id)
    cat.nom = request.form.get('nom')
    db.session.commit()
    flash('Category updated!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset-orders', methods=['POST'])
def reset_orders():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    deleted = Order.query.filter_by(statut='Completed').delete()
    db.session.commit()
    flash(f'{deleted} completed order(s) deleted.', 'success')
    return redirect(url_for('admin_dashboard'))
@app.route('/check-coupon', methods=['POST'])
def check_coupon():
    code = request.form.get('code', '').strip().upper()
    product_id = request.form.get('product_id')
    coupon = Coupon.query.filter_by(code=code, actif=True).first()
    if not coupon:
        return jsonify({'valid': False, 'reason': 'invalid'})
    if coupon.one_time and coupon.used:
        return jsonify({'valid': False, 'reason': 'used'})
    if coupon.product_id and product_id:
        if str(coupon.product_id) != str(product_id):
            return jsonify({'valid': False, 'reason': 'wrong_product'})
    if coupon.one_time:
        coupon.used = True
        db.session.commit()
    return jsonify({'valid': True, 'reduction': coupon.reduction, 'code': coupon.code, 'product_id': coupon.product_id})

@app.route('/admin/coupon/add', methods=['POST'])
def add_coupon():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    code = request.form.get('code', '').strip().upper()
    reduction = float(request.form.get('reduction', 0))
    one_time = request.form.get('one_time') == 'on'
    product_id = request.form.get('product_id') or None
    if product_id:
        product_id = int(product_id)
    if code and not Coupon.query.filter_by(code=code).first():
        db.session.add(Coupon(code=code, reduction=reduction, one_time=one_time, product_id=product_id))
        db.session.commit()
        flash(f'Coupon "{code}" added!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/coupon/delete/<int:coupon_id>')
def delete_coupon(coupon_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    c = Coupon.query.get_or_404(coupon_id)
    db.session.delete(c)
    db.session.commit()
    flash('Coupon deleted.', 'success')
    return redirect(url_for('admin_dashboard'))
@app.route('/avis', methods=['POST'])
def submit_avis():
    nom = request.form.get('nom')
    etoiles = int(request.form.get('etoiles', 5))
    texte = request.form.get('texte')
    if nom and texte:
        db.session.add(Avis(nom=nom, etoiles=etoiles, texte=texte))
        db.session.commit()
        flash('Thank you for your feedback! It will be published after a few minutes.', 'success')
    return redirect(url_for('index'))

@app.route('/admin/avis/<int:avis_id>/<action>')
def manage_avis(avis_id, action):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    a = Avis.query.get_or_404(avis_id)
    if action == 'approve':
        a.approuve = True
        db.session.commit()
        flash('Avis approuvé!', 'success')
    elif action == 'delete':
        db.session.delete(a)
        db.session.commit()
        flash('Avis supprimé.', 'success')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/filament/add', methods=['POST'])
def add_filament():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    nom = request.form.get('nom')
    hex_color = request.form.get('hex', '#ffffff')
    if nom:
        db.session.add(Filament(nom=nom, hex=hex_color))
        db.session.commit()
        flash(f'Color "{nom}" added!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/filament/delete/<int:fid>')
def delete_filament(fid):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    f = Filament.query.get_or_404(fid)
    db.session.delete(f)
    db.session.commit()
    flash('Color deleted.', 'success')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/product/filaments/<int:product_id>', methods=['POST'])
def set_product_filaments(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    product = Product.query.get_or_404(product_id)
    selected_ids = request.form.getlist('filament_ids')
    product.filaments = Filament.query.filter(Filament.id.in_([int(i) for i in selected_ids])).all()
    db.session.commit()
    flash('Colors updated!', 'success')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/product/set-double-color', methods=['POST'])
def set_double_color():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_ids = request.form.getlist('product_ids')
    for product in Product.query.all():
        product.double_color = str(product.id) in selected_ids
    try:
        db.session.commit()
        flash('Double color products updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/product/set-customizable', methods=['POST'])
def set_customizable():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_ids = request.form.getlist('product_ids')
    for product in Product.query.all():
        product.customizable = str(product.id) in selected_ids
    db.session.commit()
    flash('Customizable products updated!', 'success')
    return redirect(url_for('admin_dashboard'))
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

import os
import uuid
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import get_db

products = Blueprint('products', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied! Admins only.', 'danger')
            return redirect(url_for('auth.home'))
        return f(*args, **kwargs)
    return decorated


def ensure_product_image_column():
    """Adds the image column automatically if the old database does not have it."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS image VARCHAR(255)")
    conn.commit()
    cur.close()
    conn.close()


def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_product_image(file):
    """Save uploaded product image and return its static path, e.g. uploads/products/img.jpg."""
    if not file or file.filename == '':
        return None

    if not allowed_image(file.filename):
        raise ValueError('Only PNG, JPG, JPEG, WEBP and GIF images are allowed.')

    original_name = secure_filename(file.filename)
    extension = original_name.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"

    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'products')
    os.makedirs(upload_dir, exist_ok=True)

    file.save(os.path.join(upload_dir, filename))
    return f"uploads/products/{filename}"


# ── User: view & search products ────────────────────────
@products.route('/products')
def product_list():
    ensure_product_image_column()
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT id, name, description, price, stock, category, image FROM products WHERE 1=1"
    params = []
    if search:
        query += " AND name ILIKE %s"
        params.append(f'%{search}%')
    if category:
        query += " AND category = %s"
        params.append(category)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    items = cur.fetchall()
    cur.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL")
    categories = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template('products.html', products=items,
                           search=search, categories=categories,
                           selected_category=category)


@products.route('/products/<int:product_id>')
def product_detail(product_id):
    ensure_product_image_column()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description, price, stock, category, image FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.product_list'))
    return render_template('product_detail.html', product=product)


# ── Admin: manage products ───────────────────────────────
@products.route('/admin/products')
@login_required
@admin_required
def admin_products():
    ensure_product_image_column()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, stock, category, image FROM products ORDER BY created_at DESC")
    items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_products.html', products=items)


@products.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    ensure_product_image_column()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        stock = request.form['stock']
        category = request.form['category']

        try:
            image_path = save_product_image(request.files.get('image'))
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('product_form.html', product=None, action='Add')

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, description, price, stock, category, image) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, description, price, stock, category, image_path)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products.admin_products'))
    return render_template('product_form.html', product=None, action='Add')


@products.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    ensure_product_image_column()
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        stock = request.form['stock']
        category = request.form['category']

        cur.execute("SELECT image FROM products WHERE id = %s", (product_id,))
        existing = cur.fetchone()
        image_path = existing[0] if existing else None

        try:
            uploaded_image = save_product_image(request.files.get('image'))
            if uploaded_image:
                image_path = uploaded_image
        except ValueError as e:
            flash(str(e), 'danger')
            cur.execute("SELECT id, name, description, price, stock, category, image FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()
            cur.close()
            conn.close()
            return render_template('product_form.html', product=product, action='Edit')

        cur.execute(
            "UPDATE products SET name=%s, description=%s, price=%s, stock=%s, category=%s, image=%s WHERE id=%s",
            (name, description, price, stock, category, image_path, product_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products.admin_products'))

    cur.execute("SELECT id, name, description, price, stock, category, image FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('product_form.html', product=product, action='Edit')


@products.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Product deleted.', 'success')
    return redirect(url_for('products.admin_products'))

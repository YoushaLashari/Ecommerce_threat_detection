from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import get_db

cart = Blueprint('cart', __name__)

@cart.route('/cart')
@login_required
def view_cart():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT cart.id, products.name, products.price, cart.quantity, products.id
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (current_user.id,))
    items = cur.fetchall()
    cur.close()
    conn.close()
    total = sum(row[2] * row[3] for row in items)
    return render_template('cart.html', items=items, total=total)

@cart.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, quantity FROM cart WHERE user_id = %s AND product_id = %s",
                (current_user.id, product_id))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = %s", (existing[0],))
    else:
        cur.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, 1)",
                    (current_user.id, product_id))
    conn.commit()
    cur.close()
    conn.close()
    flash('Added to cart!')
    return redirect(url_for('products.product_detail', product_id=product_id))

@cart.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM cart WHERE id = %s AND user_id = %s", (item_id, current_user.id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('cart.view_cart'))

@cart.route('/cart/update/<int:item_id>/<int:qty>')
@login_required
def update_quantity(item_id, qty):
    conn = get_db()
    cur = conn.cursor()
    if qty <= 0:
        cur.execute("DELETE FROM cart WHERE id = %s AND user_id = %s", (item_id, current_user.id))
    else:
        cur.execute("UPDATE cart SET quantity = %s WHERE id = %s AND user_id = %s",
                    (qty, item_id, current_user.id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('cart.view_cart'))
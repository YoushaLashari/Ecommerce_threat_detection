from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import get_db

orders = Blueprint('orders', __name__)


@orders.route('/checkout')
@login_required
def checkout():
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

    if not items:
        flash('Your cart is empty. Add items before checking out.', 'warning')
        return redirect(url_for('cart.view_cart'))

    total = sum(row[2] * row[3] for row in items)
    return render_template('checkout.html', items=items, total=total)


@orders.route('/checkout/confirm', methods=['POST'])
@login_required
def confirm_order():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT cart.id, products.id, products.price, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (current_user.id,))
    items = cur.fetchall()

    if not items:
        flash('Your cart is empty.', 'warning')
        cur.close()
        conn.close()
        return redirect(url_for('cart.view_cart'))

    total = sum(row[2] * row[3] for row in items)

    cur.execute(
        "INSERT INTO orders (user_id, total_price, status) VALUES (%s, %s, 'pending') RETURNING id",
        (current_user.id, total)
    )
    order_id = cur.fetchone()[0]

    for item in items:
        cart_id, product_id, price, quantity = item
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
            (order_id, product_id, quantity, price)
        )

    cur.execute("DELETE FROM cart WHERE user_id = %s", (current_user.id,))

    conn.commit()
    cur.close()
    conn.close()

    # Run fraud detection
    from app.modules.fraud import check_fraud
    check_fraud(user_id=current_user.id, order_id=order_id, amount=total)

    flash(f'Order #{order_id} placed! Please complete your payment.', 'success')
    return redirect(url_for('payments.payment', order_id=order_id))


@orders.route('/order/success/<int:order_id>')
@login_required
def order_success(order_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, total_price, status, created_at FROM orders WHERE id = %s AND user_id = %s",
        (order_id, current_user.id)
    )
    order = cur.fetchone()

    cur.execute("""
        SELECT products.name, order_items.quantity, order_items.price
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id = %s
    """, (order_id,))
    items = cur.fetchall()

    cur.close()
    conn.close()

    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('cart.view_cart'))

    return render_template('order_success.html', order=order, items=items)


# ── User: view order history ────────────────────────────
@orders.route('/my-orders')
@login_required
def order_history():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, total_price, status, created_at
        FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (current_user.id,))
    user_orders = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('order_history.html', orders=user_orders)


# ── Admin: view all orders ──────────────────────────────
@orders.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('products.product_list'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT orders.id, users.name, orders.total_price, orders.status, orders.created_at
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.created_at DESC
    """)
    all_orders = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_orders.html', orders=all_orders)


# ── Admin: update order status ──────────────────────────
@orders.route('/admin/orders/update/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('products.product_list'))
    new_status = request.form.get('status')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
    conn.commit()
    cur.close()
    conn.close()
    flash(f'Order #{order_id} status updated to {new_status}.', 'success')
    return redirect(url_for('orders.admin_orders'))
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import get_db
import random

payments = Blueprint('payments', __name__)


@payments.route('/payment/<int:order_id>', methods=['GET', 'POST'])
@login_required
def payment(order_id):
    conn = get_db()
    cur = conn.cursor()

    # Get order details
    cur.execute(
        "SELECT id, total_price, status FROM orders WHERE id = %s AND user_id = %s",
        (order_id, current_user.id)
    )
    order = cur.fetchone()

    if not order:
        flash('Order not found.', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('orders.order_history'))

    # Check if already paid
    cur.execute("SELECT id, status FROM payments WHERE order_id = %s", (order_id,))
    existing_payment = cur.fetchone()

    if existing_payment and existing_payment[1] == 'success':
        flash('This order is already paid.', 'info')
        cur.close()
        conn.close()
        return redirect(url_for('orders.order_history'))

    if request.method == 'POST':
        card_number = request.form.get('card_number', '').replace(' ', '')
        expiry = request.form.get('expiry', '')
        cvv = request.form.get('cvv', '')

        # Basic validation
        if len(card_number) != 16 or not card_number.isdigit():
            flash('Invalid card number. Must be 16 digits.', 'danger')
            cur.close()
            conn.close()
            return render_template('payment.html', order=order)

        if len(cvv) != 3 or not cvv.isdigit():
            flash('Invalid CVV. Must be 3 digits.', 'danger')
            cur.close()
            conn.close()
            return render_template('payment.html', order=order)

        if not expiry or len(expiry) != 5:
            flash('Invalid expiry date. Use MM/YY format.', 'danger')
            cur.close()
            conn.close()
            return render_template('payment.html', order=order)

        # Simulate payment — 90% success rate
        payment_success = random.randint(1, 10) != 1

        if payment_success:
            payment_status = 'success'
            order_status = 'processing'
        else:
            payment_status = 'failed'
            order_status = 'pending'

        # Save payment record
        cur.execute(
            "INSERT INTO payments (order_id, user_id, amount, status) VALUES (%s, %s, %s, %s)",
            (order_id, current_user.id, order[1], payment_status)
        )

        # Update order status if payment succeeded
        if payment_success:
            cur.execute(
                "UPDATE orders SET status = %s WHERE id = %s",
                (order_status, order_id)
            )

        conn.commit()
        cur.close()
        conn.close()

# Run fraud detection
        from app.modules.fraud import check_fraud
        check_fraud(user_id=current_user.id, order_id=order_id, amount=order[1])

        if payment_success:
            flash(f'Payment successful! Order #{order_id} is now being processed.', 'success')
            return redirect(url_for('payments.payment_success', order_id=order_id))
        else:
            flash('Payment failed. Please try again.', 'danger')
            return redirect(url_for('payments.payment_failed', order_id=order_id))

    cur.close()
    conn.close()
    return render_template('payment.html', order=order)


@payments.route('/payment/success/<int:order_id>')
@login_required
def payment_success(order_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, total_price, status FROM orders WHERE id = %s AND user_id = %s",
        (order_id, current_user.id)
    )
    order = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('payment_success.html', order=order)


@payments.route('/payment/failed/<int:order_id>')
@login_required
def payment_failed(order_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, total_price, status FROM orders WHERE id = %s AND user_id = %s",
        (order_id, current_user.id)
    )
    order = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('payment_failed.html', order=order)
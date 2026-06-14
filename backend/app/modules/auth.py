from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import get_db, User
from app import bcrypt
from app.modules.fraud import get_all_alerts, resolve_alert

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, password, 'user')
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            conn.rollback()
            flash('Email already exists!', 'danger')
        finally:
            cur.close()
            conn.close()

    return render_template('register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        row = User.get_by_email(email)

        if row and bcrypt.check_password_hash(row[3], password):
            user = User(id=row[0], name=row[1], email=row[2], role=row[4])
            login_user(user)
            flash('Login successful!', 'success')
            if row[4] == 'admin':
                return redirect(url_for('auth.dashboard'))
            return redirect(url_for('auth.home'))
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('auth.login'))


@auth.route('/')
def home():
    return render_template('home.html')


@auth.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Access denied! Admins only.', 'danger')
        return redirect(url_for('auth.home'))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM payments")
    total_payments = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM fraud_alerts WHERE status = 'open'")
    open_alerts = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template('dashboard.html',
        total_users=total_users,
        total_products=total_products,
        total_orders=total_orders,
        total_payments=total_payments,
        open_alerts=open_alerts
    )


@auth.route('/admin/fraud-alerts')
@login_required
def fraud_alerts():
    if current_user.role != 'admin':
        flash('Access denied! Admins only.', 'danger')
        return redirect(url_for('auth.home'))

    status_filter   = request.args.get('status', 'all')
    severity_filter = request.args.get('severity', 'all')

    alerts = get_all_alerts()

    if status_filter != 'all':
        alerts = [a for a in alerts if a['status'] == status_filter]

    if severity_filter != 'all':
        alerts = [a for a in alerts if a['severity'] == severity_filter]

    return render_template('admin_fraud.html',
        alerts=alerts,
        status_filter=status_filter,
        severity_filter=severity_filter
    )


@auth.route('/admin/fraud-alerts/resolve/<int:alert_id>', methods=['POST'])
@login_required
def resolve_fraud_alert(alert_id):
    if current_user.role != 'admin':
        flash('Access denied! Admins only.', 'danger')
        return redirect(url_for('auth.home'))
    resolve_alert(alert_id)
    flash('Alert marked as resolved.', 'success')
    return redirect(url_for('auth.fraud_alerts'))


@auth.route('/admin/fraud-alerts/resolve-all', methods=['POST'])
@login_required
def resolve_all_alerts():
    if current_user.role != 'admin':
        flash('Access denied! Admins only.', 'danger')
        return redirect(url_for('auth.home'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE fraud_alerts SET status = 'resolved' WHERE status = 'open'")
    conn.commit()
    cur.close()
    conn.close()

    flash('All open alerts have been resolved.', 'success')
    return redirect(url_for('auth.fraud_alerts'))


@auth.route('/profile')
@login_required
def profile():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT o.id, o.total_price, o.status, o.created_at
        FROM orders o
        WHERE o.user_id = %s
        ORDER BY o.created_at DESC
    """, (current_user.id,))
    orders = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('profile.html', orders=orders)


@auth.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form['current_password']
    new_password     = request.form['new_password']
    confirm_password = request.form['confirm_password']

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id = %s", (current_user.id,))
    row = cur.fetchone()

    if not bcrypt.check_password_hash(row[0], current_password):
        flash('Current password is incorrect!', 'danger')
        return redirect(url_for('auth.profile'))

    if new_password != confirm_password:
        flash('New passwords do not match!', 'danger')
        return redirect(url_for('auth.profile'))

    if len(new_password) < 6:
        flash('New password must be at least 6 characters!', 'danger')
        return redirect(url_for('auth.profile'))

    hashed = bcrypt.generate_password_hash(new_password).decode('utf-8')
    cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, current_user.id))
    conn.commit()
    cur.close()
    conn.close()

    flash('Password updated successfully!', 'success')
    return redirect(url_for('auth.profile'))
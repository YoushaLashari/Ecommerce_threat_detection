from app.models import get_db


def check_fraud(user_id, order_id=None, amount=None):
    """
    Runs all fraud rules against the user.
    Call this after every order or payment.
    """
    conn = get_db()
    cur = conn.cursor()
    alerts = []

    # ── Rule 1: Multiple orders within 10 minutes ──────────
    cur.execute("""
        SELECT COUNT(*) FROM orders
        WHERE user_id = %s
        AND created_at >= NOW() - INTERVAL '10 minutes'
    """, (user_id,))
    recent_orders = cur.fetchone()[0]
    if recent_orders >= 3:
        alerts.append({
            "reason": f"Rule 1: User placed {recent_orders} orders within 10 minutes.",
            "severity": "high"
        })

    # ── Rule 2: Multiple failed payments ───────────────────
    cur.execute("""
        SELECT COUNT(*) FROM payments
        WHERE user_id = %s
        AND status = 'failed'
        AND created_at >= NOW() - INTERVAL '30 minutes'
    """, (user_id,))
    failed_payments = cur.fetchone()[0]
    if failed_payments >= 2:
        alerts.append({
            "reason": f"Rule 2: User had {failed_payments} failed payments in 30 minutes.",
            "severity": "high"
        })

    # ── Rule 3: Unusually high transaction amount ───────────
    if amount and float(amount) > 5000:
        alerts.append({
            "reason": f"Rule 3: Unusually high transaction amount of ${amount}.",
            "severity": "medium"
        })

    # ── Rule 4: Too many orders in one day ──────────────────
    cur.execute("""
        SELECT COUNT(*) FROM orders
        WHERE user_id = %s
        AND created_at >= NOW() - INTERVAL '24 hours'
    """, (user_id,))
    daily_orders = cur.fetchone()[0]
    if daily_orders >= 5:
        alerts.append({
            "reason": f"Rule 4: User placed {daily_orders} orders in the last 24 hours.",
            "severity": "medium"
        })

    # ── Save alerts to database ─────────────────────────────
    for alert in alerts:
        cur.execute("""
            SELECT id FROM fraud_alerts
            WHERE user_id = %s AND reason = %s
            AND created_at >= NOW() - INTERVAL '1 hour'
        """, (user_id, alert["reason"]))
        existing = cur.fetchone()
        if not existing:
            cur.execute(
                "INSERT INTO fraud_alerts (user_id, reason, severity, status) VALUES (%s, %s, %s, 'open')",
                (user_id, alert["reason"], alert["severity"])
            )

    conn.commit()
    cur.close()
    conn.close()
    return alerts


def get_all_alerts():
    """
    Fetch all fraud alerts with user info for the admin panel.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT fa.id, u.name, u.email, fa.reason, fa.severity, fa.status, fa.created_at
        FROM fraud_alerts fa
        JOIN users u ON fa.user_id = u.id
        ORDER BY fa.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    alerts = []
    for row in rows:
        alerts.append({
            "id":         row[0],
            "user_name":  row[1],
            "user_email": row[2],
            "reason":     row[3],
            "severity":   row[4],
            "status":     row[5],
            "created_at": row[6]
        })
    return alerts


def resolve_alert(alert_id):
    """
    Mark a fraud alert as resolved.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE fraud_alerts SET status = 'resolved' WHERE id = %s",
        (alert_id,)
    )
    conn.commit()
    cur.close()
    conn.close()
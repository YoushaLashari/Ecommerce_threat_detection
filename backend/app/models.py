import psycopg2
from urllib.parse import urlparse
from flask_login import UserMixin
from app.config import Config

def get_db():
    # Railway provides a single DATABASE_URL
    if Config.DATABASE_URL:
        result = urlparse(Config.DATABASE_URL)
        conn = psycopg2.connect(
            host=result.hostname,
            port=result.port,
            dbname=result.path[1:],  # removes leading "/"
            user=result.username,
            password=result.password
        )
    else:
        # Local development fallback
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
    return conn

class User(UserMixin):
    def __init__(self, id, name, email, role):
        self.id = id
        self.name = name
        self.email = email
        self.role = role

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return User(id=row[0], name=row[1], email=row[2], role=row[3])
        return None

    @staticmethod
    def get_by_email(email):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, password, role FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row
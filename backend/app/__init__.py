from flask import Flask, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta

bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object('app.config.Config')

    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    limiter.init_app(app)

    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))

    from app.modules.auth import auth
    app.register_blueprint(auth)

    from app.modules.products import products
    app.register_blueprint(products)

    from app.modules.cart import cart
    app.register_blueprint(cart)

    from app.modules.orders import orders
    app.register_blueprint(orders)

    from app.modules.payments import payments
    app.register_blueprint(payments)

    return app
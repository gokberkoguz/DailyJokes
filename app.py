import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_apscheduler import APScheduler
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
mail = Mail()
scheduler = APScheduler()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Basic config
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Mail config
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('GMAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('GMAIL_APP_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('GMAIL_USERNAME')

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    scheduler.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.admin_login'

    @login_manager.user_loader
    def load_user(user_id):
        from models import Admin
        return Admin.query.get(int(user_id))

    with app.app_context():
        from models import Admin, Subscriber, Joke
        db.create_all()

        # Create default admin if not exists
        if not Admin.query.first():
            admin = Admin(username='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()

    # Register blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)

    return app

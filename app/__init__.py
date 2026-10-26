import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv()
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins=[])

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "connectly.db")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "webp"}
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app, cors_allowed_origins=[])

    from .models import User
    from .routes import main
    from . import chat_events
    app.register_blueprint(main)

    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    with app.app_context():
        db.create_all()

    return app

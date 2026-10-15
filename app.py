from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db, bcrypt, User
from routes.auth import auth_bp
from routes.guest import guest_bp
from routes.reception import reception_bp
from routes.staff import staff_bp
from routes.admin import admin_bp
from routes.chat import chat_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(guest_bp)
    app.register_blueprint(reception_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)

    with app.app_context():
        db.create_all()
        # Auto-seed if database is empty (e.g. fresh Render deployment)
        if User.query.count() == 0:
            from seed import seed_db
            seed_db()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)

import os
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import LoginManager
from models import db, User, Slot, Station, Branch
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'src', 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static'
)
app.secret_key = os.environ.get('SECRET_KEY', 'ev_secret_key')
app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# =========================
# Database Config
# =========================
# IMPORTANT: Vercel's serverless filesystem is READ-ONLY (except /tmp, which
# is wiped after every request). SQLite files cannot persist there, and
# concurrent/multiple users would each hit a different, empty database.
# So in production we use a hosted Postgres database (e.g. Neon) via
# DATABASE_URL. Locally, if DATABASE_URL isn't set, we fall back to SQLite
# so you can still develop on your machine.
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Neon/Heroku-style URLs sometimes start with postgres:// — SQLAlchemy
    # needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    instance_db_path = os.path.join(instance_dir, 'database.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{instance_db_path}"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,   # avoids "server closed the connection" errors
    'pool_recycle': 280,     # recycle before Neon/serverless idle timeout
}
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

# =========================
# Login Manager
# =========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "user.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# Register Blueprints
# =========================
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)

# =========================
# Create tables (safe to call on every cold start — no-ops if they exist)
# =========================
with app.app_context():
    db.create_all()


# =========================
# Context Processors
# =========================
@app.context_processor
def inject_google_maps_api_key():
    return {
        'gmaps_api_key': app.config['GOOGLE_MAPS_API_KEY']
    }


# =========================
# Home Route
# =========================
@app.route('/')
def home():
    return render_template("home.html")


# =========================
# Run App (local development only — Vercel uses api/index.py instead)
# =========================
if __name__ == "__main__":
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    app.run(debug=True)
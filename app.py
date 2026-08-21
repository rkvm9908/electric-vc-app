import os
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager
from sqlalchemy import inspect, text
from models import db, User, Slot, Station, Branch
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp

load_dotenv()
app = Flask(__name__, template_folder='src/templates')
app.secret_key = os.environ.get('SECRET_KEY', 'ev_secret_key')
app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# Ensure instance folder exists before opening the database
instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(instance_dir, exist_ok=True)
instance_db_path = os.path.join(instance_dir, 'database.db')

# =========================
# Database Config
# =========================
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{instance_db_path.replace('//', '/') }"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)
migrate = Migrate(app, db)


def ensure_slot_branch_column():
    inspector = inspect(db.engine)
    if 'slots' not in inspector.get_table_names():
        return

    slot_columns = [col['name'] for col in inspector.get_columns('slots')]
    with db.engine.begin() as conn:
        if 'branch_id' not in slot_columns:
            conn.execute(text('ALTER TABLE slots ADD COLUMN branch_id INTEGER'))
        if 'branch_name' not in slot_columns:
            conn.execute(text('ALTER TABLE slots ADD COLUMN branch_name VARCHAR(120)'))
        if 'parent_slot_id' not in slot_columns:
            conn.execute(text('ALTER TABLE slots ADD COLUMN parent_slot_id INTEGER'))
        if 'user_id' not in slot_columns:
            conn.execute(text('ALTER TABLE slots ADD COLUMN user_id INTEGER'))
        if 'vehicle_type' not in slot_columns:
            conn.execute(text('ALTER TABLE slots ADD COLUMN vehicle_type VARCHAR(10)'))
        if 'booked_at' not in slot_columns:
            conn.execute(text('ALTER TABLE slots ADD COLUMN booked_at DATETIME'))

    branch_columns = [col['name'] for col in inspector.get_columns('branches')] if 'branches' in inspector.get_table_names() else []
    with db.engine.begin() as conn:
        if 'branches' in inspector.get_table_names():
            if 'slots_2w_total' not in branch_columns:
                conn.execute(text('ALTER TABLE branches ADD COLUMN slots_2w_total INTEGER DEFAULT 0'))
            if 'slots_4w_total' not in branch_columns:
                conn.execute(text('ALTER TABLE branches ADD COLUMN slots_4w_total INTEGER DEFAULT 0'))
            if 'price_2w_per_hour' not in branch_columns:
                conn.execute(text('ALTER TABLE branches ADD COLUMN price_2w_per_hour FLOAT DEFAULT 20.0'))
            if 'price_4w_per_hour' not in branch_columns:
                conn.execute(text('ALTER TABLE branches ADD COLUMN price_4w_per_hour FLOAT DEFAULT 50.0'))
            if 'open_time' not in branch_columns:
                conn.execute(text('ALTER TABLE branches ADD COLUMN open_time TIME'))
            if 'close_time' not in branch_columns:
                conn.execute(text('ALTER TABLE branches ADD COLUMN close_time TIME'))

    # No automatic branch_id assignment for legacy data; keep branch_name available for fallback
    if 'branch_name' in slot_columns:
        missing_slots = Slot.query.filter((Slot._branch_name == None) | (Slot._branch_name == '')).all()
        for slot in missing_slots:
            branch_code = slot.station.branch_code if slot.station else f"BR{slot.station_id:03d}"
            slot._branch_name = f"{branch_code}-{slot.type}-{slot.id:02d}"
        if missing_slots:
            db.session.commit()

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

with app.app_context():
    db.create_all()
    ensure_slot_branch_column()

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
# Run App
# =========================
if __name__ == "__main__":
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    with app.app_context():
        db.create_all()
        ensure_slot_branch_column()
    app.run(debug=True)


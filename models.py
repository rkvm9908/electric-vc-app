from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, time
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    vehicle_no = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='user')  # user/admin
    profile_pic = db.Column(db.String(255), default='default_profile.png')
    bio = db.Column(db.Text, default='Electric Vehicle Enthusiast')

    bookings = db.relationship('Booking', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)


class Station(db.Model):
    __tablename__ = 'stations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)  # Tamil Nadu Area
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    slots = db.relationship('Slot', backref='station', lazy=True)
    bookings = db.relationship('Booking', backref='station', lazy=True)
    feedbacks = db.relationship('Feedback', backref='station', lazy=True)
    branches = db.relationship('Branch', backref='station', lazy=True)

    @property
    def branch_code(self):
        return f"BR{self.id:03d}" if self.id else "BR000"

    @property
    def branch_label(self):
        return f"{self.branch_code} - {self.name}"


class Branch(db.Model):
    __tablename__ = 'branches'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    slots_2w_total = db.Column(db.Integer, default=0)
    slots_4w_total = db.Column(db.Integer, default=0)
    price_2w_per_hour = db.Column(db.Float, default=20.0)
    price_4w_per_hour = db.Column(db.Float, default=50.0)
    open_time = db.Column(db.Time, default=time(6, 0))
    close_time = db.Column(db.Time, default=time(22, 0))

    slots = db.relationship('Slot', backref='branch', lazy=True)

    @property
    def branch_code(self):
        if self.station and self.id:
            return f"{self.station.branch_code}-{self.id:02d}"
        return f"BR000-00"

    @property
    def branch_label(self):
        return f"{self.branch_code} - {self.name}"

    def __repr__(self):
        return f"<Branch {self.name} ({self.location})>"


class Slot(db.Model):
    __tablename__ = 'slots'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=True)
    parent_slot_id = db.Column(db.Integer, db.ForeignKey('slots.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    type = db.Column(db.String(10), nullable=False)  # 2W or 4W
    status = db.Column(db.String(20), default='Available')  # Available, Booked, Occupied, Completed
    vehicle_type = db.Column(db.String(10), nullable=True)
    booked_at = db.Column(db.DateTime, nullable=True)
    _branch_name = db.Column('branch_name', db.String(120), nullable=True)

    parent_slot = db.relationship('Slot', remote_side=[id], backref='child_slots', uselist=False)
    user = db.relationship('User', backref='slots', foreign_keys=[user_id])
    booking = db.relationship('Booking', backref='slot', uselist=False)

    @property
    def branch_name(self):
        if self.branch:
            return self.branch.name
        if self._branch_name:
            return self._branch_name
        return self.station.branch_label if self.station else 'Unknown'


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    vehicle_type = db.Column(db.String(10), nullable=False)
    booking_time = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_start = db.Column(db.DateTime, nullable=True)  # Scheduled start time
    scheduled_end = db.Column(db.DateTime, nullable=True)    # Scheduled end time
    total_cost = db.Column(db.Float, nullable=True)          # Total cost for the booking
    status = db.Column(db.String(20), default='Upcoming')  # Upcoming, Completed, Cancelled

    @property
    def booking_reference(self):
        source_time = self.booking_time or datetime.utcnow()
        return f"BK-{self.station_id}-{self.user_id}-{source_time.strftime('%Y%m%d%H%M%S')}"


class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

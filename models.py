from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize the SQLAlchemy object
db = SQLAlchemy()

class Admin(db.Model):
    """Replaces admin_users.csv for secure admin login."""
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Resident(db.Model):
    """Replaces residents.csv to store community members."""
    __tablename__ = 'residents'
    id = db.Column(db.Integer, primary_key=True)
    resident_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone_no = db.Column(db.String(20), nullable=False)
    flat_no = db.Column(db.String(20), nullable=False)
    # Establishes a relationship: One resident can own multiple vehicles
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)

class Vehicle(db.Model):
    """Stores registered vehicles linked to residents."""
    __tablename__ = 'vehicles'
    license_plate = db.Column(db.String(20), primary_key=True)
    resident_id = db.Column(db.String(50), db.ForeignKey('residents.resident_id'), nullable=False)

class VisitorLog(db.Model):
    """Replaces access_granted.csv to track every entry."""
    __tablename__ = 'visitor_logs'
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False) # e.g., 'Resident Entry', 'Visitor OTP Granted'

class Suspect(db.Model):
    """Replaces suspect_list.csv for vehicles failing OTP verification."""
    __tablename__ = 'suspects'
    license_plate = db.Column(db.String(20), primary_key=True)
    failed_attempts = db.Column(db.Integer, default=1)
    last_attempt = db.Column(db.DateTime, default=datetime.utcnow)

class Blacklist(db.Model):
    """Replaces blacklist.csv for permanently banned vehicles."""
    __tablename__ = 'blacklist'
    license_plate = db.Column(db.String(20), primary_key=True)
    reason = db.Column(db.String(200), nullable=False) # e.g., 'Failed OTP 3 times'
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
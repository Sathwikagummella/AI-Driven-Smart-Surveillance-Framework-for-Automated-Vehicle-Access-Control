# ==========================================
# FILE: app.py
# FIX: If you only see the "Next-Gen Access Control" screen, you are on the home page (/).
# You must click the "LOGIN" button to go to /login, enter your credentials, 
# and the server will then redirect you to the /dashboard.
# Replace your entire app.py with this verified code.
# ==========================================

import os
import random
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session

from ml_engine.detect import process_license_plate 
from config import Config
from models import db, Admin, Resident, Vehicle, VisitorLog, Suspect, Blacklist

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()
    if not Admin.query.first():
        hashed_pw = generate_password_hash('admin123')
        default_admin = Admin(name='Main Admin', email='admin@pravigil.com', password=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()

@app.route('/')
def index():
    # This renders the screen you showed in your screenshot.
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        
        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            session['admin_name'] = admin.name
            flash(f'Authentication Successful. Welcome, {admin.name}.', 'success')
            return redirect(url_for('dashboard')) # Redirects to dashboard upon success
        else:
            flash('ACCESS DENIED: Invalid email or password.', 'error')
            
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out securely.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    # You will only see this page after successful login
    if 'admin_id' not in session: 
        flash('Please log in to access the Command Center.', 'error')
        return redirect(url_for('login'))

    resident_count = Resident.query.count()
    suspect_count = Suspect.query.count()
    blacklist_count = Blacklist.query.count()
    access_granted_count = VisitorLog.query.filter(VisitorLog.status.like('Granted%')).count()

    return render_template('dashboard.html', 
                           residents=resident_count, suspects=suspect_count, 
                           blacklisted=blacklist_count, access_granted=access_granted_count)

@app.route('/add_resident', methods=['GET', 'POST'])
def add_resident():
    if 'admin_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        vehicle_no = request.form.get('vehicle_no').strip().upper()
        name = request.form.get('name').strip()
        resident_id = request.form.get('resident_id').strip()
        phone_no = request.form.get('phone_no').strip()
        flat_no = request.form.get('flat_no').strip()

        if Vehicle.query.filter_by(license_plate=vehicle_no).first():
            flash(f"ERROR: Vehicle {vehicle_no} is already registered.", "error")
            return redirect(url_for('add_resident'))

        try:
            existing_resident = Resident.query.filter_by(resident_id=resident_id).first()
            if not existing_resident:
                new_resident = Resident(resident_id=resident_id, name=name, phone_no=phone_no, flat_no=flat_no)
                db.session.add(new_resident)
                db.session.commit() 
            new_vehicle = Vehicle(license_plate=vehicle_no, resident_id=resident_id)
            db.session.add(new_vehicle)
            db.session.commit()
            flash(f"✅ SUCCESS: Registered {name} and linked vehicle {vehicle_no}.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Database Error: {str(e)}", "error")
        return redirect(url_for('add_resident'))
    return render_template('add_resident.html')

@app.route('/residents')
def residents():
    if 'admin_id' not in session: return redirect(url_for('login'))
    return render_template('residents.html', vehicles=Vehicle.query.all())

@app.route('/suspects')
def suspects():
    if 'admin_id' not in session: return redirect(url_for('login'))
    return render_template('suspects.html', suspects=Suspect.query.all())

@app.route('/blacklist')
def blacklist():
    if 'admin_id' not in session: return redirect(url_for('login'))
    return render_template('blacklist.html', blacklisted=Blacklist.query.all())

@app.route('/delete_record', methods=['POST'])
def delete_record():
    if 'admin_id' not in session: return redirect(url_for('login'))
    plate = request.form.get('license_plate')
    table_type = request.form.get('table_type') 
    try:
        if table_type == 'resident':
            v = Vehicle.query.filter_by(license_plate=plate).first()
            if v: db.session.delete(v)
        elif table_type == 'suspect':
            s = Suspect.query.filter_by(license_plate=plate).first()
            if s: db.session.delete(s)
        elif table_type == 'blacklist':
            b = Blacklist.query.filter_by(license_plate=plate).first()
            if b: db.session.delete(b)
        db.session.commit()
        flash(f"✅ SUCCESS: Record {plate} deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"ERROR: {str(e)}", "error")
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/access_check', methods=['GET', 'POST'])
def access_check():
    if 'admin_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            flash('ERROR: No valid image file detected.', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            extracted_text, status_msg = process_license_plate(filepath)
            if os.path.exists(filepath): os.remove(filepath)

            if not extracted_text:
                flash(f"SCAN FAILED: {status_msg}", 'error')
                return redirect(request.url)

            if Blacklist.query.filter_by(license_plate=extracted_text).first():
                log = VisitorLog(license_plate=extracted_text, status='Denied - Blacklisted')
                db.session.add(log)
                db.session.commit()
                flash(f"🚨 ACCESS DENIED: {extracted_text} is Blacklisted!", 'error')
                return redirect(url_for('access_check'))

            vehicle = Vehicle.query.filter_by(license_plate=extracted_text).first()
            if vehicle:
                log = VisitorLog(license_plate=extracted_text, status='Granted - Resident')
                db.session.add(log)
                db.session.commit()
                flash(f"✅ ACCESS GRANTED: {vehicle.owner.name}.", 'success')
                return redirect(url_for('access_check'))

            session['pending_visitor_plate'] = extracted_text
            flash(f"⚠️ UNKNOWN VEHICLE ({extracted_text}): Redirecting to OTP.", 'warning')
            return redirect(url_for('visitor_otp'))
    return render_template('access_check.html')

@app.route('/visitor_otp', methods=['GET', 'POST'])
def visitor_otp():
    if 'admin_id' not in session: return redirect(url_for('login'))
    pending_plate = session.get('pending_visitor_plate')
    if not pending_plate:
        return redirect(url_for('access_check'))

    VALID_OTP = "123456" 
    if request.method == 'POST':
        if request.form.get('otp') == VALID_OTP:
            log = VisitorLog(license_plate=pending_plate, status='Granted - Visitor OTP')
            db.session.add(log)
            db.session.commit()
            session.pop('pending_visitor_plate', None)
            flash(f"✅ ACCESS GRANTED: {pending_plate} verified.", 'success')
            return redirect(url_for('access_check'))
        else:
            suspect = Suspect.query.filter_by(license_plate=pending_plate).first()
            if not suspect:
                new_suspect = Suspect(license_plate=pending_plate, failed_attempts=1)
                db.session.add(new_suspect)
                db.session.commit()
                flash(f"❌ INVALID OTP. Attempt 1/3 logged for {pending_plate}.", 'error')
            else:
                suspect.failed_attempts += 1
                if suspect.failed_attempts >= 3:
                    db.session.add(Blacklist(license_plate=pending_plate, reason="Failed OTP 3x"))
                    db.session.delete(suspect)
                    db.session.add(VisitorLog(license_plate=pending_plate, status='Denied - OTP Failed 3x'))
                    db.session.commit()
                    session.pop('pending_visitor_plate', None)
                    flash(f"🚨 ALERT: {pending_plate} failed 3 attempts. BLACKLISTED.", 'error')
                    return redirect(url_for('access_check'))
                else:
                    db.session.commit()
                    flash(f"❌ INVALID OTP. Attempt {suspect.failed_attempts}/3.", 'error')
            return redirect(url_for('visitor_otp'))
    return render_template('visitor_otp.html', plate=pending_plate)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, port=5000)
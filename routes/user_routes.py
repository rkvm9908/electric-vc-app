import os
import cloudinary
import cloudinary.uploader
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.utils import secure_filename
from models import db, User, Station, Slot, Branch, Booking, Feedback
from datetime import datetime, time, timedelta

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)
user_bp = Blueprint('user', __name__, url_prefix='/user')
# =========================
# AUTHENTICATION
# =========================
@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        vehicle_no = request.form.get('vehicle_no')
        password = request.form.get('password')

        if not username or not email or not vehicle_no or not password:
            flash("All fields (Username, Email, Vehicle Number, Password) are mandatory!", "danger")
            return redirect(url_for('user.register'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            return redirect(url_for('user.register'))
        
        if User.query.filter_by(username=username).first():
            flash("Username already taken!", "danger")
            return redirect(url_for('user.register'))

        new_user = User(username=username, email=email, vehicle_no=vehicle_no)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('user.login'))

    return render_template('auth/register.html')

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.role == 'user':
            login_user(user)
            return redirect(url_for('user.dashboard'))
        else:
            flash("Invalid credentials or access denied.", "danger")
            return redirect(url_for('user.login'))

    return render_template('auth/login.html')

# =========================
# DASHBOARD & MODULES
# =========================
@user_bp.route('/dashboard')
@login_required
def dashboard():
    total_bookings = Booking.query.filter_by(user_id=current_user.id).count()
    active_bookings = Booking.query.filter_by(user_id=current_user.id, status='Confirmed').count()
    return render_template('user/dashboard.html', total_bookings=total_bookings, active_bookings=active_bookings)

@user_bp.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    selected_vehicle = request.args.get('vehicle_type')
    selected_branch_id = request.args.get('branch_id', '').strip()
    selected_branch = None
    available_slots = []

    branches = Branch.query.order_by(Branch.name).all()
    branch_summaries = []
    for branch in branches:
        available_2w = Slot.query.filter_by(branch_id=branch.id, status='Available', type='2W', parent_slot_id=None).count()
        available_4w = Slot.query.filter_by(branch_id=branch.id, status='Available', type='4W', parent_slot_id=None).count()
        branch_summaries.append({
            'branch': branch,
            'available_2w': available_2w,
            'available_4w': available_4w,
            'total_available': available_2w + available_4w
        })

    if request.method == 'POST':
        selected_branch_id = request.form.get('branch_id', '').strip()
        selected_vehicle = request.form.get('vehicle_type')
        date_str = request.form.get('booking_date')
        time_str = request.form.get('booking_time')

        if not selected_branch_id:
            flash('Please select a branch before booking.', 'danger')
            return redirect(url_for('user.booking'))

        try:
            branch_id_int = int(selected_branch_id)
            selected_branch = Branch.query.get(branch_id_int)
        except (ValueError, TypeError):
            selected_branch = None

        if not selected_branch:
            flash('Selected branch not found.', 'danger')
            return redirect(url_for('user.booking'))

        if not selected_vehicle:
            flash('Please choose a vehicle type.', 'danger')
            return redirect(url_for('user.booking', branch_id=selected_branch.id))

        if not date_str or not time_str:
            flash('Please choose booking date and time.', 'danger')
            return redirect(url_for('user.booking', branch_id=selected_branch.id))

        try:
            scheduled_start = datetime.fromisoformat(f"{date_str}T{time_str}")
        except ValueError:
            flash('Please enter a valid date and time.', 'danger')
            return redirect(url_for('user.booking', branch_id=selected_branch.id))

        scheduled_end = scheduled_start + timedelta(hours=1)
        open_time = selected_branch.open_time or time(6, 0)
        close_time = selected_branch.close_time or time(22, 0)

        if not (open_time <= scheduled_start.time() < close_time and open_time < scheduled_end.time() <= close_time):
            flash('Selected time is outside operating hours.', 'danger')
            return redirect(url_for('user.booking', branch_id=selected_branch.id))

        # SELECT ... FOR UPDATE: locks the matching row so that if two users
        # hit this endpoint for the same slot at the same time, the second
        # request waits until the first one's transaction commits (and by
        # then the slot is no longer 'Available'), preventing double-booking.
        slot = Slot.query.filter_by(
            branch_id=selected_branch.id,
            status='Available',
            parent_slot_id=None,
            type=selected_vehicle
        ).order_by(Slot.id).with_for_update().first()

        if not slot:
            db.session.rollback()
            flash(f'No available {selected_vehicle} slots at this branch.', 'danger')
            return redirect(url_for('user.booking', branch_id=selected_branch.id))

        hours = 1
        price_per_hour = selected_branch.price_2w_per_hour if selected_vehicle == '2W' else selected_branch.price_4w_per_hour
        total_cost = price_per_hour * hours

        booking_time = datetime.utcnow()
        booking = Booking(
            user_id=current_user.id,
            slot_id=slot.id,
            station_id=slot.station_id,
            vehicle_type=selected_vehicle,
            booking_time=booking_time,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            total_cost=total_cost,
            status='Booked'
        )
        child_slot = Slot(
            station_id=slot.station_id,
            branch_id=slot.branch_id,
            parent_slot_id=slot.id,
            user_id=current_user.id,
            type=slot.type,
            status='Booked',
            vehicle_type=slot.type,
            booked_at=booking_time,
            _branch_name=slot.branch_name
        )
        slot.status = 'Occupied'
        db.session.add(child_slot)
        db.session.add(booking)
        db.session.commit()
        flash(f'Booking confirmed successfully! Reference: {booking.booking_reference}', 'success')
        return redirect(url_for('user.history'))

    if selected_branch_id:
        try:
            branch_id_int = int(selected_branch_id)
            selected_branch = Branch.query.get(branch_id_int)
        except ValueError:
            selected_branch = None

    available_2w = 0
    available_4w = 0
    if selected_branch:
        available_base = Slot.query.filter(
            Slot.status == 'Available',
            Slot.parent_slot_id == None,
            Slot.branch_id == selected_branch.id
        )
        available_2w = available_base.filter(Slot.type == '2W').count()
        available_4w = available_base.filter(Slot.type == '4W').count()
        available_slots = available_base.order_by(Slot.type, Slot.id).all()

    return render_template('user/booking.html',
                           branches=branches,
                           branch_summaries=branch_summaries,
                           slots=available_slots,
                           selected_vehicle=selected_vehicle,
                           selected_branch=selected_branch,
                           selected_branch_id=selected_branch_id,
                           available_2w=available_2w,
                           available_4w=available_4w,
                           total_available=available_2w + available_4w)

@user_bp.route('/confirm-booking/<int:slot_id>', methods=['GET', 'POST'])
@login_required
def confirm_booking(slot_id):
    slot = Slot.query.get_or_404(slot_id)
    if slot.status != 'Available':
        flash("Slot is no longer available.", "danger")
        return redirect(url_for('user.booking'))
    
    if request.method == 'POST':
        date_str = request.form.get('booking_date')
        time_str = request.form.get('booking_time')
        if not date_str or not time_str:
            flash("Please select a valid date and time.", "danger")
            return redirect(url_for('user.confirm_booking', slot_id=slot_id))

        # Re-fetch with a row lock and re-check availability: another user
        # could have booked this exact slot between the GET above and this
        # POST. Locking + re-checking prevents two people ending up with the
        # same slot.
        slot = Slot.query.filter_by(id=slot_id).with_for_update().first()
        if not slot or slot.status != 'Available':
            db.session.rollback()
            flash("Sorry, this slot was just booked by someone else. Please pick another.", "danger")
            return redirect(url_for('user.booking'))

        scheduled_start = datetime.fromisoformat(f"{date_str}T{time_str}")
        # Assume 1 hour duration for now
        scheduled_end = scheduled_start + timedelta(hours=1)
        
        # Validate within operating hours using branch schedule when available
        branch = slot.branch
        if branch:
            open_time = branch.open_time
            close_time = branch.close_time
        else:
            open_time = time(6, 0)
            close_time = time(22, 0)

        if not (open_time <= scheduled_start.time() < close_time and 
                open_time < scheduled_end.time() <= close_time):
            flash("Selected time is outside operating hours.", "danger")
            return redirect(url_for('user.confirm_booking', slot_id=slot_id))
        
        # Calculate total cost
        hours = 1  # Fixed for now
        if slot.branch:
            price_per_hour = slot.branch.price_2w_per_hour if slot.type == '2W' else slot.branch.price_4w_per_hour
        else:
            price_per_hour = 0.0
        total_cost = price_per_hour * hours
        
        booking_time = datetime.utcnow()
        booking = Booking(
            user_id=current_user.id,
            slot_id=slot.id,
            station_id=slot.station_id,
            vehicle_type=slot.type,
            booking_time=booking_time,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            total_cost=total_cost,
            status='Booked'
        )
        child_slot = Slot(
            station_id=slot.station_id,
            branch_id=slot.branch_id,
            parent_slot_id=slot.id,
            user_id=current_user.id,
            type=slot.type,
            status='Booked',
            vehicle_type=slot.type,
            booked_at=booking_time,
            _branch_name=slot.branch_name
        )
        slot.status = 'Occupied'
        db.session.add(child_slot)
        db.session.add(booking)
        db.session.commit()
        flash(f"Booking confirmed successfully! Reference: {booking.booking_reference}", "success")
        return redirect(url_for('user.history'))
    
    return render_template('user/confirm_booking.html', slot=slot)

@user_bp.route('/history')
@login_required
def history():
    status_filter = request.args.get('status', 'All')
    station_filter = request.args.get('station', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    bookings_query = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_time.desc())
    if status_filter != 'All':
        bookings_query = bookings_query.filter_by(status=status_filter)
    if station_filter:
        bookings_query = bookings_query.join(Station).filter(Station.name.ilike(f'%{station_filter}%'))
    if date_from:
        try:
            from_dt = datetime.fromisoformat(date_from)
            bookings_query = bookings_query.filter(Booking.scheduled_start >= from_dt)
        except ValueError:
            pass
    if date_to:
        try:
            to_dt = datetime.fromisoformat(date_to)
            bookings_query = bookings_query.filter(Booking.scheduled_start <= datetime.combine(to_dt, time.max))
        except ValueError:
            pass

    bookings = bookings_query.all()
    return render_template(
        'user/history.html',
        bookings=bookings,
        status_filter=status_filter,
        station_filter=station_filter,
        date_from=date_from,
        date_to=date_to
    )

@user_bp.route('/history/data')
@login_required
def history_data():
    status_filter = request.args.get('status', 'All')
    station_filter = request.args.get('station', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    query = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_time.desc())
    if status_filter != 'All':
        query = query.filter_by(status=status_filter)
    if station_filter:
        query = query.join(Station).filter(Station.name.ilike(f'%{station_filter}%'))
    if date_from:
        try:
            from_dt = datetime.fromisoformat(date_from)
            query = query.filter(Booking.scheduled_start >= from_dt)
        except ValueError:
            pass
    if date_to:
        try:
            to_dt = datetime.fromisoformat(date_to)
            query = query.filter(Booking.scheduled_start <= datetime.combine(to_dt, time.max))
        except ValueError:
            pass

    bookings = query.all()
    return jsonify(
        total_count=len(bookings),
        bookings=[{
            'booking_reference': booking.booking_reference,
            'station': booking.station.name,
            'vehicle_type': booking.vehicle_type,
            'scheduled_start': booking.scheduled_start.strftime('%b %d, %Y %H:%M') if booking.scheduled_start else booking.booking_time.strftime('%b %d, %Y'),
            'scheduled_end': booking.scheduled_end.strftime('%H:%M') if booking.scheduled_end else '',
            'total_cost': booking.total_cost or 0,
            'status': booking.status
        } for booking in bookings]
    )

@user_bp.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        station_id = request.form.get('station_id')
        rating = request.form.get('rating')
        comment = request.form.get('comment')

        if not station_id or not rating:
            flash("Please select a station and a star rating.", "danger")
            return redirect(url_for('user.feedback'))

        new_feedback = Feedback(
            user_id=current_user.id,
            station_id=int(station_id),
            rating=int(rating),
            comment=comment
        )
        db.session.add(new_feedback)
        db.session.commit()
        flash("Review submitted! Thank you.", "success")
        return redirect(url_for('user.feedback'))

    stations = Station.query.all()
    my_feedbacks = Feedback.query.filter_by(user_id=current_user.id)\
                                 .order_by(Feedback.timestamp.desc()).all()
    return render_template('user/feedback.html', stations=stations, my_feedbacks=my_feedbacks)

# =========================
# PROFILE (INSTAGRAM STYLE)
# =========================
@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.bio = request.form.get('bio')
        
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="ev_charge/profile_pics",
                        public_id=f"user_{current_user.id}",
                        overwrite=True,
                        resource_type="image"
                    )
                    # Store the full Cloudinary URL directly — templates using
                    # this field as a URL (e.g. <img src="{{ current_user.profile_pic }}">)
                    # will keep working without changes.
                    current_user.profile_pic = upload_result['secure_url']
                except Exception as e:
                    flash(f"Profile picture upload failed: {e}", "danger")
        
        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html')

# =========================
# TRACK LOCATION (SIMULATED)
# =========================
@user_bp.route('/track')
@login_required
def track():
    branches = Branch.query.all()
    branch_totals = {}
    for branch in branches:
        available_2w = Slot.query.filter_by(branch_id=branch.id, status='Available', parent_slot_id=None, type='2W').count()
        available_4w = Slot.query.filter_by(branch_id=branch.id, status='Available', parent_slot_id=None, type='4W').count()
        branch_totals[branch.id] = {
            '2w': available_2w,
            '4w': available_4w,
            'total': available_2w + available_4w
        }

    return render_template('user/track.html', branches=branches, branch_totals=branch_totals)

@user_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for('home'))
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, current_user, logout_user
from sqlalchemy import func
from models import db, User, Station, Slot, Branch, Booking, Feedback
from datetime import datetime, time

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# =========================
# ADMIN AUTH
# =========================
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        admin = User.query.filter_by(email=email, role='admin').first()

        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid admin credentials.", "danger")
            return redirect(url_for('admin.login'))

    return render_template('admin/login.html')

# =========================
# DASHBOARD (STATS)
# =========================
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('admin.login'))
    
    stats = {
        'total_users': User.query.filter_by(role='user').count(),
        'total_stations': Station.query.count(),
        'total_bookings': Booking.query.count(),
        'confirmed_bookings': Booking.query.filter_by(status='Confirmed').count(),
        'completed_bookings': Booking.query.filter_by(status='Completed').count(),
        'pending_feedbacks': Feedback.query.count()
    }
    return render_template('admin/dashboard.html', stats=stats)

# =========================
# STATION MANAGEMENT
# =========================
@admin_bp.route('/stations', methods=['GET', 'POST'])
@login_required
def stations():
    if request.method == 'POST':
        form_type = request.form.get('form_type', 'station')

        if form_type == 'branch':
            station_id = request.form.get('branch_station_id')
            branch_name = request.form.get('branch_name')
            branch_location = request.form.get('branch_location')
            branch_lat = request.form.get('branch_latitude')
            branch_lng = request.form.get('branch_longitude')
            branch_2w = int(request.form.get('branch_slots_2w', 0))
            branch_4w = int(request.form.get('branch_slots_4w', 0))
            branch_open_time_str = request.form.get('branch_open_time')
            branch_close_time_str = request.form.get('branch_close_time')

            if not station_id or not branch_name:
                flash('Please choose a station and enter a branch name.', 'danger')
                return redirect(url_for('admin.stations'))

            branch_station = Station.query.get(station_id)
            if not branch_station:
                flash('Selected station not found.', 'danger')
                return redirect(url_for('admin.stations'))

            from datetime import time
            branch_open_time = time.fromisoformat(branch_open_time_str) if branch_open_time_str else time(6, 0)
            branch_close_time = time.fromisoformat(branch_close_time_str) if branch_close_time_str else time(22, 0)

            branch_price_2w = float(request.form.get('branch_price_2w', 20.0))
            branch_price_4w = float(request.form.get('branch_price_4w', 50.0))
            new_branch = Branch(
                station_id=branch_station.id,
                name=branch_name,
                location=branch_location,
                latitude=float(branch_lat) if branch_lat else None,
                longitude=float(branch_lng) if branch_lng else None,
                slots_2w_total=branch_2w,
                slots_4w_total=branch_4w,
                price_2w_per_hour=branch_price_2w,
                price_4w_per_hour=branch_price_4w,
                open_time=branch_open_time,
                close_time=branch_close_time
            )
            db.session.add(new_branch)
            db.session.flush()

            for index in range(1, branch_2w + 1):
                db.session.add(Slot(
                    station_id=branch_station.id,
                    branch_id=new_branch.id,
                    type='2W',
                    status='Available',
                    _branch_name=f"{new_branch.branch_code}-2W-{index:02d}"
                ))
            for index in range(1, branch_4w + 1):
                db.session.add(Slot(
                    station_id=branch_station.id,
                    branch_id=new_branch.id,
                    type='4W',
                    status='Available',
                    _branch_name=f"{new_branch.branch_code}-4W-{index:02d}"
                ))

            db.session.commit()
            flash(f"Branch '{branch_name}' added to {branch_station.name}.", 'success')
            return redirect(url_for('admin.stations'))

        name = request.form.get('name')
        location = request.form.get('location')  # TN Location
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')

        new_station = Station(
            name=name,
            location=location,
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None
        )
        db.session.add(new_station)
        db.session.commit()
        flash(f"Station '{name}' added successfully.", "success")
        return redirect(url_for('admin.stations'))

    all_stations = Station.query.all()
    all_branches = Branch.query.order_by(Branch.name).all()
    return render_template('admin/stations.html', stations=all_stations, branches=all_branches)

@admin_bp.route('/edit_station/<int:station_id>', methods=['GET', 'POST'])
@login_required
def edit_station(station_id):
    station = Station.query.get_or_404(station_id)
    if request.method == 'POST':
        station.name = request.form.get('name')
        station.location = request.form.get('location')
        station.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
        station.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
        db.session.commit()
        flash(f"Station '{station.name}' updated.", "success")
        return redirect(url_for('admin.stations'))
    
    return render_template('admin/edit_station.html', station=station)

@admin_bp.route('/delete_station/<int:station_id>', methods=['POST'])
@login_required
def delete_station(station_id):
    station = Station.query.get_or_404(station_id)
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('admin.login'))

    Booking.query.filter_by(station_id=station.id).delete()
    Slot.query.filter_by(station_id=station.id).delete()
    Branch.query.filter_by(station_id=station.id).delete()
    db.session.delete(station)
    db.session.commit()
    flash(f"Station '{station.name}' and its related data have been deleted.", "success")
    return redirect(url_for('admin.stations'))

@admin_bp.route('/edit_branch/<int:branch_id>', methods=['GET', 'POST'])
@login_required
def edit_branch(branch_id):
    branch = Branch.query.get_or_404(branch_id)
    if request.method == 'POST':
        branch.name = request.form.get('name')
        branch.location = request.form.get('location')
        branch.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
        branch.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
        branch.slots_2w_total = int(request.form.get('slots_2w', branch.slots_2w_total))
        branch.slots_4w_total = int(request.form.get('slots_4w', branch.slots_4w_total))
        branch.price_2w_per_hour = float(request.form.get('price_2w', branch.price_2w_per_hour))
        branch.price_4w_per_hour = float(request.form.get('price_4w', branch.price_4w_per_hour))
        branch.open_time = time.fromisoformat(request.form.get('open_time')) if request.form.get('open_time') else branch.open_time
        branch.close_time = time.fromisoformat(request.form.get('close_time')) if request.form.get('close_time') else branch.close_time
        db.session.commit()
        flash(f"Branch '{branch.name}' updated.", "success")
        return redirect(url_for('admin.stations'))
    return render_template('admin/edit_branch.html', branch=branch)

# =========================
# SLOT MONITORING
# =========================
@admin_bp.route('/slots')
@login_required
def slots():
    confirm_slot = Slot.query.filter_by(status='Confirmed').all()
    occupied_slots = Slot.query.filter_by(status='Occupied').all()

    available_branches = []
    branches = Branch.query.order_by(Branch.name).all()
    for branch in branches:
        available_2w = Slot.query.filter_by(branch_id=branch.id, status='Available', type='2W').count()
        available_4w = Slot.query.filter_by(branch_id=branch.id, status='Available', type='4W').count()
        if available_2w or available_4w:
            available_branches.append({
                'branch': branch,
                'available_2w': available_2w,
                'available_4w': available_4w,
                'total_available': available_2w + available_4w
            })

    return render_template(
        'admin/slots.html',
        occupied_slots=occupied_slots,
        confirmed_slots=confirm_slot,
        available_branches=available_branches
    )

@admin_bp.route('/release_slot/<int:slot_id>', methods=['POST'])
@login_required
def release_slot(slot_id):
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('admin.login'))

    # `slot` here is the PHYSICAL (parent) slot — it's the one shown in the
    # admin slots list with status 'Occupied' / 'Confirmed'.
    slot = Slot.query.get_or_404(slot_id)

    # The actual reservation is stored as a separate CHILD slot row
    # (parent_slot_id == slot.id). That child row is what should move to
    # 'Completed' — the physical slot itself should go back to 'Available'
    # so it can be booked again.
    child_slot = Slot.query.filter_by(
        parent_slot_id=slot.id,
        status='Booked'
    ).order_by(Slot.id.desc()).first()

    if child_slot:
        child_slot.status = 'Completed'

    slot.status = 'Available'

    booking = Booking.query.filter_by(slot_id=slot.id, status='Confirmed').first()
    if booking:
        booking.status = 'Completed'

    db.session.commit()
    flash(f"Slot at {slot.station.name} has been marked as Completed and is now Available again.", "success")
    return redirect(url_for('admin.slots'))
@admin_bp.route('/confirm_slot/<int:slot_id>', methods=['POST'])
@login_required
def confirm_slot(slot_id):
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('admin.login'))
    
    slot = Slot.query.get_or_404(slot_id)
    slot.status = 'Confirmed'
    
    # Update associated booking if any
    booking = Booking.query.filter_by(slot_id=slot.id, status='Booked').first()
    if booking:
        booking.status = 'Confirmed'
    
    db.session.commit()
    flash(f"Slot at {slot.station.name} has been marked as Confirmed.", "success")
    return redirect(url_for('admin.slots'))


@admin_bp.route('/history')
@login_required
def history():
    status_filter = request.args.get('status', 'Completed')
    if status_filter != 'Completed':
        status_filter = 'Completed'
    user_filter = request.args.get('user', '').strip()
    station_filter = request.args.get('station', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    bookings_query = Booking.query.filter_by(status='Completed').order_by(Booking.booking_time.desc())
    if user_filter:
        bookings_query = bookings_query.join(User).filter(User.username.ilike(f'%{user_filter}%'))
    if station_filter:
        bookings_query = bookings_query.join(Station).filter(Station.name.ilike(f'%{station_filter}%'))
    if date_from:
        try:
            from_dt = datetime.fromisoformat(date_from)
            bookings_query = bookings_query.filter(func.coalesce(Booking.scheduled_start, Booking.booking_time) >= from_dt)
        except ValueError:
            pass
    if date_to:
        try:
            to_dt = datetime.fromisoformat(date_to)
            bookings_query = bookings_query.filter(func.coalesce(Booking.scheduled_start, Booking.booking_time) <= datetime.combine(to_dt, time.max))
        except ValueError:
            pass

    bookings = bookings_query.all()
    return render_template(
        'admin/history.html',
        bookings=bookings,
        status_filter=status_filter,
        user_filter=user_filter,
        station_filter=station_filter,
        date_from=date_from,
        date_to=date_to,
    )

@admin_bp.route('/history/data')
@login_required
def history_data():
    user_filter = request.args.get('user', '').strip()
    station_filter = request.args.get('station', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    query = Booking.query.filter_by(status='Completed').order_by(Booking.booking_time.desc())
    if user_filter:
        query = query.join(User).filter(User.username.ilike(f'%{user_filter}%'))
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
            'station': booking.station.name,
            'user': booking.user.username,
            'vehicle_type': booking.vehicle_type,
            'vehicle_no': booking.user.vehicle_no,
            'scheduled_start': booking.scheduled_start.strftime('%b %d, %Y %H:%M') if booking.scheduled_start else booking.booking_time.strftime('%b %d, %Y'),
            'scheduled_end': booking.scheduled_end.strftime('%H:%M') if booking.scheduled_end else '',
            'total_cost': booking.total_cost or 0,
            'status': booking.status
        } for booking in bookings]
    )

@admin_bp.route('/history/analysis', methods=['GET', 'POST'])
@login_required
def history_analysis():
    stations = Station.query.order_by(Station.name).all()
    users = User.query.filter_by(role='user').order_by(User.username).all()
    selected_station_id = request.form.get('station_id', '').strip()
    selected_user_id = request.form.get('user_id', '').strip()
    errors = []
    results = {}

    if request.method == 'POST':
        if not selected_station_id and not selected_user_id:
            errors.append('Please select a station or a user to analyze.')
        else:
            selected_station = Station.query.get(int(selected_station_id)) if selected_station_id else None
            selected_user = User.query.get(int(selected_user_id)) if selected_user_id else None

            if selected_station_id and not selected_station:
                errors.append('Selected station could not be found.')
            if selected_user_id and not selected_user:
                errors.append('Selected user could not be found.')

            if not errors:
                results['selected_station'] = selected_station
                results['selected_user'] = selected_user

                if selected_station:
                    station_groups = db.session.query(
                        Booking.user_id,
                        db.func.count(Booking.id).label('count')
                    ).filter(Booking.station_id == selected_station.id)
                    station_groups = station_groups.group_by(Booking.user_id).order_by(db.func.count(Booking.id).desc()).all()

                    if station_groups:
                        top_station_user_id, top_station_count = station_groups[0]
                        results['top_user_for_station'] = {
                            'user': User.query.get(top_station_user_id),
                            'count': top_station_count
                        }
                    else:
                        results['top_user_for_station'] = None

                    other_groups = db.session.query(
                        Booking.user_id,
                        db.func.count(Booking.id).label('count')
                    ).filter(Booking.station_id != selected_station.id)
                    other_groups = other_groups.group_by(Booking.user_id).order_by(db.func.count(Booking.id).desc()).all()

                    if other_groups:
                        top_other_user_id, top_other_count = other_groups[0]
                        results['top_user_across_other_stations'] = {
                            'user': User.query.get(top_other_user_id),
                            'count': top_other_count
                        }
                    else:
                        results['top_user_across_other_stations'] = None

                if selected_user:
                    user_bookings = db.session.query(
                        Booking.station_id,
                        db.func.count(Booking.id).label('count')
                    ).filter(Booking.user_id == selected_user.id).group_by(Booking.station_id).all()

                    station_breakdown = [
                        {
                            'station': Station.query.get(station_id),
                            'count': count
                        }
                        for station_id, count in user_bookings
                    ]
                    results['selected_user_station_breakdown'] = station_breakdown
                    results['selected_user_total_bookings'] = sum(item['count'] for item in station_breakdown)

                    if selected_station:
                        results['selected_user_bookings_at_station'] = next((item['count'] for item in station_breakdown if item['station'] and item['station'].id == selected_station.id), 0)
                        results['selected_user_bookings_other_stations'] = sum(item['count'] for item in station_breakdown if item['station'] and item['station'].id != selected_station.id)
                    else:
                        results['selected_user_bookings_at_station'] = None
                        results['selected_user_bookings_other_stations'] = None

    return render_template(
        'admin/history_analysis.html',
        stations=stations,
        users=users,
        results=results,
        errors=errors,
        selected_station_id=selected_station_id,
        selected_user_id=selected_user_id
    )

# =========================
# FEEDBACK VIEW
# =========================
@admin_bp.route('/feedback')
@login_required
def feedback():
    all_feedbacks = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    total_count = len(all_feedbacks)
    avg_rating = sum(f.rating for f in all_feedbacks) / total_count if total_count > 0 else 0
    
    # Calculate distribution (5 to 1 stars)
    distribution = {}
    for i in range(1, 6):
        count = sum(1 for f in all_feedbacks if f.rating == i)
        percentage = (count / total_count * 100) if total_count > 0 else 0
        distribution[i] = {
            'count': count,
            'percentage': percentage
        }

    return render_template('admin/feedback.html', 
                           feedbacks=all_feedbacks, 
                           avg_rating=round(avg_rating, 1),
                           total_count=total_count,
                           distribution=distribution)

# =========================
# PROFILE
# =========================
@admin_bp.route('/profile')
@login_required
def profile():
    return render_template('admin/profile.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Admin logged out.", "info")
    return redirect(url_for('home'))
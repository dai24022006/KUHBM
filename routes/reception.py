from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Booking, Room
from datetime import date

reception_bp = Blueprint('reception', __name__, url_prefix='/reception')


def reception_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ['reception', 'admin']:
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated


@reception_bp.route('/dashboard')
@login_required
@reception_required
def dashboard():
    today = date.today()
    checkins_today = Booking.query.filter(
        Booking.check_in == today,
        Booking.status == 'confirmed'
    ).all()
    checkouts_today = Booking.query.filter(
        Booking.check_out == today,
        Booking.status == 'checked_in'
    ).all()
    active_guests = Booking.query.filter_by(status='checked_in').all()
    return render_template('reception/dashboard.html',
                           checkins=checkins_today,
                           checkouts=checkouts_today,
                           active_guests=active_guests)


@reception_bp.route('/checkin/<int:booking_id>', methods=['POST'])
@login_required
@reception_required
def checkin(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'confirmed':
        flash('Booking is not in confirmed status.', 'warning')
    else:
        booking.status = 'checked_in'
        booking.room.status = 'occupied'
        db.session.commit()
        flash(f'Guest checked in to room {booking.room.number}.', 'success')
    return redirect(url_for('reception.dashboard'))


@reception_bp.route('/checkout/<int:booking_id>', methods=['POST'])
@login_required
@reception_required
def checkout(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'checked_in':
        flash('Guest is not currently checked in.', 'warning')
    else:
        booking.status = 'checked_out'
        booking.room.status = 'available'
        db.session.commit()
        flash(f'Guest checked out from room {booking.room.number}.', 'success')
    return redirect(url_for('reception.dashboard'))

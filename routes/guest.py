from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Room, Booking, ServiceRequest
from datetime import datetime, date

guest_bp = Blueprint('guest', __name__, url_prefix='/guest')


def guest_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'guest':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated


@guest_bp.route('/dashboard')
@login_required
@guest_required
def dashboard():
    my_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).limit(3).all()
    my_requests = ServiceRequest.query.filter_by(user_id=current_user.id).order_by(ServiceRequest.created_at.desc()).limit(3).all()
    return render_template('guest/dashboard.html', bookings=my_bookings, requests=my_requests)


@guest_bp.route('/book', methods=['GET', 'POST'])
@login_required
@guest_required
def book():
    available_rooms = []
    check_in = request.args.get('check_in') or request.form.get('check_in')
    check_out = request.args.get('check_out') or request.form.get('check_out')
    room_type = request.args.get('room_type') or request.form.get('room_type')

    if check_in and check_out:
        try:
            ci = datetime.strptime(check_in, '%Y-%m-%d').date()
            co = datetime.strptime(check_out, '%Y-%m-%d').date()
            if co <= ci:
                flash('Check-out must be after check-in.', 'danger')
            else:
                # Find rooms not booked during this period
                booked_room_ids = db.session.query(Booking.room_id).filter(
                    Booking.status.in_(['confirmed', 'checked_in']),
                    Booking.check_in < co,
                    Booking.check_out > ci
                ).all()
                booked_ids = [r[0] for r in booked_room_ids]

                query = Room.query.filter(
                    Room.status == 'available',
                    ~Room.id.in_(booked_ids)
                )
                if room_type:
                    query = query.filter_by(type=room_type)
                available_rooms = query.all()
        except ValueError:
            flash('Invalid date format.', 'danger')

    return render_template('guest/book.html', rooms=available_rooms,
                           check_in=check_in, check_out=check_out, room_type=room_type)


@guest_bp.route('/book/confirm/<int:room_id>', methods=['POST'])
@login_required
@guest_required
def confirm_booking(room_id):
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    try:
        ci = datetime.strptime(check_in, '%Y-%m-%d').date()
        co = datetime.strptime(check_out, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Invalid dates.', 'danger')
        return redirect(url_for('guest.book'))

    room = Room.query.get_or_404(room_id)
    nights = (co - ci).days
    total = room.base_price * nights

    booking = Booking(user_id=current_user.id, room_id=room_id,
                      check_in=ci, check_out=co, total_price=total)
    db.session.add(booking)
    db.session.commit()
    flash(f'Booking confirmed! Room {room.number} for {nights} night(s). Total: AED {total:.2f}', 'success')
    return redirect(url_for('guest.bookings'))


@guest_bp.route('/bookings')
@login_required
@guest_required
def bookings():
    my_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('guest/bookings.html', bookings=my_bookings)


@guest_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
@guest_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    if booking.status not in ['confirmed']:
        flash('This booking cannot be cancelled.', 'warning')
    else:
        booking.status = 'cancelled'
        db.session.commit()
        flash('Booking cancelled.', 'success')
    return redirect(url_for('guest.bookings'))


@guest_bp.route('/services', methods=['GET', 'POST'])
@login_required
@guest_required
def services():
    if request.method == 'POST':
        req_type = request.form.get('type')
        description = request.form.get('description')
        # Get the guest's active booking if any
        active_booking = Booking.query.filter_by(
            user_id=current_user.id, status='checked_in'
        ).first()
        sr = ServiceRequest(
            user_id=current_user.id,
            booking_id=active_booking.id if active_booking else None,
            type=req_type,
            description=description
        )
        db.session.add(sr)
        db.session.commit()
        flash('Service request submitted!', 'success')
        return redirect(url_for('guest.services'))

    my_requests = ServiceRequest.query.filter_by(user_id=current_user.id).order_by(ServiceRequest.created_at.desc()).all()
    return render_template('guest/services.html', requests=my_requests)

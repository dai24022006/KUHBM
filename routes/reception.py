
import re
from datetime import datetime, date, timedelta
from functools import wraps

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, jsonify
)
from flask_login import login_required, current_user

from models import db, Booking, Room


reception_bp = Blueprint(
    'reception',
    __name__,
    url_prefix='/reception'
)


def reception_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ['reception', 'admin']:
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.index'))

        return f(*args, **kwargs)

    return decorated


# ==========================================
# KIỂM TRA NGÀY
# ==========================================

def validate_dates(check_in, check_out):
    try:
        ci = datetime.strptime(
            check_in, '%Y-%m-%d'
        ).date()

        co = datetime.strptime(
            check_out, '%Y-%m-%d'
        ).date()

    except (ValueError, TypeError):
        return None, None, 'Ngày đặt phòng không hợp lệ.'

    if ci < date.today():
        return None, None, 'Không thể đặt phòng trong quá khứ.'

    if co <= ci:
        return None, None, 'Ngày trả phòng phải sau ngày nhận phòng.'

    return ci, co, None


# ==========================================
# LẤY DANH SÁCH PHÒNG TRỐNG
# ==========================================

def get_available_rooms(ci, co):
    booked_rooms = db.session.query(
        Booking.room_id
    ).filter(
        Booking.status.in_([
            'confirmed',
            'checked_in'
        ]),
        Booking.check_in < co,
        Booking.check_out > ci
    )

    query = Room.query.filter(
        Room.status != 'maintenance',
        ~Room.id.in_(booked_rooms)
    )

    # Nếu nhận phòng hôm nay thì phòng phải
    # thực sự sẵn sàng để khách vào ở.
    if ci == date.today():
        query = query.filter(
            Room.status == 'available'
        )

    return query.order_by(Room.number).all()


# ==========================================
# DASHBOARD
# ==========================================

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

    active_guests = Booking.query.filter_by(
        status='checked_in'
    ).all()

    return render_template(
        'reception/dashboard.html',
        checkins=checkins_today,
        checkouts=checkouts_today,
        active_guests=active_guests
    )


# ==========================================
# API LẤY PHÒNG TRỐNG THEO NGÀY
# ==========================================

@reception_bp.route('/api/available-rooms')
@login_required
@reception_required
def available_rooms():
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')

    ci, co, error = validate_dates(
        check_in, check_out
    )

    if error:
        return jsonify({
            'success': False,
            'message': error,
            'rooms': []
        }), 400

    rooms = get_available_rooms(ci, co)

    return jsonify({
        'success': True,
        'nights': (co - ci).days,
        'rooms': [
            {
                'id': room.id,
                'number': room.number,
                'type': room.type,
                'price': room.base_price,
                'status': room.status
            }
            for room in rooms
        ]
    })


# ==========================================
# ĐẶT PHÒNG TRỰC TIẾP TẠI QUẦY
# ==========================================

@reception_bp.route('/book', methods=['GET', 'POST'])
@login_required
@reception_required
def book():

    if request.method == 'GET':
        return render_template(
            'reception/book.html',
            today=date.today().isoformat(),
            tomorrow=(
                date.today() + timedelta(days=1)
            ).isoformat()
        )

    # Lấy thông tin form
    guest_name = request.form.get(
        'guest_name', ''
    ).strip()

    guest_phone = request.form.get(
        'guest_phone', ''
    ).strip()

    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    room_id = request.form.get('room_id', type=int)

    checkin_now = (
        request.form.get('checkin_now') == 'on'
    )

    # Kiểm tra họ tên
    if not guest_name or len(guest_name) > 100:
        flash('Họ tên phải có từ 1 đến 100 ký tự.', 'danger')
        return redirect(url_for('reception.book'))

    # Kiểm tra SĐT Việt Nam
    if not re.fullmatch(r'0[0-9]{9}', guest_phone):
        flash('Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.', 'danger')
        return redirect(url_for('reception.book'))

    # Kiểm tra ngày
    ci, co, error = validate_dates(
        check_in, check_out
    )

    if error:
        flash(error, 'danger')
        return redirect(url_for('reception.book'))

    # Kiểm tra phòng
    if not room_id:
        flash('Vui lòng chọn phòng.', 'danger')
        return redirect(url_for('reception.book'))

    room = db.session.get(Room, room_id)

    if not room:
        flash('Phòng không tồn tại.', 'danger')
        return redirect(url_for('reception.book'))

    if room.base_price <= 0:
        flash('Giá phòng không hợp lệ.', 'danger')
        return redirect(url_for('reception.book'))

    # Kiểm tra lại lịch phòng ngay trước khi lưu
    available_ids = {
        r.id for r in get_available_rooms(ci, co)
    }

    if room.id not in available_ids:
        flash(
            'Phòng không còn trống trong khoảng thời gian này.',
            'danger'
        )
        return redirect(url_for('reception.book'))

    if checkin_now:
        if ci != date.today():
            flash(
                'Chỉ có thể nhận phòng ngay trong ngày hôm nay.',
                'danger'
            )
            return redirect(url_for('reception.book'))

        if room.status != 'available':
            flash('Phòng chưa sẵn sàng.', 'danger')
            return redirect(url_for('reception.book'))

    # Tính tiền trên server
    nights = (co - ci).days
    total_price = round(room.base_price * nights, 2)

    booking = Booking(
        user_id=None,
        guest_name=guest_name,
        guest_phone=guest_phone,
        booking_source='reception',
        room_id=room.id,
        check_in=ci,
        check_out=co,
        total_price=total_price,
        status=(
            'checked_in'
            if checkin_now
            else 'confirmed'
        )
    )

    try:
        db.session.add(booking)

        if checkin_now:
            room.status = 'occupied'

        db.session.commit()

    except Exception:
        db.session.rollback()
        flash(
            'Có lỗi khi lưu đặt phòng. Vui lòng thử lại.',
            'danger'
        )
        return redirect(url_for('reception.book'))

    flash(
        f'Đặt phòng {room.number} thành công! '
        f'{nights} đêm - Tổng: {total_price:,.2f} AED',
        'success'
    )

    return redirect(url_for('reception.dashboard'))


# ==========================================
# CHECK IN
# ==========================================

@reception_bp.route(
    '/checkin/<int:booking_id>',
    methods=['POST']
)
@login_required
@reception_required
def checkin(booking_id):

    booking = db.get_or_404(Booking, booking_id)

    if booking.status != 'confirmed':
        flash(
            'Booking không ở trạng thái chờ nhận phòng.',
            'warning'
        )

    elif not (
        booking.check_in <= date.today() < booking.check_out
    ):
        flash(
            'Chưa đến ngày nhận phòng hoặc đã quá ngày trả phòng.',
            'danger'
        )

    elif booking.room.status != 'available':
        flash(
            'Phòng hiện chưa sẵn sàng để nhận khách.',
            'danger'
        )

    else:
        booking.status = 'checked_in'
        booking.room.status = 'occupied'

        db.session.commit()

        flash(
            f'Check-in phòng {booking.room.number} thành công.',
            'success'
        )

    return redirect(url_for('reception.dashboard'))


# ==========================================
# CHECK OUT
# ==========================================

@reception_bp.route(
    '/checkout/<int:booking_id>',
    methods=['POST']
)
@login_required
@reception_required
def checkout(booking_id):

    booking = db.get_or_404(Booking, booking_id)

    if booking.status != 'checked_in':
        flash(
            'Khách chưa ở trạng thái đã nhận phòng.',
            'warning'
        )

    else:
        booking.status = 'checked_out'
        booking.room.status = 'available'

        db.session.commit()

        flash(
            f'Check-out phòng {booking.room.number} thành công.',
            'success'
        )

    return redirect(url_for('reception.dashboard'))

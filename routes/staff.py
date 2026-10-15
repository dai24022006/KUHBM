from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, ServiceRequest
from datetime import datetime

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


def staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ['service_staff', 'admin']:
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated


@staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    pending = ServiceRequest.query.filter_by(status='pending').order_by(ServiceRequest.created_at).all()
    in_progress = ServiceRequest.query.filter_by(status='in_progress').order_by(ServiceRequest.created_at).all()
    completed = ServiceRequest.query.filter_by(status='completed').order_by(ServiceRequest.updated_at.desc()).limit(10).all()
    return render_template('staff/dashboard.html',
                           pending=pending,
                           in_progress=in_progress,
                           completed=completed)


@staff_bp.route('/requests/<int:req_id>/update', methods=['POST'])
@login_required
@staff_required
def update_request(req_id):
    sr = ServiceRequest.query.get_or_404(req_id)
    new_status = request.form.get('status')
    if new_status in ['pending', 'in_progress', 'completed']:
        sr.status = new_status
        sr.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Request #{sr.id} updated to {new_status.replace("_", " ")}.', 'success')
    return redirect(url_for('staff.dashboard'))

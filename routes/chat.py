from flask import Blueprint, render_template, request, jsonify, session, abort
from flask_login import login_required, current_user
from models import Room, Booking, ServiceRequest
from config import Config
from openai import OpenAI

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/')
@login_required
def index():
    if current_user.role != 'guest':
        abort(403)
    return render_template('guest/chat.html')


@chat_bp.route('/send', methods=['POST'])
@login_required
def send():
    if current_user.role != 'guest':
        abort(403)
    if not Config.OPENAI_API_KEY:
        return jsonify({'response': 'AI assistant is not configured. Please add an API key.'})

    user_message = request.json.get('message', '')
    if not user_message.strip():
        return jsonify({'response': 'Please enter a message.'})

    if len(user_message) > 500:
        return jsonify({'response': 'Message too long. Please keep messages under 500 characters.'})

    chat_history = session.get('chat_history', [])

    # Build context about available rooms
    available_rooms = Room.query.filter_by(status='available').all()
    room_info = '\n'.join([
        f"- Room {r.number} ({r.type}): AED {r.base_price}/night. {r.description or ''}"
        for r in available_rooms
    ])

    # Guest's active bookings
    active_bookings = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.status.in_(['confirmed', 'checked_in'])
    ).all()
    booking_info = '\n'.join([
        f"- Room {b.room.number} ({b.room.type}): check-in {b.check_in}, check-out {b.check_out}, status: {b.status}, total: AED {b.total_price}"
        for b in active_bookings
    ]) or 'No active bookings.'

    # Guest's open service requests
    open_requests = ServiceRequest.query.filter(
        ServiceRequest.user_id == current_user.id,
        ServiceRequest.status.in_(['pending', 'in_progress'])
    ).all()
    request_info = '\n'.join([
        f"- {r.type} request: '{r.description}', status: {r.status}"
        for r in open_requests
    ]) or 'No open service requests.'

    system_prompt = f"""You are a friendly and knowledgeable hotel assistant for KUHBM, a smart hotel management system.
You are speaking with {current_user.name}. Address them by name occasionally to keep it personal.

--- AVAILABLE ROOMS ---
{room_info if room_info else 'No rooms currently available.'}

--- {current_user.name.upper()}'S ACTIVE BOOKINGS ---
{booking_info}

--- {current_user.name.upper()}'S OPEN SERVICE REQUESTS ---
{request_info}

--- HOW TO USE KUHBM ---
Book a Room:
  1. Click "Book a Room" in the left sidebar.
  2. Select your check-in and check-out dates.
  3. Choose a room type (single, double, or suite).
  4. Click "Confirm Booking". Your booking will appear under "My Bookings".

View / Manage Bookings:
  - Click "My Bookings" in the sidebar to see all your reservations and their status.

Request a Service:
  1. Click "Services" in the sidebar.
  2. Choose a request type: Housekeeping, Room Service, or Maintenance.
  3. Add a description of what you need.
  4. Click "Submit Request". Staff will be notified and you can track the status there.

Chat with AI Assistant:
  - You're already here! Ask anything about your stay, the rooms, or how to use the site.

--- HOTEL POLICIES ---
- Check-in time: 3:00 PM | Check-out time: 11:00 AM
- Cancellations can be requested at the front desk.
- Room service is available 24/7.
- Housekeeping is available daily between 9:00 AM and 5:00 PM.
- For emergencies, contact reception directly at the front desk.

--- YOUR ROLE ---
- Answer questions about available rooms, pricing, and hotel policies.
- Help {current_user.name} understand how to use the website with step-by-step instructions when asked.
- Answer questions about their existing bookings and service requests using the data above.
- You CANNOT make bookings or submit service requests on their behalf - guide them to do it themselves.
- If you don't know something specific (e.g. exact cancellation policy), say so honestly and suggest they contact reception.
- Keep responses concise, friendly, and helpful."""

    try:
        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            max_tokens=512,
            messages=[
                {'role': 'system', 'content': system_prompt},
                *chat_history,
                {'role': 'user', 'content': user_message}
            ]
        )
        reply = response.choices[0].message.content
        chat_history.append({'role': 'user', 'content': user_message})
        chat_history.append({'role': 'assistant', 'content': reply})

        # Cap to last 20 entries, always starting with a user turn
        chat_history = chat_history[-20:]
        if chat_history and chat_history[0]['role'] == 'assistant':
            chat_history = chat_history[1:]

        session['chat_history'] = chat_history
        session.modified = True
    except Exception as e:
        reply = 'Sorry, I encountered an error. Please try again later.'

    return jsonify({'response': reply})

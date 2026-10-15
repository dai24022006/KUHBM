<div align="center">
  <img src="static/img/logo.png" alt="KUHBM" width="120" />

  <p>Hotel management system with room booking, service requests, and an AI guest assistant.</p>

  <a href="https://kuhbm.onrender.com"><strong>kuhbm.onrender.com →</strong></a>

  <br />
  <br />

  ![Python](https://img.shields.io/badge/python-3.x-blue?style=flat-square)
  ![Flask](https://img.shields.io/badge/flask-3.x-lightgrey?style=flat-square)
  ![OpenAI](https://img.shields.io/badge/openai-gpt--4o--mini-412991?style=flat-square)
  ![Status](https://img.shields.io/badge/status-live-brightgreen?style=flat-square)
</div>

---

KUHBM is a full-stack hotel management app built with Flask. Guests can book rooms, request services, and chat with an AI assistant that knows their actual booking data. Staff and admins get their own dashboards. Everything runs as a single Python app with no frontend build step.

No microservices. No separate frontend. No unnecessary complexity.

## Features

- **Room booking**: search by date and type, with real-time conflict prevention
- **Check-in / check-out**: one-click workflows for reception staff with automatic room status updates
- **Service requests**: guests submit housekeeping, room service, or maintenance requests and track them live
- **Role-based access**: four roles (Guest, Reception, Service Staff, Admin), each with a completely separate dashboard
- **AI assistant**: context-aware chatbot that can see the guest's bookings, open requests, and available rooms
- **Dynamic pricing**: admin dashboard suggests price adjustments based on occupancy patterns
- **Auto-seed**: demo accounts and rooms are created automatically on first launch

## How it works

KUHBM uses a standard MVC layout inside Flask. Every request hits a route, queries the database via SQLAlchemy, and returns a rendered Jinja2 template. There is no API layer and no JavaScript framework.

The AI assistant is the only exception. On each message, the `/chat/send` endpoint:

1. Loads the guest's conversation history from the Flask session (capped at 20 messages)
2. Queries the database for the guest's active bookings and open service requests
3. Builds a system prompt with that context and sends it to OpenAI's GPT-4o Mini
4. Saves the updated history back to the session

The AI can answer questions about the guest's stay, explain how to use the site, and discuss room availability. It cannot take actions on the guest's behalf.

## Running locally

```bash
git clone https://github.com/Frisbiz/KUHBM.git
cd KUHBM

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```
SECRET_KEY=any-random-string
OPENAI_API_KEY=sk-...
```

Then run:

```bash
python app.py
```

Open [localhost:5000](http://localhost:5000). Demo accounts are created automatically on first run.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Guest | guest@hotel.com | guest123 |
| Reception | reception@hotel.com | staff123 |
| Service Staff | staff@hotel.com | staff123 |
| Admin | admin@hotel.com | admin123 |

## Project structure

```
hotel-system/
├── app.py              # App factory, DB init, auto-seed
├── models.py           # User, Room, Booking, ServiceRequest
├── config.py           # Config from environment variables
├── seed.py             # Demo data
├── Procfile            # Render/gunicorn entry point
├── requirements.txt
├── routes/
│   ├── auth.py         # Login, register, logout
│   ├── guest.py        # Booking, services dashboard
│   ├── reception.py    # Check-in / check-out
│   ├── staff.py        # Service request queue
│   ├── admin.py        # Rooms, pricing, admin tools
│   └── chat.py         # AI assistant endpoint
├── templates/
│   ├── base.html       # Shared layout and sidebar
│   ├── auth/
│   ├── guest/
│   ├── reception/
│   ├── staff/
│   └── admin/
└── static/
    └── img/            # Logo
```

## Deployment

The app is deployed on Render's free tier with a PostgreSQL database. To deploy your own:

1. Fork this repo
2. Create a new Web Service on [render.com](https://render.com) pointing to your fork
3. Add a PostgreSQL database in Render and link it (sets `DATABASE_URL` automatically)
4. Add `SECRET_KEY` and `OPENAI_API_KEY` as environment variables
5. Deploy. The app will seed itself on first boot

One thing to know about the free tier: the service spins down after 15 minutes of inactivity. The first request after idle will be slow while it wakes up.

## Limitations

- The AI assistant has no memory between sessions. History is cleared on logout
- Dynamic pricing suggestions are rule-based, not a trained model
- No email notifications when service request statuses change
- No mobile-optimised layout
- The free Render tier sleeps after inactivity

## License

MIT.

---

<div align="center">
  <sub>Built with Flask, SQLAlchemy, and OpenAI.</sub>
</div>

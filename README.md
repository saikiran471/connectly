# Connectly — Flask social media portfolio project

A social media web application built with Flask, SQLAlchemy, HTML, CSS, JavaScript, SQLite/PostgreSQL, and Flask-SocketIO.

## Features
- Account registration, login, logout, secure password hashing
- User profiles and bio editing
- Photo posts, captions, comments, likes
- Follow/unfollow and followed-users feed
- Search/explore users and recent posts
- Save/bookmark posts
- Stories that expire after 24 hours (expiration is enforced when displaying stories)
- Notifications for follows, likes, and comments
- Private one-to-one conversations with persisted messages and live updates using Socket.IO
- Post deletion by owner, user reports, pagination, CSRF protection
- Responsive UI and file-size/extension checks

## Requirements
- Python 3.11+
- pip

## Windows PowerShell setup
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Edit `.env` and set `SECRET_KEY` to a long random value, then run:
```powershell
python run.py
```
Open http://127.0.0.1:5000

## macOS/Linux setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set SECRET_KEY
python run.py
```

## Database
SQLite is used by default and created at `instance/connectly.db`. To use PostgreSQL, create a database and set a URL in `.env`, e.g.
`DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/connectly`

This starter calls `db.create_all()` at startup for convenience. It creates missing tables but does not migrate existing tables. If you are upgrading from an earlier Connectly database during development, stop the app and delete `instance/connectly.db` to recreate it. This deletes local test data. For persistent data, configure Flask-Migrate/Alembic migrations instead.

## Test the app
1. Register two different accounts in separate browser profiles.
2. Add posts and follow the second account from Explore.
3. Verify followed accounts' posts appear in your feed.
4. Test likes, comments, bookmarks, notifications, and post deletion.
5. Open Messages, start a conversation, and open the same conversation in both browser profiles to test live updates.

## Security and production checklist
This is a learning/portfolio starter, not a fully audited production service. Before public deployment:
- Use a strong secret, HTTPS, `SESSION_COOKIE_SECURE=True`, and secure proxy settings.
- Configure allowed Socket.IO origins for your actual domain.
- Validate image contents using Pillow, re-encode uploads, limit dimensions, and scan/clean uploads as needed. Extension checks alone are not sufficient.
- Add login rate limiting, email verification, password reset, moderation workflows, and privacy controls.
- Use Flask-Migrate for schema changes, managed PostgreSQL, and managed object storage/CDN for images.
- Configure logging, monitoring, backups, and automated tests.
- Run with a production WSGI/ASGI-compatible deployment setup; do not use Flask debug mode in production.

## Notes
- Story records older than 24 hours are hidden from the feed; a scheduled cleanup can remove old story records and image files.
- Report submissions are stored in the database. A moderation/admin interface is not included yet.
- Socket.IO message sends require both participants to be connected to the same conversation room for immediate live display. Messages remain stored in the database and appear after reload.

from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room
from . import socketio, db
from .models import Conversation, Message

@socketio.on("connect")
def socket_connect(auth=None):
    if not current_user.is_authenticated:
        return False

@socketio.on("join_conversation")
def join_conversation(data):
    if not current_user.is_authenticated:
        return
    try:
        conversation_id = int((data or {}).get("conversation_id"))
    except (TypeError, ValueError):
        return
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or not conversation.contains_user(current_user.id):
        return
    join_room(f"conversation_{conversation_id}")

@socketio.on("send_message")
def send_message(data):
    if not current_user.is_authenticated:
        return
    try:
        conversation_id = int((data or {}).get("conversation_id"))
    except (TypeError, ValueError):
        return
    body = str((data or {}).get("body", "")).strip()
    if not body or len(body) > 2000:
        return
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or not conversation.contains_user(current_user.id):
        return
    message = Message(conversation_id=conversation_id, sender_id=current_user.id, body=body)
    db.session.add(message)
    db.session.commit()
    emit("new_message", {
        "id": message.id,
        "conversation_id": conversation_id,
        "sender_id": current_user.id,
        "sender": current_user.username,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
    }, to=f"conversation_{conversation_id}")

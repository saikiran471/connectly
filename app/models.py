from datetime import datetime, timezone, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

def utcnow():
    return datetime.now(timezone.utc)

follows = db.Table(
    "follows",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.CheckConstraint("follower_id != followed_id", name="no_self_follow"),
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(160), default="")
    avatar = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    posts = db.relationship("Post", backref="author", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="author", lazy=True, cascade="all, delete-orphan")
    liked_posts = db.relationship("Like", backref="user", lazy=True, cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", backref="user", lazy=True, cascade="all, delete-orphan")
    notifications_received = db.relationship(
        "Notification", foreign_keys="Notification.recipient_id",
        backref="recipient", lazy=True, cascade="all, delete-orphan"
    )
    notifications_sent = db.relationship(
        "Notification", foreign_keys="Notification.actor_id",
        backref="actor", lazy=True
    )

    following = db.relationship(
        "User", secondary=follows,
        primaryjoin=(follows.c.follower_id == id),
        secondaryjoin=(follows.c.followed_id == id),
        backref=db.backref("followers", lazy="dynamic"),
        lazy="dynamic",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_following(self, user):
        return self.following.filter(follows.c.followed_id == user.id).count() > 0

    def has_bookmarked(self, post):
        return Bookmark.query.filter_by(user_id=self.id, post_id=post.id).first() is not None

    @property
    def unread_notifications_count(self):
        return Notification.query.filter_by(recipient_id=self.id, is_read=False).count()

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(2200), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    likes = db.relationship("Like", backref="post", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="post", lazy=True, cascade="all, delete-orphan", order_by="Comment.created_at.asc()")
    bookmarks = db.relationship("Bookmark", backref="post", lazy=True, cascade="all, delete-orphan")

    def is_liked_by(self, user):
        return Like.query.filter_by(user_id=user.id, post_id=self.id).first() is not None

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="unique_user_post_like"),)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="unique_user_post_bookmark"),)

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(180), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    author = db.relationship("User", backref=db.backref("stories", lazy=True, cascade="all, delete-orphan"))

    @property
    def is_expired(self):
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created < utcnow() - timedelta(hours=24)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(30), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    post = db.relationship("Post")

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    members = db.relationship("ConversationMember", back_populates="conversation", cascade="all, delete-orphan")
    messages = db.relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at.asc()")

    def contains_user(self, user_id):
        return any(member.user_id == user_id for member in self.members)

    def other_member(self, user_id):
        return next((member.user for member in self.members if member.user_id != user_id), None)

class ConversationMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    last_read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    conversation = db.relationship("Conversation", back_populates="members")
    user = db.relationship("User", backref=db.backref("conversation_memberships", lazy=True))
    __table_args__ = (db.UniqueConstraint("conversation_id", "user_id", name="unique_conversation_member"),)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    conversation = db.relationship("Conversation", back_populates="messages")
    sender = db.relationship("User", backref=db.backref("messages_sent", lazy=True))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    reason = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(20), default="open", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("reporter_id", "post_id", name="unique_reporter_post"),)

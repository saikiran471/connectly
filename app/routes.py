import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc
from . import db
from .models import User, Post, Like, Comment, Bookmark, Story, Notification, Conversation, ConversationMember, Message, Report
from .forms import RegisterForm, LoginForm, PostForm, StoryForm, CommentForm, ProfileForm, MessageForm, ReportForm

main = Blueprint("main", __name__)

def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

def save_upload(file):
    if not file or not file.filename or not allowed_image(file.filename):
        raise ValueError("Choose a valid image file.")
    ext = Path(secure_filename(file.filename)).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return filename

def notify(recipient_id, actor_id, kind, post_id=None):
    if recipient_id and recipient_id != actor_id:
        db.session.add(Notification(recipient_id=recipient_id, actor_id=actor_id, kind=kind, post_id=post_id))

def conversation_for_users(user_a, user_b):
    if user_a.id == user_b.id:
        return None
    candidate_ids = [m.conversation_id for m in ConversationMember.query.filter_by(user_id=user_a.id).all()]
    for conv in Conversation.query.filter(Conversation.id.in_(candidate_ids)).all():
        if conv.contains_user(user_b.id) and len(conv.members) == 2:
            return conv
    conv = Conversation()
    db.session.add(conv)
    db.session.flush()
    db.session.add_all([
        ConversationMember(conversation_id=conv.id, user_id=user_a.id),
        ConversationMember(conversation_id=conv.id, user_id=user_b.id),
    ])
    db.session.commit()
    return conv

@main.route("/")
def index():
    return redirect(url_for("main.feed" if current_user.is_authenticated else "main.login"))

@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip().lower(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Your account is ready. Welcome to Connectly!", "success")
        return redirect(url_for("main.feed"))
    return render_template("register.html", form=form)

@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.feed"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("You are logged in.", "success")
            next_page = request.args.get("next", "")
            if next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("main.feed"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", form=form)

@main.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have logged out.", "info")
    return redirect(url_for("main.login"))

@main.route("/feed")
@login_required
def feed():
    page = max(request.args.get("page", 1, type=int), 1)
    followed_ids = [u.id for u in current_user.following.all()]
    feed_ids = followed_ids + [current_user.id]
    query = Post.query.filter(Post.user_id.in_(feed_ids)).order_by(Post.created_at.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    posts = pagination.items
    comment_forms = {post.id: CommentForm(prefix=f"comment-{post.id}") for post in posts}
    post_form, story_form = PostForm(), StoryForm()
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    stories = Story.query.order_by(Story.created_at.desc()).limit(80).all()
    stories = [story for story in stories if not story.is_expired and (story.user_id in feed_ids)]
    return render_template("feed.html", posts=posts, pagination=pagination,
        post_form=post_form, story_form=story_form, comment_forms=comment_forms, stories=stories)

@main.route("/posts/create", methods=["POST"])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        try:
            filename = save_upload(form.image.data)
        except ValueError:
            flash("Choose a valid image (PNG, JPG, GIF, or WEBP; max 5 MB).", "error")
            return redirect(url_for("main.feed"))
        post = Post(image_filename=filename, caption=(form.caption.data or "").strip(), author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your post has been shared.", "success")
    else:
        flash("Check the image and caption, then try again.", "error")
    return redirect(url_for("main.feed"))

@main.route("/stories/create", methods=["POST"])
@login_required
def create_story():
    form = StoryForm()
    if form.validate_on_submit():
        try:
            filename = save_upload(form.image.data)
        except ValueError:
            flash("Choose a valid image file.", "error")
            return redirect(url_for("main.feed"))
        db.session.add(Story(image_filename=filename, caption=(form.caption.data or "").strip(), author=current_user))
        db.session.commit()
        flash("Your story is live for 24 hours.", "success")
    else:
        flash("Choose an image and keep the caption under 180 characters.", "error")
    return redirect(url_for("main.feed"))

@main.route("/stories/<int:story_id>/delete", methods=["POST"])
@login_required
def delete_story(story_id):
    story = db.session.get(Story, story_id) or abort(404)
    if story.user_id != current_user.id:
        abort(403)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], story.image_filename)
    db.session.delete(story)
    db.session.commit()
    if os.path.exists(path):
        os.remove(path)
    flash("Story deleted.", "info")
    return redirect(url_for("main.feed"))

@main.route("/posts/<int:post_id>/like", methods=["POST"])
@login_required
def toggle_like(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post.id))
        notify(post.user_id, current_user.id, "liked your post", post.id)
    db.session.commit()
    return redirect(request.referrer or url_for("main.feed"))

@main.route("/posts/<int:post_id>/bookmark", methods=["POST"])
@login_required
def toggle_bookmark(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    bookmark = Bookmark.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    if bookmark:
        db.session.delete(bookmark)
        flash("Removed from saved posts.", "info")
    else:
        db.session.add(Bookmark(user_id=current_user.id, post_id=post.id))
        flash("Post saved.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("main.feed"))

@main.route("/saved")
@login_required
def saved_posts():
    bookmarks = Bookmark.query.filter_by(user_id=current_user.id).order_by(Bookmark.created_at.desc()).all()
    return render_template("saved.html", bookmarks=bookmarks)

@main.route("/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    if post.user_id != current_user.id:
        abort(403)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], post.image_filename)
    db.session.delete(post)
    db.session.commit()
    if os.path.exists(path):
        os.remove(path)
    flash("Post deleted.", "info")
    return redirect(request.referrer or url_for("main.feed"))

@main.route("/posts/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    form = CommentForm(prefix=f"comment-{post_id}")
    if form.validate_on_submit():
        comment = Comment(body=form.body.data.strip(), author=current_user, post=post)
        db.session.add(comment)
        notify(post.user_id, current_user.id, "commented on your post", post.id)
        db.session.commit()
    else:
        flash("Comments must contain 1–500 characters.", "error")
    return redirect(request.referrer or url_for("main.feed"))

@main.route("/users/<string:username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username.lower()).first_or_404()
    form = ProfileForm()
    return render_template("profile.html", profile_user=user, form=form)

@main.route("/profile/edit", methods=["POST"])
@login_required
def edit_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.bio = (form.bio.data or "").strip()
        db.session.commit()
        flash("Profile updated.", "success")
    else:
        flash("Bio must be 160 characters or fewer.", "error")
    return redirect(url_for("main.profile", username=current_user.username))

@main.route("/users/<string:username>/follow", methods=["POST"])
@login_required
def toggle_follow(username):
    user = User.query.filter_by(username=username.lower()).first_or_404()
    if user.id == current_user.id:
        flash("You cannot follow yourself.", "error")
    elif current_user.is_following(user):
        current_user.following.remove(user)
        db.session.commit()
        flash(f"You unfollowed @{user.username}.", "info")
    else:
        current_user.following.append(user)
        notify(user.id, current_user.id, "started following you")
        db.session.commit()
        flash(f"You followed @{user.username}.", "success")
    return redirect(request.referrer or url_for("main.profile", username=user.username))

@main.route("/explore")
@login_required
def explore():
    q = request.args.get("q", "").strip().lower()
    users = []
    if q:
        users = User.query.filter(or_(User.username.contains(q), User.bio.contains(q))).order_by(User.username.asc()).limit(30).all()
    posts = Post.query.order_by(Post.created_at.desc()).limit(30).all()
    return render_template("explore.html", users=users, posts=posts, q=q)

@main.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    for item in items:
        item.is_read = True
    db.session.commit()
    return render_template("notifications.html", items=items)

@main.route("/messages")
@login_required
def messages():
    memberships = ConversationMember.query.filter_by(user_id=current_user.id).all()
    conversations = []
    for membership in memberships:
        conv = membership.conversation
        other = conv.other_member(current_user.id)
        last_message = conv.messages[-1] if conv.messages else None
        conversations.append((conv, other, last_message))
    conversations.sort(key=lambda row: row[2].created_at if row[2] else row[0].created_at, reverse=True)
    users = User.query.filter(User.id != current_user.id).order_by(User.username.asc()).limit(100).all()
    return render_template("messages.html", conversations=conversations, users=users)

@main.route("/messages/start/<string:username>", methods=["POST"])
@login_required
def start_message(username):
    other = User.query.filter_by(username=username.lower()).first_or_404()
    if other.id == current_user.id:
        flash("You cannot message yourself.", "error")
        return redirect(url_for("main.messages"))
    conv = conversation_for_users(current_user, other)
    return redirect(url_for("main.conversation", conversation_id=conv.id))

@main.route("/messages/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def conversation(conversation_id):
    conv = db.session.get(Conversation, conversation_id) or abort(404)
    if not conv.contains_user(current_user.id):
        abort(403)
    membership = ConversationMember.query.filter_by(conversation_id=conv.id, user_id=current_user.id).first()
    membership.last_read_at = datetime.now(timezone.utc)
    db.session.commit()
    form = MessageForm()
    if form.validate_on_submit():
        message = Message(conversation=conv, sender=current_user, body=form.body.data.strip())
        db.session.add(message)
        db.session.commit()
        # The standard POST path works without websockets; clients can refresh to see it.
        return redirect(url_for("main.conversation", conversation_id=conv.id))
    return render_template("conversation.html", conversation=conv, other=conv.other_member(current_user.id), form=form)

@main.route("/posts/<int:post_id>/report", methods=["POST"])
@login_required
def report_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    reason = request.form.get("reason", "").strip()
    if len(reason) < 5 or len(reason) > 300:
        flash("Please provide a reason between 5 and 300 characters.", "error")
    elif post.user_id == current_user.id:
        flash("You cannot report your own post.", "error")
    elif Report.query.filter_by(reporter_id=current_user.id, post_id=post.id).first():
        flash("You already reported this post.", "info")
    else:
        db.session.add(Report(reporter_id=current_user.id, post_id=post.id, reason=reason))
        db.session.commit()
        flash("Report submitted for review.", "success")
    return redirect(request.referrer or url_for("main.feed"))

@main.route("/api/health")
def api_health():
    return jsonify(status="ok", app="Connectly")

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from .models import User

class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=30)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match.")
    ])
    submit = SubmitField("Create account")
    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip().lower()).first():
            raise ValidationError("That username is already taken.")
    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("That email is already registered.")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")

class PostForm(FlaskForm):
    image = FileField("Photo", validators=[
        FileRequired(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Images only.")
    ])
    caption = TextAreaField("Caption", validators=[Length(max=2200)])
    submit = SubmitField("Share")

class StoryForm(FlaskForm):
    image = FileField("Story photo", validators=[
        FileRequired(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "Images only.")
    ])
    caption = StringField("Story caption", validators=[Length(max=180)])
    submit = SubmitField("Add story")

class CommentForm(FlaskForm):
    body = StringField("Add a comment", validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField("Post")

class ProfileForm(FlaskForm):
    bio = TextAreaField("Bio", validators=[Length(max=160)])
    submit = SubmitField("Save profile")

class MessageForm(FlaskForm):
    body = StringField("Message", validators=[DataRequired(), Length(min=1, max=2000)])
    submit = SubmitField("Send")

class ReportForm(FlaskForm):
    reason = StringField("Reason", validators=[DataRequired(), Length(min=5, max=300)])
    submit = SubmitField("Report post")

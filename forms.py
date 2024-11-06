from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, FileField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, NumberRange
from flask_wtf.file import FileField, FileAllowed

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UploadBookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    price_per_day = FloatField('Price per Day', validators=[DataRequired()])
    cover_image = FileField('Upload Cover Image', validators=[FileAllowed(['jpg', 'png'])])
    txt_file = FileField('Upload Book (TXT only)', validators=[DataRequired(), FileAllowed(['txt'], 'txt files only!')])
    tags = StringField('Tags (comma-separated)')
    submit = SubmitField('Upload Book')

class ReviewForm(FlaskForm):
    review_text = TextAreaField('Review', validators=[DataRequired()])
    rating = SelectField('Rating', choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Submit Review')

class RentalForm(FlaskForm):
    book_id = SelectField('Select Book', coerce=int, validators=[DataRequired()])
    rental_days = IntegerField('Rental Days', validators=[DataRequired(), NumberRange(min=1, message='Must be at least 1')])
    submit = SubmitField('Confirm Rental')

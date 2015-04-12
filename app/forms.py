from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class LoginForm(Form):
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	remember_me = BooleanField('remember_me', default = False)

class CreateUserForm(Form):
	username = TextField(
			'username',
			validators=[DataRequired(), Length(min=4, max=8)]
	)
	email = TextField(
			'email',
			validators=[DataRequired(), Email(message=None), Length(min=6, max=20)]
	)
	password = PasswordField(
			'password',
			validators=[DataRequired(), Length(min=6, max=25)]
	)
	confirm = PasswordField(
			'Repeat password',
			validators=[
				DataRequired(), EqualTo('password', message='Passwords must match.')
			]
	)

class addPart(Form):
	part = TextField('part', validators=[DataRequired()])
	manufacturer = TextField('manufacturer', validators=[DataRequired()])

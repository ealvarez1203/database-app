from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField, IntegerField, SelectField, DateField, validators
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_wtf.file import FileField

class LoginForm(Form):
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	remember_me = BooleanField('remember_me', default = False)

class CreateUserForm(Form):
	username = TextField(
			'username',
			validators=[DataRequired(), Length(min=4, max=10)]
	)
	email = TextField(
			'email',
			validators=[DataRequired(), Email(message=None), Length(min=6, max=20)]
	)
	password = PasswordField(
			'password',
			validators=[DataRequired(), Length(min=6, max=10)]
	)
	confirm = PasswordField(
			'Repeat password',
			validators=[
				DataRequired(), EqualTo('password', message='Passwords must match.')
			]
	)

class AddPart(Form):
	PO = TextField('PO', validators=[DataRequired()], id='PO')
	PR = TextField('PR', validators=[DataRequired()], id='PR')
	part = SelectField('part', coerce=unicode, validators=[DataRequired()], id="parts")
	project_name = TextField('project_name', validators=[DataRequired()], id="project_names")
	requestor = TextField('requestor', validators=[DataRequired()], id="requestors")
	supplier = TextField('supplier', validators=[DataRequired()], id="suppliers")
	supplier_contact = TextField('supplier_contact', validators=[DataRequired()], id="supplier_contacts")
	item_description = TextField('item_description', validators=[DataRequired()], id="item_descriptions")
	CPN = TextField('CPN', id="CPN")
	PID = TextField('PID', id='PID')
	manufacturer_part_num = TextField('manufacturer_part_num', validators=[DataRequired()], id='manufacturer_part_num')
	SN = TextField('SN', filters = [lambda x: x or None])
	submit_date = DateField('submit_date', format='%m/%d/%Y', id='submit_date')
	tracking = TextField('tracking', validators=[DataRequired()], id='tracking')
	status = SelectField('status', coerce=unicode, validators=[validators.optional()])
	location = TextField('location', validators=[DataRequired()], id='location')
	qty = IntegerField('qty', validators=[validators.NumberRange(min=1, max=None, message='Please Enter a Positive Interger')])


class CheckoutPart(Form):
	project = TextField('project', validators=[DataRequired()], id='project')
	details = TextField('details', validators=[DataRequired()], id='details')
	return_date = DateField('return_date', format='%m/%d/%Y', id='return_date', validators=[validators.Optional()])
	location = TextField('location', validators=[DataRequired()], id='location')

class UpdatePart(Form):
	PO = TextField('PO', id='PO')
	PR = TextField('PR', id='PR')
	part = TextField('part', id="parts")
	project_name = TextField('project_name', id="project_names")
	requestor = TextField('requestor', id="requestors")
	supplier = TextField('supplier', id="suppliers")
	supplier_contact = TextField('supplier_contact', id="supplier_contacts")
	item_description = TextField('item_description', id="item_descriptions")
	CPN = TextField('CPN', id='CPN')
	PID = TextField('PID', id='PID')
	SN = TextField('SN', id='SN')
	manufacturer_part_num = TextField('manufacturer_part_num', id='manufacturer_part_num')
	submit_date = DateField('submit_date', format='%m/%d/%Y', id='submit_date', validators=[validators.Optional()])
	tracking = TextField('tracking', id='tracking')
	#status = SelectField('status', coerce=unicode, validators=[validators.optional()])
	location = TextField('location', id='location')

class UploadFile(Form):
	excelFile = FileField('excelFile')


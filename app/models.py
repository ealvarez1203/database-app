from app import db
from app import bcrypt

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(db.Model):
	
	__tablename__ = "users"

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(20), nullable=False, unique=True)
	password = db.Column(db.String(20), nullable=False)
	email = db.Column(db.String(20), nullable=True, unique=True)
	parts = relationship("Parts", backref="user")

	def __init__(self, name, password, email):
		self.name = name
		self.password = bcrypt.generate_password_hash(password)
		self.email = email

	def is_authenticated(self):
		return True

	def is_active(self):
		return True

	def is_anonymous(self):
		return False

	def get_id(self):
		return unicode(self.id)

	def __repr__(self):
		return '<name {}>'.format(self.name)	

class Parts(db.Model):

	__tablename__ = 'parts'

	id = db.Column(db.Integer, primary_key=True)
	PO = db.Column(db.String(20), nullable=False)
	PR = db.Column(db.String(20), nullable=False)
	part = db.Column(db.String(20), nullable=False)
	project_name = db.Column(db.String(20), nullable=False)
	requestor = db.Column(db.String(20), nullable=False)
	supplier = db.Column(db.String(30), nullable=False)
	supplier_contact = db.Column(db.String(30), nullable=False)
	item_description= db.Column(db.String(200), nullable=True)
	CPN = db.Column(db.String(20), nullable=True)
	PID = db.Column(db.String(20), nullable=True)
	manufacturer_part_num = db.Column(db.String(30), nullable=True)
	submit_date = db.Column(db.String(10), nullable=True)
	tracking = db.Column(db.String(30), nullable=True)
	status = db.Column(db.String(20), nullable=False)
	location = db.Column(db.String(20), nullable=True)
	checkout_date = db.Column(db.String(20), nullable=True)
	return_date= db.Column(db.String(20), nullable=True)
	times_used = db.Column(db.Integer, nullable=False)
	current_user = db.Column(db.Integer, ForeignKey('users.id'), nullable=True)
	current_project = db.Column(db.String(20), nullable=True)

	def __init__(
		self, 
		PO, 
		PR, 
		part, 
		project_name, 
		requestor, 
		supplier, 
		supplier_contact,
		item_description,
		CPN,
		PID,
		manufacturer_part_num,
		submit_date,
		tracking,
		status, 
		location
		):
		self.PO = PO
		self.PR = PR
		self.part = part
		self.project_name = project_name
		self.requestor = requestor
		self.supplier = supplier
		self.supplier_contact = supplier_contact
		self.item_description = item_description
		self.CPN = CPN
		self.PID = PID
		self.manufacturer_part_num = manufacturer_part_num
		self.submit_date = submit_date
		self.tracking = tracking
		self.status = status
		self.location = location
		self.times_used = 0

	def __repr__(self):
		return '{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}'.format(
			self.PO.encode('utf-8'), 
			self.PR.encode('utf-8'), 
			self.part.encode('utf-8'), 
			self.project_name.encode('utf-8'), 
			self.requestor.encode('utf-8'), 
			self.supplier.encode('utf-8'), 
			self.supplier_contact.encode('utf-8'),
			self.item_description.encode('utf-8'),
			self.CPN.encode('utf-8'),
			self.PID.encode('utf-8'),
			self.manufacturer_part_num.encode('utf-8'),
			self.submit_date.encode('utf-8'),
			self.tracking.encode('utf-8'), 
			self.status.encode('utf-8'),
			self.times_used.encode('utf-8')
			)


class History(db.Model):

	__tablename__ = 'history'

	id = db.Column(db.Integer, primary_key= True)
	Part_SN = db.Column(db.String(20), ForeignKey('parts.id'))
	project = db.Column(db.String(20), nullable=False)
	user= db.Column(db.String(20), nullable=False)
	checkout_date = db.Column(db.String(10), nullable=False)
	return_date = db.Column(db.String(10), nullable=False)
	detail = db.Column(db.String(30), nullable=True)	

	def __init__(self, serial, project, user, checkout_date, return_date, detail):	
		self.Part_SN = serial
		self.project = project
		self.user = user
		self.checkout_date = checkout_date
		self.return_date = return_date
		self.detail = detail

	def __repr__(self):
		return '{}, {}, {}, {}, {}'.format(self.Part_SN, self.project, self.user, self.checkout_date, self.return_date)

		
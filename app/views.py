from flask import render_template, flash, redirect, url_for, request
from flask.ext.login import login_user, login_required, logout_user, current_user
from app import app, db, login_manager, bcrypt 
from forms import *
from models import User, Parts, History, Requests
import time, xlrd, os
from werkzeug import secure_filename
from functools import wraps
from sqlalchemy import or_
from sqlalchemy.sql.expression import func


@app.errorhandler(404)
def not_found_error(error):
	return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
	db.session.rollback()
	return render_template('500.html'), 500


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


@login_manager.user_loader
def load_user(user_id):
	return User.query.filter(User.id == int(user_id)).first()


def allowed_users(*users):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.name not in users:
            	flash('Sorry, You Currently you Don\'t Have Permission to Access this Page')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return wrapped
    return wrapper


# route for handling the login page logic
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	form = LoginForm(request.form)
	if request.method == 'POST':
		if form.validate_on_submit():
			user = User.query.filter_by(name = request.form['username']).first()
			if user is not None and bcrypt.check_password_hash(user.password, request.form['password']):
				login_user(user)
				flash("You were logged in!")
				return redirect(url_for('home'))
			else:
				error = 'Invalid Credentials. Please try again.'
	return render_template('login.html', form=form, error=error)

@app.route('/logout/')
def logout():
	logout_user()
	flash('You were logged out.')
	return redirect(url_for('login'))

@app.route('/register/', methods=['GET', 'POST']) 
def create_user():
	error = None
	form = CreateUserForm()
	if form.validate_on_submit():
		if User.query.filter_by(name=form.username.data).first() or User.query.filter_by(email=form.email.data).first():
			error = 'Username already exist. Please try using a different username or email'
		else:	
			user = User(
				name=form.username.data,
				email=form.email.data,
				password=form.password.data
			)
			db.session.add(user)
			db.session.commit()
			login_user(user)
			app.logger.info('User :%s was registered'%current_user.name)
			return redirect(url_for('home'))
	return render_template('create_user.html', form=form, error=error)

@app.route('/home')
@login_required
def home():
	return render_template('main.html', user=current_user.name)


@app.route('/History/<serialNumber>/')
@login_required
def show_history(serialNumber):
	cur = db.engine.execute('SELECT project, user, checkout_date, return_date, detail FROM History WHERE Part_SN=:s', s=serialNumber)
	history = [dict(project=row[0], user=row[1], checkout_date=row[2], return_date=row[3], detail=row[4]) for row in cur.fetchall()]
	return render_template('history.html', history=history)


@app.route('/UserInfo/<username>/')
@login_required
def show_user_info(username):
	user = User.query.filter_by(name=username).first()
	user = dict(id=user.id,
				name=user.name,
				email=user.email
			)
	return render_template('user_info.html', User=user)


@app.route('/Part/<id>/')
@login_required
def show_part_info(id):
	part = Parts.query.get(id)
	part = dict(id=part.id, 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						manufacturer_part_num=part.manufacturer_part_num,
						SN=part.SN, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status,
						location=part.location, 
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) 
	#   add quantity variable to each update_part
	kwargs = {'PR':part['PR'], 
			'PO':part['PO'], 
			'part':part['part'], 
			'project_name':part['project_name'], 
			'requestor':part['requestor'],
			'supplier':part['supplier'], 
			'supplier_contact':part['supplier_contact'], 
			'item_description':part['item_description'], 
			'CPN':part['CPN'], 
			'PID':part['PID'], 
			'manufacturer_part_num':part['manufacturer_part_num'], 
			'submit_date':part['submit_date'], 
			'tracking':part['tracking'], 
			'status':part['status'], 
			'location':part['location'], 
			'checkout_date':part['checkout_date'], 
			'return_date':part['return_date'], 
			'times_used':part['times_used'], 
			'current_user':part['current_user'], 
			'current_project':part['current_project'], 
			'SN':part['SN']
		}
	qty = Parts.query.filter_by(**kwargs).count()
	part['qty'] = qty 
	return render_template('part_info.html', part=part, user=current_user.name)


@app.route('/Upload', methods=['GET','POST'])
@login_required
@allowed_users('admin')
def upload_file():
	error=None
	if request.method == 'POST':
	        file = request.files['file'] # file object from form
	        if file and allowed_file(file.filename): #checks is file is uploaded and has valid format
	            filename = secure_filename(file.filename) #verify authenticy of file
	            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) #save file in programs /tmp directory
	            workbook = xlrd.open_workbook(os.path.join(app.config['UPLOAD_FOLDER'], filename))	#open workbook
	            sheet = workbook.sheet_by_index(int(request.form.get('sheet'))) #select sheet number
	            keys = [sheet.cell(0, col_index).value for col_index in xrange(sheet.ncols)] #obtain column names
	            dict_list = [] 
	            for row_index in xrange(1, sheet.nrows): #iterate through all rows of sheet and store them in dict_list
	            	d = dict((keys[col_index], sheet.cell(row_index, col_index).value) for col_index in xrange(sheet.ncols))
	            	dict_list.append(d)
	            try:
	            	for i in dict_list: # import to database
	            		for j in range(0, int(i['QTY'])):
	            			db.session.add(Parts((int(i['PO#']) if isinstance(i['PO#'], float) else i['PO#']),
	    										(int(i['PR#']) if isinstance(i['PR#'], float) else i['PR#']), 
												i['PART'], 
												i['PROJECT NAME'],
												i['REQUESTOR'],
												i['SUPPLIER NAME'],
												i['SUPPLIER CONTACT'],
												i['ITEM DESCRIPTION'],
												(int(i['CPN']) if isinstance(i['CPN'], float) else i['CPN']),
												(int(i['PID']) if isinstance(i['PID'], float) else i['PID']),
												(int(i['MFG PART#']) if isinstance(i['MFG PART#'], float) else i['MFG PART#']),
												(int(i['S/N']) if isinstance(i['S/N'], float) else i['S/N']),
												time.strftime("%m/%d/%Y"), # xlrd function needed
												(int(i['TRACKING#']) if isinstance(i['TRACKING#'], float) else i['TRACKING#']), 
												'Unavailable', 
												i['LOCATION']
					          			))
	            		app.logger.info('| ACTION: upload | PART: %s | QUANTITY: %s | BY USER: %s'%(i['PART'], int(i['QTY']), current_user.name))	
	            	db.session.commit()
	            	
	            	flash('The Spreadsheet was Sucessfully Uploaded into the Database!')
	            except KeyError, key:
	            	error = 'Column missing: %s'%key
	            	return render_template('upload_file.html', error=error)

	            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename)) #remove file from tmp folder
	            return redirect(url_for('upload_file'))
	        else:
	        	error= "Wrong File Format"

	return render_template('upload_file.html', error=error, user=current_user.name)


@app.route('/inventory')
def inventory():
	parts = Parts.query.group_by(Parts.PR, 
								Parts.PO, 
								Parts.part, 
								Parts.project_name, 
								Parts.requestor, 
								Parts.supplier, 
								Parts.supplier_contact,
								Parts.item_description, 
								Parts.CPN, Parts.PID, 
								Parts.manufacturer_part_num, 
								Parts.SN, 
								Parts.submit_date, 
								Parts.tracking, 
								Parts.status,
								Parts.location, 
								Parts.checkout_date, 
								Parts.return_date, 
								Parts.times_used, 
								Parts.current_user, 
								Parts.current_project
							).all()

	parts = [dict(id=part.id, 
					PR=part.PR, 
					PO=part.PO, 
					part=part.part, 
					project_name=part.project_name,
					requestor=part.requestor, 
					supplier=part.supplier, 
					supplier_contact=part.supplier_contact, 
					item_description=part.item_description, 
					CPN=part.CPN, 
					PID=part.PID, 
					SN=part.SN,
					manufacturer_part_num=part.manufacturer_part_num, 
					submit_date=part.submit_date, 
					tracking=part.tracking, 
					status=part.status, 
					location=part.location,
					checkout_date=part.checkout_date,
					return_date=part.return_date,
					times_used=part.times_used,
					current_user=part.current_user,
					current_project=part.current_project
				) for part in parts]

	#"""Add quantity variable to each delete_parts"""
	for i in parts:
		kwargs = {'PR':i['PR'], 
					'PO':i['PO'], 
					'part':i['part'], 
					'project_name':i['project_name'], 
					'requestor':i['requestor'], 
					'supplier':i['supplier'], 
					'supplier_contact':i['supplier_contact'], 
					'item_description':i['item_description'], 
					'CPN':i['CPN'], 'PID':i['PID'], 
					'manufacturer_part_num':i['manufacturer_part_num'], 
					'submit_date':i['submit_date'], 
					'tracking':i['tracking'], 
					'status':i['status'], 
					'location':i['location'], 
					'checkout_date':i['checkout_date'], 
					'return_date':i['return_date'], 
					'times_used':i['times_used'],
					'current_user':i['current_user'], 
					'current_project':i['current_project'], 
					'SN':i['SN']
				}
		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 
	return render_template('inventory.html', parts=parts)


@app.route('/add_part', methods=['GET', 'POST'])
@login_required
def add_part():
	error = None
	POs = ["%s" %i for i in db.session.query(Parts.PO).group_by(Parts.PO).all()]
	POs = [x.encode('utf-8') for x in POs]
	PRs = ["%s" %i for i in db.session.query(Parts.PR).group_by(Parts.PR).all()]
	PRs = [x.encode('utf-8') for x in PRs]
	project_names = ["%s" %i for i in db.session.query(Parts.project_name).group_by(Parts.project_name).all()]
	project_names = [x.encode('utf-8') for x in project_names]
	current_projects = ["%s" %i for i in db.session.query(Parts.current_project).group_by(Parts.current_project).all()]
	current_projects = [x.encode('utf-8') for x in current_projects]
	requestors = ["%s" %i for i in db.session.query(Parts.requestor).group_by(Parts.requestor).all()]
	requestors = [x.encode('utf-8') for x in requestors]
	suppliers = ["%s" %i for i in db.session.query(Parts.supplier).group_by(Parts.supplier).all()]
	suppliers = [x.encode('utf-8') for x in suppliers]
	supplier_contacts = ["%s" %i for i in db.session.query(Parts.supplier_contact).group_by(Parts.supplier_contact).all()]
	supplier_contacts = [x.encode('utf-8') for x in supplier_contacts]
	item_descriptions = ["%s" %i for i in db.session.query(Parts.item_description).group_by(Parts.item_description).all()]
	item_descriptions = [x.encode('utf-8') for x in item_descriptions]
	project_names = project_names + current_projects # merge these two lists
	CPNs = ["%s" %i for i in db.session.query(Parts.CPN).group_by(Parts.CPN).all()]
	CPNs = [x.encode('utf-8') for x in CPNs]
	PIDs = ["%s" %i for i in db.session.query(Parts.PID).group_by(Parts.PID).all()]
	PIDs = [x.encode('utf-8') for x in PIDs]
	manufacturer_part_nums = ["%s" %i for i in db.session.query(Parts.manufacturer_part_num).group_by(Parts.manufacturer_part_num).all()]
	manufacturer_part_nums = [x.encode('utf-8') for x in manufacturer_part_nums]
	tracking = ["%s" %i for i in db.session.query(Parts.tracking).group_by(Parts.tracking).all()]
	tracking = [x.encode('utf-8') for x in tracking]
	location = ["%s" %i for i in db.session.query(Parts.location).group_by(Parts.location).all()]
	location = [x.encode('utf-8') for x in location]

	form = AddPart(request.form)
	form.status.choices = [('Available', 'Available'), 
						('Unavailable', 'Unavailable')
					]
	form.part.choices = [('DIMM', 'DIMM'), 
						('CPU', 'CPU'), 
						('CABLES', 'CABLES'), 
						('CHASSIS', 'CHASSIS'), 
						('HDD', 'HDD'),
						('MEZZ-CARD', 'MEZZ-CARD'), 
						('PROTOTYPE', 'PROTOTYPE'), 
						('GPU', 'GPU'), 
						('PSU', 'PSU'), 
						('RAID-UNIT', 'RAID-UNIT'), 
						('TPM', 'TPM')
					]

	if request.method == 'POST' and form.validate():
		if form.SN.data is not None and int(form.qty.data) > 1:
			error = 'If S/N field is used, Qty must be 1'
		else:
			for i in range(0, int(form.qty.data)):
				part = Parts(
					PO = form.PO.data,
					PR = form.PR.data,
					part = form.part.data,
					project_name = form.project_name.data,
					requestor = form.requestor.data,
					supplier = form.supplier.data,
					supplier_contact = form.supplier_contact.data,
					item_description = form.item_description.data,
					CPN = form.CPN.data,
					PID = form.PID.data,
					manufacturer_part_num = form.manufacturer_part_num.data,
					SN = form.SN.data,
					submit_date = form.submit_date.raw_data[0],
					tracking = form.tracking.data,
					status = form.status.data,
					location = form.location.data
					)
				db.session.add(part)
			db.session.commit()
			app.logger.info('| ACTION: add | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(part.part, part.id-(int(form.qty.data)-1), form.qty.data, current_user.name))
			flash("The Part was Added to the Database!")
			return redirect(url_for('add_part'))
	return render_template('add_part.html', form=form, POs=POs, PRs=PRs, project_names=project_names, requestors=requestors,
		suppliers=suppliers, supplier_contacts=supplier_contacts, item_descriptions=item_descriptions, CPNs=CPNs, PIDs=PIDs,
		manufacturer_part_nums=manufacturer_part_nums, tracking=tracking, location=location, error=error)


@app.route('/add_more/<part_id>/', methods=['GET', 'POST'])
@login_required
@allowed_users('admin')
def add_more(part_id):
	error = None
	# project names options for autocomplete field
	POs = ["%s" %i for i in db.session.query(Parts.PO).group_by(Parts.PO).all()]
	POs = [x.encode('utf-8') for x in POs]
	PRs = ["%s" %i for i in db.session.query(Parts.PR).group_by(Parts.PR).all()]
	PRs = [x.encode('utf-8') for x in PRs]
	parts = ["%s" %i for i in db.session.query(Parts.part).group_by(Parts.part).all()]
	parts = [x.encode('utf-8') for x in parts]
	project_names = ["%s" %i for i in db.session.query(Parts.project_name).group_by(Parts.project_name).all()]
	project_names = [x.encode('utf-8') for x in project_names]
	current_projects = ["%s" %i for i in db.session.query(Parts.current_project).group_by(Parts.current_project).all()]
	current_projects = [x.encode('utf-8') for x in current_projects]
	requestors = ["%s" %i for i in db.session.query(Parts.requestor).group_by(Parts.requestor).all()]
	requestors = [x.encode('utf-8') for x in requestors]
	suppliers = ["%s" %i for i in db.session.query(Parts.supplier).group_by(Parts.supplier).all()]
	suppliers = [x.encode('utf-8') for x in suppliers]
	supplier_contacts = ["%s" %i for i in db.session.query(Parts.supplier_contact).group_by(Parts.supplier_contact).all()]
	supplier_contacts = [x.encode('utf-8') for x in supplier_contacts]
	item_descriptions = ["%s" %i for i in db.session.query(Parts.item_description).group_by(Parts.item_description).all()]
	item_descriptions = [x.encode('utf-8') for x in item_descriptions]
	project_names = project_names + current_projects # merge these two lists
	CPNs = ["%s" %i for i in db.session.query(Parts.CPN).group_by(Parts.CPN).all()]
	CPNs = [x.encode('utf-8') for x in CPNs]
	PIDs = ["%s" %i for i in db.session.query(Parts.PID).group_by(Parts.PID).all()]
	PIDs = [x.encode('utf-8') for x in PIDs]
	manufacturer_part_nums = ["%s" %i for i in db.session.query(Parts.manufacturer_part_num).group_by(Parts.manufacturer_part_num).all()]
	manufacturer_part_nums = [x.encode('utf-8') for x in manufacturer_part_nums]
	tracking = ["%s" %i for i in db.session.query(Parts.tracking).group_by(Parts.tracking).all()]
	tracking = [x.encode('utf-8') for x in tracking]
	location = ["%s" %i for i in db.session.query(Parts.location).group_by(Parts.location).all()]
	location = [x.encode('utf-8') for x in location]

	#   obtain ids from arg list
	part = Parts.query.get(part_id)
	part = dict(id=part.id, 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						manufacturer_part_num=part.manufacturer_part_num,
						SN =part.SN, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status,
						location=part.location, 
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) 
	#   add quantity variable to each update_part
	kwargs = {'PR':part['PR'], 
			'PO':part['PO'], 
			'part':part['part'], 
			'project_name':part['project_name'], 
			'requestor':part['requestor'],
			'supplier':part['supplier'], 
			'supplier_contact':part['supplier_contact'], 
			'item_description':part['item_description'], 
			'CPN':part['CPN'], 
			'PID':part['PID'], 
			'manufacturer_part_num':part['manufacturer_part_num'], 
			'submit_date':part['submit_date'], 
			'tracking':part['tracking'], 
			'status':part['status'], 
			'location':part['location'], 
			'checkout_date':part['checkout_date'], 
			'return_date':part['return_date'], 
			'times_used':part['times_used'], 
			'current_user':part['current_user'], 
			'current_project':part['current_project'], 
			'SN':part['SN']
		}

	qty = Parts.query.filter_by(**kwargs).count()
	part['qty'] = qty 

	form = Add_more(request.form)
	if request.method == 'POST' and form.validate():
		# retrieve qty and id values from form
		part_id = int(request.form.get('id'))
		quantity = int(request.form.get('qty'))
		
		if str(form.SN.data) != "" and quantity > 1:
			error = 'If S/N field is used, Qty must be 1'
		else:
			#	get all attributes of part
			Part = Parts.query.filter_by(id=part_id).first()
			#	get ids of rows that match these attributes
			kwargs = {'PR':Part.PR, 
					'PO':Part.PO, 
					'part':Part.part, 
					'project_name':Part.project_name, 
					'requestor':Part.requestor, 
					'supplier':Part.supplier, 
					'supplier_contact':Part.supplier_contact, 
					'item_description':Part.item_description, 
					'CPN':Part.CPN, 
					'PID':Part.PID, 
					'manufacturer_part_num':Part.manufacturer_part_num, 
					'submit_date':Part.submit_date, 
					'tracking':Part.tracking, 
					'status':Part.status, 
					'location':Part.location, 
					'checkout_date':Part.checkout_date, 
					'return_date':Part.return_date, 
					'times_used':Part.times_used, 
					'current_user':Part.current_user, 
					'current_project':Part.current_project, 
					'SN':Part.SN
				}
			ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 
			#	initial qty of these parts
			
			#	if input form input field is empty keep previous value for column
			form.PR.data = (Part.PR if not form.PR.data else form.PR.data)
			form.PO.data = (Part.PO if not form.PO.data else form.PO.data)
			form.requestor.data = (Part.requestor if not form.requestor.data else form.requestor.data)
			form.supplier.data = (Part.supplier if not form.supplier.data is None else form.supplier.data)
			form.supplier_contact.data = (Part.supplier_contact if not form.supplier_contact.data else form.supplier_contact.data)
			form.item_description.data = (Part.item_description if not form.item_description.data else form.item_description.data)
			form.CPN.data = (Part.CPN if not form.CPN.data else form.CPN.data)
			form.PID.data = (Part.PID if not form.PID.data else form.PID.data)
			form.manufacturer_part_num.data = (Part.manufacturer_part_num if not form.manufacturer_part_num.data else form.manufacturer_part_num.data)
			form.submit_date.data = (Part.submit_date if not form.submit_date.data else form.submit_date.raw_data[0])
			form.tracking.data = (Part.tracking if not form.tracking.data else form.tracking.data)
			form.project_name.data = (Part.project_name if not form.project_name.data else form.project_name.data)
			form.location.data = (Part.location if not form.location.data else form.location.data)
			form.SN.data = (Part.SN if not form.SN.data else form.SN.data)

			for i in range(0, quantity):
				part = Parts(
					PO = form.PO.data,
					PR = form.PR.data,
					part = request.form['part'],
					project_name = form.project_name.data,
					requestor = form.requestor.data,
					supplier = form.supplier.data,
					supplier_contact = form.supplier_contact.data,
					item_description = form.item_description.data,
					CPN = form.CPN.data,
					PID = form.PID.data,
					manufacturer_part_num = form.manufacturer_part_num.data,
					SN = form.SN.data,
					submit_date = form.submit_date.data,
					tracking = form.tracking.data,
					status = request.form['status'],
					location = form.location.data
					)
				db.session.add(part)
			db.session.commit()
			app.logger.info('| ACTION: add | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(request.form['part'], ids[0], quantity, current_user.name))

			flash("The Part was Added to the Database!")
			return redirect(url_for('home'))
	return render_template('add_more.html', part=part, id=part_id, form=form, POs=POs, PRs=PRs, project_names=project_names, part_default=part['part'].encode('utf-8'), 
		requestors=requestors, suppliers=suppliers, supplier_contacts=supplier_contacts, item_descriptions=item_descriptions, CPNs=CPNs, PIDs=PIDs,
		manufacturer_part_nums=manufacturer_part_nums, tracking=tracking, location=location, status_default=part['status'].encode('utf-8'), error=error)


@app.route('/delete_part', methods=['GET', 'POST'])
@login_required
@allowed_users('admin')
def delete_part():
	
	delete_parts = Parts.query.group_by(Parts.PR, 
										Parts.PO, 
										Parts.part, 
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description, 
										Parts.CPN, 
										Parts.PID, 
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
				).all()

	delete_parts = [dict(id=part.id, 
					PR=part.PR, 
					PO=part.PO, 
					part=part.part, 
					project_name=part.project_name,
					requestor=part.requestor, 
					supplier=part.supplier, 
					supplier_contact=part.supplier_contact, 
					item_description=part.item_description, 
					CPN=part.CPN, 
					PID=part.PID, 
					SN=part.SN,
					manufacturer_part_num=part.manufacturer_part_num, 
					submit_date=part.submit_date, 
					tracking=part.tracking, 
					status=part.status, 
					location=part.location,
					checkout_date=part.checkout_date,
					return_date=part.return_date,
					times_used=part.times_used,
					current_user=part.current_user,
					current_project=part.current_project
				) for part in delete_parts]

	#"""Add quantity variable to each delete_parts"""
	for i in delete_parts:
		kwargs = {'PR':i['PR'], 
				'PO':i['PO'], 
				'part':i['part'], 
				'project_name':i['project_name'], 
				'requestor':i['requestor'], 
				'supplier':i['supplier'], 
				'supplier_contact':i['supplier_contact'], 
				'item_description':i['item_description'], 
				'CPN':i['CPN'], 'PID':i['PID'], 
				'manufacturer_part_num':i['manufacturer_part_num'], 
				'submit_date':i['submit_date'], 
				'tracking':i['tracking'], 
				'status':i['status'], 
				'location':i['location'], 
				'checkout_date':i['checkout_date'], 
				'return_date':i['return_date'], 
				'times_used':i['times_used'],
				'current_user':i['current_user'], 
				'current_project':i['current_project'], 
				'SN':i['SN']
		}
		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	#post method
	if request.method == 'POST':
		delete_ids = request.form.getlist("do_delete")
		if delete_ids:
			return redirect(url_for('confirm_delete', delete_ids=delete_ids))
		else:
			flash('No Part was Selected!')
	return render_template('delete_part.html', parts=delete_parts)


@app.route('/delete_part/confirm', methods=['GET', 'POST'])
@login_required
@allowed_users('admin')
def confirm_delete():
	#"""Obtain ids from args"""
	delete_ids = sorted([i.encode('utf-8') for i in request.args.getlist('delete_ids')]) # same order as listed in delete_part page
	delete_parts = Parts.query.filter(Parts.id.in_(delete_ids)).all() # the ids now are retrieved in order
	delete_parts = [dict(id=part.id, 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						SN=part.SN,
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						location=part.location,
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) for part in delete_parts]

	#"""Add quantity variable to each delete_parts"""
	for i in delete_parts:
		kwargs = {'PR':i['PR'], 
				'PO':i['PO'], 
				'part':i['part'], 
				'project_name':i['project_name'], 
				'requestor':i['requestor'], 
				'supplier':i['supplier'], 
				'supplier_contact':i['supplier_contact'], 
				'item_description':i['item_description'], 
				'CPN':i['CPN'], 'PID':i['PID'], 
				'manufacturer_part_num':i['manufacturer_part_num'], 
				'submit_date':i['submit_date'], 
				'tracking':i['tracking'], 
				'status':i['status'], 
				'location':i['location'], 
				'checkout_date':i['checkout_date'], 
				'return_date':i['return_date'], 
				'times_used':i['times_used'],
				'current_user':i['current_user'], 
				'current_project':i['current_project'], 
				'SN':i['SN']
			}
		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	#"""Post Method"""#
	if request.method == 'POST':
		delete_ids = sorted([int(i) for i in request.form.getlist('delete_ids')])
		quantities = [int(i) for i in request.form.getlist('qty')]

		for i in range(len(delete_ids)):
			#	get all attributes of part
			Part = Parts.query.filter_by(id=delete_ids[i]).first()
			#	get ids of rows that match these attributes
			kwargs = {'PR':Part.PR, 
					'PO':Part.PO, 
					'part':Part.part, 
					'project_name':Part.project_name, 
					'requestor':Part.requestor, 
					'supplier':Part.supplier, 
					'supplier_contact':Part.supplier_contact, 
					'item_description':Part.item_description, 
					'CPN':Part.CPN, 'PID':Part.PID, 
					'manufacturer_part_num':Part.manufacturer_part_num, 
					'submit_date':Part.submit_date, 
					'tracking':Part.tracking, 
					'status':Part.status, 
					'location':Part.location, 
					'current_user':Part.current_user, 
					'current_project':Part.current_project, 
					'checkout_date':Part.checkout_date, 
					'return_date':Part.return_date, 
					'times_used':Part.times_used, 
					'SN':Part.SN
			}

			ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 

			#	iterate through these parts only for specified quantities starting from last in list
			iterator=len(ids)-quantities[i]
			while iterator < len(ids):
				Parts.query.filter(Parts.id == ids[iterator]).delete()	
				iterator += 1
			db.session.commit()
			app.logger.info('| ACTION: delete | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(Part.part, delete_ids[i], quantities[i], current_user.name))
		flash('The Parts were Deleted From Database')
		return redirect(url_for('delete_part'))
	return render_template('confirm_delete.html', delete_parts=delete_parts, delete_ids=delete_ids)


@app.route('/update', methods=['GET', 'POST'])
@login_required
def update_part():
	if request.method == 'POST':
		keyword = request.form['keyword']
		if keyword:
			return redirect(url_for('update_part_search', keyword=keyword))
		else:
			flash('Please Enter a Keyword!')	
	return render_template('update_part.html')


@app.route('/update_part_search/<keyword>', methods= ['GET', 'POST'])
@login_required
@allowed_users('admin')
def update_part_search(keyword):
	# if option is other, select all other type parts from db
	if keyword=='OTHER':
		parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
										).filter(~Parts.part.in_(['DIMM',
													'CPU',
													'PSU',
													'PROTOTYPE',
													'MEZZ-CARD',
													'HEATSINK',
													'HDD',
													'RAID-UNIT',
													'CHASSIS',
													'CABLES',
													'TPM',
													'GPU'])
											).group_by(Parts.PR, 
													Parts.PO, 
													Parts.part, 
													Parts.project_name, 
													Parts.requestor, 
													Parts.supplier, 
													Parts.supplier_contact,
													Parts.item_description, 
													Parts.CPN, 
													Parts.PID, 
													Parts.manufacturer_part_num, 
													Parts.SN, 
													Parts.submit_date, 
													Parts.tracking, 
													Parts.status,
													Parts.location, 
													Parts.checkout_date, 
													Parts.return_date, 
													Parts.times_used, 
													Parts.current_user, 
													Parts.current_project
											).all()

		parts = [dict(id=part[0], 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						SN=part.SN,
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						location=part.location,
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) for part in parts]

		#"""Add quantity variable to each delete_parts"""
		for i in parts:
			kwargs = {'PR':i['PR'], 
					'PO':i['PO'], 
					'part':i['part'], 
					'project_name':i['project_name'], 
					'requestor':i['requestor'], 
					'supplier':i['supplier'], 
					'supplier_contact':i['supplier_contact'], 
					'item_description':i['item_description'], 
					'CPN':i['CPN'], 
					'PID':i['PID'], 
					'manufacturer_part_num':i['manufacturer_part_num'], 
					'submit_date':i['submit_date'], 
					'tracking':i['tracking'], 
					'status':i['status'], 
					'location':i['location'], 
					'checkout_date':i['checkout_date'], 
					'return_date':i['return_date'], 
					'times_used':i['times_used'],
					'current_user':i['current_user'], 
					'current_project':i['current_project'], 
					'SN':i['SN']}

			qty = Parts.query.filter_by(**kwargs).count()
			i['qty'] = qty 
	else:	
		#retrieve parts where part=type and status=Available
		parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
						).filter(or_(Parts.PO.like('%'+keyword+'%'),
										Parts.PR.like('%'+keyword+'%'),
										Parts.part.like('%'+keyword+'%'),
										Parts.project_name.like('%'+keyword+'%'),
										Parts.requestor.like('%'+keyword+'%'),
										Parts.supplier.like('%'+keyword+'%'),
										Parts.supplier_contact.like('%'+keyword+'%'),	
										Parts.item_description.like('%'+keyword+'%'),
										Parts.CPN.like('%'+keyword+'%'),
										Parts.PID.like('%'+keyword+'%'),
										Parts.manufacturer_part_num.like('%'+keyword+'%'),
										Parts.submit_date.like('%'+keyword+'%'),
										Parts.tracking.like('%'+keyword+'%'),
										Parts.status.like('%'+keyword+'%'),
										Parts.location.like('%'+keyword+'%'),
										Parts.checkout_date.like('%'+keyword+'%'),	
										Parts.current_user.like('%'+keyword+'%'),
										Parts.current_project.like('%'+keyword+'%'),
										Parts.SN.like('%'+keyword+'%')
								)).group_by(Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
								).all()
		
		parts = [dict(id=part[0], 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						SN=part.SN,
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						location=part.location,
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) for part in parts]

		#"""Add quantity variable to each delete_parts"""
		for i in parts:
			kwargs = {'PR':i['PR'], 
					'PO':i['PO'], 
					'part':i['part'], 
					'project_name':i['project_name'], 
					'requestor':i['requestor'], 
					'supplier':i['supplier'], 
					'supplier_contact':i['supplier_contact'], 
					'item_description':i['item_description'], 
					'CPN':i['CPN'], 
					'PID':i['PID'], 
					'manufacturer_part_num':i['manufacturer_part_num'], 
					'submit_date':i['submit_date'], 
					'tracking':i['tracking'], 
					'status':i['status'], 
					'location':i['location'], 
					'checkout_date':i['checkout_date'], 
					'return_date':i['return_date'], 
					'times_used':i['times_used'],
					'current_user':i['current_user'], 
					'current_project':i['current_project'], 
					'SN':i['SN']}

			qty = Parts.query.filter_by(**kwargs).count()
			i['qty'] = qty 

	return render_template('update_part_search.html', keyword=keyword, parts=parts)


@app.route('/update_part/confirm/<part_id>', methods=['GET', 'POST'])
@login_required
@allowed_users('admin')
def confirm_update(part_id):
	# project names options for autocomplete field
	POs = ["%s" %i for i in db.session.query(Parts.PO).group_by(Parts.PO).all()]
	POs = [x.encode('utf-8') for x in POs]
	PRs = ["%s" %i for i in db.session.query(Parts.PR).group_by(Parts.PR).all()]
	PRs = [x.encode('utf-8') for x in PRs]
	parts = ["%s" %i for i in db.session.query(Parts.part).group_by(Parts.part).all()]
	parts = [x.encode('utf-8') for x in parts]
	project_names = ["%s" %i for i in db.session.query(Parts.project_name).group_by(Parts.project_name).all()]
	project_names = [x.encode('utf-8') for x in project_names]
	current_projects = ["%s" %i for i in db.session.query(Parts.current_project).group_by(Parts.current_project).all()]
	current_projects = [x.encode('utf-8') for x in current_projects]
	requestors = ["%s" %i for i in db.session.query(Parts.requestor).group_by(Parts.requestor).all()]
	requestors = [x.encode('utf-8') for x in requestors]
	suppliers = ["%s" %i for i in db.session.query(Parts.supplier).group_by(Parts.supplier).all()]
	suppliers = [x.encode('utf-8') for x in suppliers]
	supplier_contacts = ["%s" %i for i in db.session.query(Parts.supplier_contact).group_by(Parts.supplier_contact).all()]
	supplier_contacts = [x.encode('utf-8') for x in supplier_contacts]
	item_descriptions = ["%s" %i for i in db.session.query(Parts.item_description).group_by(Parts.item_description).all()]
	item_descriptions = [x.encode('utf-8') for x in item_descriptions]
	project_names = project_names + current_projects # merge these two lists
	CPNs = ["%s" %i for i in db.session.query(Parts.CPN).group_by(Parts.CPN).all()]
	CPNs = [x.encode('utf-8') for x in CPNs]
	PIDs = ["%s" %i for i in db.session.query(Parts.PID).group_by(Parts.PID).all()]
	PIDs = [x.encode('utf-8') for x in PIDs]
	manufacturer_part_nums = ["%s" %i for i in db.session.query(Parts.manufacturer_part_num).group_by(Parts.manufacturer_part_num).all()]
	manufacturer_part_nums = [x.encode('utf-8') for x in manufacturer_part_nums]
	tracking = ["%s" %i for i in db.session.query(Parts.tracking).group_by(Parts.tracking).all()]
	tracking = [x.encode('utf-8') for x in tracking]
	location = ["%s" %i for i in db.session.query(Parts.location).group_by(Parts.location).all()]
	location = [x.encode('utf-8') for x in location]

	#   obtain ids from arg list
	update_part = Parts.query.get(part_id)
	update_part = dict(id=update_part.id, 
						PR=update_part.PR, 
						PO=update_part.PO, 
						part=update_part.part, 
						project_name=update_part.project_name,
						requestor=update_part.requestor, 
						supplier=update_part.supplier, 
						supplier_contact=update_part.supplier_contact, 
						item_description=update_part.item_description, 
						CPN=update_part.CPN, 
						PID=update_part.PID, 
						manufacturer_part_num=update_part.manufacturer_part_num,
						SN =update_part.SN, 
						submit_date=update_part.submit_date, 
						tracking=update_part.tracking, 
						status=update_part.status,
						location=update_part.location, 
						checkout_date=update_part.checkout_date,
						return_date=update_part.return_date,
						times_used=update_part.times_used,
						current_user=update_part.current_user,
						current_project=update_part.current_project
					) 
	#   add quantity variable to each update_part
	kwargs = {'PR':update_part['PR'], 
			'PO':update_part['PO'], 
			'part':update_part['part'], 
			'project_name':update_part['project_name'], 
			'requestor':update_part['requestor'],
			'supplier':update_part['supplier'], 
			'supplier_contact':update_part['supplier_contact'], 
			'item_description':update_part['item_description'], 
			'CPN':update_part['CPN'], 
			'PID':update_part['PID'], 
			'manufacturer_part_num':update_part['manufacturer_part_num'], 
			'submit_date':update_part['submit_date'], 
			'tracking':update_part['tracking'], 
			'status':update_part['status'], 
			'location':update_part['location'], 
			'checkout_date':update_part['checkout_date'], 
			'return_date':update_part['return_date'], 
			'times_used':update_part['times_used'], 
			'current_user':update_part['current_user'], 
			'current_project':update_part['current_project'], 
			'SN':update_part['SN']
		}

	qty = Parts.query.filter_by(**kwargs).count()
	update_part['qty'] = qty 

	#setup form class UpdatePart
	form = UpdatePart(request.form)

	if request.method == 'POST' and form.validate():
		update_id = int(request.form.get('update_id'))
		quantity = int(request.form.get('update_qty'))

		#	get all attributes of part
		Part = Parts.query.filter_by(id=update_id).first()
		#	get ids of rows that match these attributes
		kwargs = {'PR':Part.PR, 
				'PO':Part.PO, 
				'part':Part.part, 
				'project_name':Part.project_name, 
				'requestor':Part.requestor, 
				'supplier':Part.supplier, 
				'supplier_contact':Part.supplier_contact, 
				'item_description':Part.item_description, 
				'CPN':Part.CPN, 
				'PID':Part.PID, 
				'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 
				'tracking':Part.tracking, 
				'status':Part.status, 
				'location':Part.location, 
				'checkout_date':Part.checkout_date, 
				'return_date':Part.return_date, 
				'times_used':Part.times_used, 
				'current_user':Part.current_user, 
				'current_project':Part.current_project, 
				'SN':Part.SN
			}
		ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 
		#	initial qty of these parts
		prev_quantity = len(ids)
		
		#	if input form input field is empty keep previous value for column
		form.PR.data = (Part.PR if not form.PR.data else form.PR.data)
		form.PO.data = (Part.PO if not form.PO.data else form.PO.data)
		form.requestor.data = (Part.requestor if not form.requestor.data else form.requestor.data)
		form.supplier.data = (Part.supplier if not form.supplier.data is None else form.supplier.data)
		form.supplier_contact.data = (Part.supplier_contact if not form.supplier_contact.data else form.supplier_contact.data)
		form.item_description.data = (Part.item_description if not form.item_description.data else form.item_description.data)
		form.CPN.data = (Part.CPN if not form.CPN.data else form.CPN.data)
		form.PID.data = (Part.PID if not form.PID.data else form.PID.data)
		form.manufacturer_part_num.data = (Part.manufacturer_part_num if not form.manufacturer_part_num.data else form.manufacturer_part_num.data)
		form.submit_date.data = (Part.submit_date if not form.submit_date.data else form.submit_date.raw_data[0])
		form.tracking.data = (Part.tracking if not form.tracking.data else form.tracking.data)
		form.project_name.data = (Part.project_name if not form.project_name.data else form.project_name.data)
		form.location.data = (Part.location if not form.location.data else form.location.data)
		form.SN.data = (Part.SN if not form.SN.data else form.SN.data)

		# if adding new parts
		if (quantity >= prev_quantity):

			# add new parts
			add_qty = quantity - prev_quantity

			if (add_qty>0):
				for i in range(0, add_qty):
					part = Parts(
						PO = form.PO.data,
						PR = form.PR.data,
						part = request.form['part'],
						project_name = form.project_name.data,
						requestor = form.requestor.data,
						supplier = form.supplier.data,
						supplier_contact = form.supplier_contact.data,
						item_description = form.item_description.data,
						CPN = form.CPN.data,
						PID = form.PID.data,
						manufacturer_part_num = form.manufacturer_part_num.data,
						SN = form.SN.data,
						submit_date = form.submit_date.data,
						tracking = form.tracking.data,
						status = request.form['status'],
						location = form.location.data
						)
					db.session.add(part)
				db.session.commit()
				app.logger.info('| ACTION: add | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(request.form['part'], part.id-(add_qty-1), add_qty, current_user.name))
				
			# modify existing parts
			iterator=1
			while iterator<=prev_quantity:
				db.engine.execute('UPDATE parts SET PR=:a, PO=:b, part=:c, requestor=:d, supplier=:e, supplier_contact=:f, item_description=:g,\
							CPN=:h, PID=:i, manufacturer_part_num=:j, submit_date=:k, tracking=:l, status = :m, project_name=:n, location=:o, SN=:p WHERE id=:q',
							a=form.PR.data, b=form.PO.data, c=request.form['part'], d=form.requestor.data, e=form.supplier.data, f=form.supplier_contact.data,
							g=form.item_description.data, h=form.CPN.data, i=form.PID.data, j=form.manufacturer_part_num.data, k=form.submit_date.data,
							l=form.tracking.data, m=request.form['status'], n=form.project_name.data, o=form.location.data, p=form.SN.data, q=ids[iterator-1])
				iterator += 1


			db.session.commit()
			app.logger.info('| ACTION: update | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(request.form['part'], update_id, prev_quantity, current_user.name))
			
			flash('The part has been updated!')		

		else:
			# delete parts
			delete_qty = prev_quantity - quantity

			iterator=len(ids)-delete_qty
			while iterator < len(ids):
				Parts.query.filter(Parts.id == ids[iterator]).delete()	
				iterator += 1
			db.session.commit()
			app.logger.info('| ACTION: delete | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(Part.part, ids[delete_qty-1], delete_qty, current_user.name))
			
			# modify existing parts
			iterator=1
			while iterator<=quantity:
				db.engine.execute('UPDATE parts SET PR=:a, PO=:b, part=:c, requestor=:d, supplier=:e, supplier_contact=:f, item_description=:g,\
							CPN=:h, PID=:i, manufacturer_part_num=:j, submit_date=:k, tracking=:l, status = :m, project_name=:n, location=:o, SN=:p WHERE id=:q',
							a=form.PR.data, b=form.PO.data, c=request.form['part'], d=form.requestor.data, e=form.supplier.data, f=form.supplier_contact.data,
							g=form.item_description.data, h=form.CPN.data, i=form.PID.data, j=form.manufacturer_part_num.data, k=form.submit_date.data,
							l=form.tracking.data, m=request.form['status'], n=form.project_name.data, o=form.location.data, p=form.SN.data, q=ids[iterator-1])
				iterator += 1

			db.session.commit()
			app.logger.info('| ACTION: update | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(request.form['part'], update_id, quantity, current_user.name))
			
			flash('The part has been updated!')		

		return redirect(url_for('update_part_search', keyword=request.form['part']))
	return render_template('confirm_update.html', part=update_part, update_id=part_id, form=form, POs=POs, PRs=PRs, project_names=project_names, part_default=update_part['part'].encode('utf-8'), 
		requestors=requestors, suppliers=suppliers, supplier_contacts=supplier_contacts, item_descriptions=item_descriptions, CPNs=CPNs, PIDs=PIDs,
		manufacturer_part_nums=manufacturer_part_nums, tracking=tracking, location=location, status_default=update_part['status'].encode('utf-8'))


@app.route('/return_part', methods=['GET', 'POST'])
@login_required
def return_part():
	#	retrieve data where current_user=currentuser and status=unavailable
	parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project).filter(Parts.current_user==current_user.name, Parts.status=='Unavailable'
							).group_by(Parts.PR, 
									Parts.PO,
									Parts.part,
									Parts.project_name, 
									Parts.requestor, 
									Parts.supplier, 
									Parts.supplier_contact,
									Parts.item_description,
									Parts.CPN, 
									Parts.PID,
									Parts.manufacturer_part_num, 
									Parts.SN, 
									Parts.submit_date, 
									Parts.tracking, 
									Parts.status,
									Parts.location, 
									Parts.checkout_date, 
									Parts.return_date, 
									Parts.times_used, 
									Parts.current_user, 
									Parts.current_project
							).all()
	
	parts = [dict(id=part[0], 
					PR=part.PR, 
					PO=part.PO, 
					part=part.part, 
					project_name=part.project_name,
					requestor=part.requestor, 
					supplier=part.supplier, 
					supplier_contact=part.supplier_contact, 
					item_description=part.item_description, 
					CPN=part.CPN, 
					PID=part.PID, 
					SN=part.SN,
					manufacturer_part_num=part.manufacturer_part_num, 
					submit_date=part.submit_date, 
					tracking=part.tracking, 
					status=part.status, 
					location=part.location,
					checkout_date=part.checkout_date,
					return_date=part.return_date,
					times_used=part.times_used,
					current_user=part.current_user,
					current_project=part.current_project
				) for part in parts]

	#"""Add quantity variable to each delete_parts"""
	for i in parts:
		kwargs = {'PR':i['PR'], 
				'PO':i['PO'], 
				'part':i['part'], 
				'project_name':i['project_name'], 
				'requestor':i['requestor'], 
				'supplier':i['supplier'], 
				'supplier_contact':i['supplier_contact'], 
				'item_description':i['item_description'], 
				'CPN':i['CPN'], 
				'PID':i['PID'], 
				'manufacturer_part_num':i['manufacturer_part_num'], 
				'submit_date':i['submit_date'], 
				'tracking':i['tracking'], 
				'status':i['status'], 
				'location':i['location'], 
				'checkout_date':i['checkout_date'], 
				'return_date':i['return_date'], 
				'times_used':i['times_used'],
				'current_user':i['current_user'], 
				'current_project':i['current_project'], 
				'SN':i['SN']}

		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	return render_template('return_part.html', parts=parts)


@app.route('/return_part/confirm/<part_id>', methods=['GET', 'POST'])
@login_required
def confirm_return(part_id):
	return_part = Parts.query.get(part_id)
	return_part = dict(id=return_part.id, 
				PR=return_part.PR, 
				PO=return_part.PO, 
				part=return_part.part, 
				project_name=return_part.project_name,
				requestor=return_part.requestor, 
				supplier=return_part.supplier, 
				supplier_contact=return_part.supplier_contact, 
				item_description=return_part.item_description, 
				CPN=return_part.CPN, 
				PID=return_part.PID, 
				manufacturer_part_num=return_part.manufacturer_part_num, 
				SN=return_part.SN,
				submit_date=return_part.submit_date, 
				tracking=return_part.tracking, 
				status=return_part.status, 
				location=return_part.location,
				checkout_date=return_part.checkout_date,
				return_date=return_part.return_date,
				times_used=return_part.times_used,
				current_user=return_part.current_user,
				current_project=return_part.current_project
				) 
	#   add quantity variable to each checkout_parts
	kwargs = {'PR':return_part['PR'], 
			'PO':return_part['PO'], 
			'part':return_part['part'], 
			'project_name':return_part['project_name'], 
			'requestor':return_part['requestor'], 
			'supplier':return_part['supplier'], 
			'supplier_contact':return_part['supplier_contact'], 
			'item_description':return_part['item_description'], 
			'CPN':return_part['CPN'], 'PID':return_part['PID'], 
			'manufacturer_part_num':return_part['manufacturer_part_num'], 
			'submit_date':return_part['submit_date'], 
			'tracking':return_part['tracking'], 
			'status':return_part['status'], 
			'location':return_part['location'], 
			'checkout_date':return_part['checkout_date'], 
			'return_date':return_part['return_date'], 
			'times_used':return_part['times_used'],
			'current_user':return_part['current_user'], 
			'current_project':return_part['current_project'], 
			'SN':return_part['SN']
		}
	qty = Parts.query.filter_by(**kwargs).count()
	return_part['qty'] = qty 

	if request.method == 'POST':
		date = time.strftime("%m/%d/%Y")
		# get ids and quentities from form
		return_id = int(request.form.get('return_id'))
		quantity = int(request.form.get('qty'))

		# get all attributes of part
		Part = Parts.query.filter_by(id=return_id).first()
		# get ids of rows that match these attributes
		kwargs = {'PR':Part.PR, 
				'PO':Part.PO, 
				'part':Part.part, 
				'project_name':Part.project_name, 
				'requestor':Part.requestor, 
				'supplier':Part.supplier, 
				'supplier_contact':Part.supplier_contact, 
				'item_description':Part.item_description, 
				'CPN':Part.CPN, 
				'PID':Part.PID, 
				'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 
				'tracking':Part.tracking, 
				'status':Part.status, 
				'location':Part.location, 
				'current_user':Part.current_user, 
				'current_project':Part.current_project, 
				'checkout_date':Part.checkout_date, 
				'return_date':Part.return_date, 
				'times_used':Part.times_used, 
				'SN':Part.SN
			}
		ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 
			
		#	iterate through these parts only for specified quantities
		iterator=1
		while iterator<=quantity:
			db.engine.execute('update parts set status = :s, return_date = :r, current_user=:u, current_project=:p, location=:l, requestor=:q where id=:i',
								s='Available', r=date, u=None, p=None, l=None, q="None", i=ids[iterator-1])	
			iterator += 1
		db.session.commit()
		app.logger.info('| ACTION: return | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(Part.part, return_id, quantity, current_user.name))
		flash('The parts were returned!')
		return redirect(url_for('return_part'))
	return render_template('confirm_return.html', return_part=return_part)


@app.route('/checkout_part', methods=['GET', 'POST'])
@login_required
def checkout_part():
	if request.method == 'POST':
		keyword = request.form['keyword']
		if keyword:
			return redirect(url_for('part_search', keyword=keyword))
		else:
			flash('Please enter a keyword!')	
	return render_template('checkout_part.html')


@app.route('/search/<keyword>', methods= ['GET', 'POST'])
@login_required
def part_search(keyword):
	#retrieve parts where part=type and status=Available
	if keyword=='OTHER':
		available_parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
								).filter(~Parts.part.in_(['DIMM',
													'CPU',
													'PSU',
													'PROTOTYPE',
													'MEZZ-CARD',
													'HEATSINK',
													'HDD',
													'RAID-UNIT',
													'CHASSIS',
													'CABLES',
													'TPM',
													'GPU']),
									Parts.status=='Available'
										).group_by(Parts.PR, 
													Parts.PO, 
													Parts.part, 
													Parts.project_name, 
													Parts.requestor, 
													Parts.supplier, 
													Parts.supplier_contact,
													Parts.item_description, 
													Parts.CPN, 
													Parts.PID, 
													Parts.manufacturer_part_num, 
													Parts.SN, 
													Parts.submit_date, 
													Parts.tracking, 
													Parts.status,
													Parts.location, 
													Parts.checkout_date, 
													Parts.return_date, 
													Parts.times_used, 
													Parts.current_user, 
													Parts.current_project
											).all()

		available_parts = [dict(id=part[0], 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						SN=part.SN,
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						location=part.location,
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) for part in available_parts]

		#"""Add quantity variable to each delete_parts"""
		for i in available_parts:
			kwargs = {'PR':i['PR'], 
					'PO':i['PO'], 
					'part':i['part'], 
					'project_name':i['project_name'], 
					'requestor':i['requestor'], 
					'supplier':i['supplier'], 
					'supplier_contact':i['supplier_contact'], 
					'item_description':i['item_description'], 
					'CPN':i['CPN'], 
					'PID':i['PID'], 
					'manufacturer_part_num':i['manufacturer_part_num'], 
					'submit_date':i['submit_date'], 
					'tracking':i['tracking'], 
					'status':i['status'], 
					'location':i['location'], 
					'checkout_date':i['checkout_date'], 
					'return_date':i['return_date'], 
					'times_used':i['times_used'],
					'current_user':i['current_user'], 
					'current_project':i['current_project'], 
					'SN':i['SN']}

			qty = Parts.query.filter_by(**kwargs).count()
			i['qty'] = qty 

		unavailable_parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
							).filter(~Parts.part.in_(['DIMM',
													'CPU',
													'PSU',
													'PROTOTYPE',
													'MEZZ-CARD',
													'HEATSINK',
													'HDD',
													'RAID-UNIT',
													'CHASSIS',
													'CABLES',
													'TPM',
													'GPU']),
									Parts.status=='Unvailable'
										).group_by(Parts.PR, 
													Parts.PO, 
													Parts.part, 
													Parts.project_name, 
													Parts.requestor, 
													Parts.supplier, 
													Parts.supplier_contact,
													Parts.item_description, 
													Parts.CPN, 
													Parts.PID, 
													Parts.manufacturer_part_num, 
													Parts.SN, 
													Parts.submit_date, 
													Parts.tracking, 
													Parts.status,
													Parts.location, 
													Parts.checkout_date, 
													Parts.return_date, 
													Parts.times_used, 
													Parts.current_user, 
													Parts.current_project
											).all()

		unavailable_parts = [dict(id=part[0], 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						SN=part.SN,
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						location=part.location,
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) for part in unavailable_parts]

		#"""Add quantity variable to each delete_parts"""
		for i in unavailable_parts:
			kwargs = {'PR':i['PR'], 
					'PO':i['PO'], 
					'part':i['part'], 
					'project_name':i['project_name'], 
					'requestor':i['requestor'], 
					'supplier':i['supplier'], 
					'supplier_contact':i['supplier_contact'], 
					'item_description':i['item_description'], 
					'CPN':i['CPN'], 
					'PID':i['PID'], 
					'manufacturer_part_num':i['manufacturer_part_num'], 
					'submit_date':i['submit_date'], 
					'tracking':i['tracking'], 
					'status':i['status'], 
					'location':i['location'], 
					'checkout_date':i['checkout_date'], 
					'return_date':i['return_date'], 
					'times_used':i['times_used'],
					'current_user':i['current_user'], 
					'current_project':i['current_project'], 
					'SN':i['SN']}

			qty = Parts.query.filter_by(**kwargs).count()
			i['qty'] = qty 
	else:	
		#retrieve parts where part=type and status=Available
		available_parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
							).filter(or_(Parts.PO.like('%'+keyword+'%'),
										Parts.PR.like('%'+keyword+'%'),
										Parts.part.like('%'+keyword+'%'),
										Parts.project_name.like('%'+keyword+'%'),
										Parts.requestor.like('%'+keyword+'%'),
										Parts.supplier.like('%'+keyword+'%'),
										Parts.supplier_contact.like('%'+keyword+'%'),	
										Parts.item_description.like('%'+keyword+'%'),
										Parts.CPN.like('%'+keyword+'%'),
										Parts.PID.like('%'+keyword+'%'),
										Parts.manufacturer_part_num.like('%'+keyword+'%'),
										Parts.submit_date.like('%'+keyword+'%'),
										Parts.tracking.like('%'+keyword+'%'),
										Parts.status.like('%'+keyword+'%'),
										Parts.location.like('%'+keyword+'%'),
										Parts.checkout_date.like('%'+keyword+'%'),	
										Parts.current_user.like('%'+keyword+'%'),
										Parts.current_project.like('%'+keyword+'%'),
										Parts.SN.like('%'+keyword+'%'))
										,Parts.status=="Available").group_by(
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
								).all()
		
		available_parts = [dict(id=part[0], 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						SN=part.SN,
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						location=part.location,
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) for part in available_parts]

		#"""Add quantity variable to each delete_parts"""
		for i in available_parts:
			kwargs = {'PR':i['PR'], 
					'PO':i['PO'], 
					'part':i['part'], 
					'project_name':i['project_name'], 
					'requestor':i['requestor'], 
					'supplier':i['supplier'], 
					'supplier_contact':i['supplier_contact'], 
					'item_description':i['item_description'], 
					'CPN':i['CPN'], 
					'PID':i['PID'], 
					'manufacturer_part_num':i['manufacturer_part_num'], 
					'submit_date':i['submit_date'], 
					'tracking':i['tracking'], 
					'status':i['status'], 
					'location':i['location'], 
					'checkout_date':i['checkout_date'], 
					'return_date':i['return_date'], 
					'times_used':i['times_used'],
					'current_user':i['current_user'], 
					'current_project':i['current_project'], 
					'SN':i['SN']}

			qty = Parts.query.filter_by(**kwargs).count()
			i['qty'] = qty 

				#retrieve parts where part=type and status=Available
		unavailable_parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
							).filter(or_(Parts.PO.like('%'+keyword+'%'),
										Parts.PR.like('%'+keyword+'%'),
										Parts.part.like('%'+keyword+'%'),
										Parts.project_name.like('%'+keyword+'%'),
										Parts.requestor.like('%'+keyword+'%'),
										Parts.supplier.like('%'+keyword+'%'),
										Parts.supplier_contact.like('%'+keyword+'%'),	
										Parts.item_description.like('%'+keyword+'%'),
										Parts.CPN.like('%'+keyword+'%'),
										Parts.PID.like('%'+keyword+'%'),
										Parts.manufacturer_part_num.like('%'+keyword+'%'),
										Parts.submit_date.like('%'+keyword+'%'),
										Parts.tracking.like('%'+keyword+'%'),
										Parts.status.like('%'+keyword+'%'),
										Parts.location.like('%'+keyword+'%'),
										Parts.checkout_date.like('%'+keyword+'%'),	
										Parts.current_user.like('%'+keyword+'%'),
										Parts.current_project.like('%'+keyword+'%'),
										Parts.SN.like('%'+keyword+'%'))
								,Parts.status=="Unavailable").group_by(Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
								).all()
		
		unavailable_parts = [dict(id=part[0], 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						project_name=part.project_name,
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						SN=part.SN,
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						location=part.location,
						checkout_date=part.checkout_date,
						return_date=part.return_date,
						times_used=part.times_used,
						current_user=part.current_user,
						current_project=part.current_project
					) for part in unavailable_parts]

		#"""Add quantity variable to each delete_parts"""
		for i in unavailable_parts:
			kwargs = {'PR':i['PR'], 
					'PO':i['PO'], 
					'part':i['part'], 
					'project_name':i['project_name'], 
					'requestor':i['requestor'], 
					'supplier':i['supplier'], 
					'supplier_contact':i['supplier_contact'], 
					'item_description':i['item_description'], 
					'CPN':i['CPN'], 
					'PID':i['PID'], 
					'manufacturer_part_num':i['manufacturer_part_num'], 
					'submit_date':i['submit_date'], 
					'tracking':i['tracking'], 
					'status':i['status'], 
					'location':i['location'], 
					'checkout_date':i['checkout_date'], 
					'return_date':i['return_date'], 
					'times_used':i['times_used'],
					'current_user':i['current_user'], 
					'current_project':i['current_project'], 
					'SN':i['SN']}

			qty = Parts.query.filter_by(**kwargs).count()
			i['qty'] = qty 
	
	return render_template('part_search.html', keyword=keyword, part_available=available_parts, part_unavailable=unavailable_parts)


@app.route('/checkout_part/confirm/<part_id>', methods=['GET', 'POST'])
@login_required
def send_request(part_id):
	# project names options for autocomplete field
	project_names = ["%s" %i for i in db.session.query(Parts.project_name).group_by(Parts.project_name).all()]
	project_names = [x.encode('utf-8') for x in project_names]
	location = ["%s" %i for i in db.session.query(Parts.location).group_by(Parts.location).all()]
	location = [x.encode('utf-8') for x in location]
	# get part by id
	part = Parts.query.get(part_id)
	part = dict(id=part.id, 
				PR=part.PR, 
				PO=part.PO, 
				part=part.part, 
				project_name=part.project_name,
				requestor=part.requestor, 
				supplier=part.supplier, 
				supplier_contact=part.supplier_contact, 
				item_description=part.item_description, 
				CPN=part.CPN, 
				PID=part.PID, 
				manufacturer_part_num=part.manufacturer_part_num,
				SN=part.SN, 
				submit_date=part.submit_date, 
				tracking=part.tracking, 
				status=part.status,
				location=part.location, 
				checkout_date=part.checkout_date,
				return_date=part.return_date,
				times_used=part.times_used,
				current_user=part.current_user,
				current_project=part.current_project
			) 
	#   add quantity variable to each update_part
	kwargs = {'PR':part['PR'], 
			'PO':part['PO'], 
			'part':part['part'], 
			'project_name':part['project_name'], 
			'requestor':part['requestor'],
			'supplier':part['supplier'], 
			'supplier_contact':part['supplier_contact'], 
			'item_description':part['item_description'], 
			'CPN':part['CPN'], 
			'PID':part['PID'], 
			'manufacturer_part_num':part['manufacturer_part_num'], 
			'submit_date':part['submit_date'], 
			'tracking':part['tracking'], 
			'status':part['status'], 
			'location':part['location'], 
			'checkout_date':part['checkout_date'], 
			'return_date':part['return_date'], 
			'times_used':part['times_used'], 
			'current_user':part['current_user'], 
			'current_project':part['current_project'], 
			'SN':part['SN']
		}
	qty = Parts.query.filter_by(**kwargs).count()
	part['qty'] = qty 

	# create part	
	form = CheckoutPart(request.form)
	if request.method == 'POST' and form.validate():
		date = time.strftime("%m/%d/%Y")
		checkout_id = [int(request.form.get('checkout_id'))]
		quantity = [int(i) for i in request.form.getlist('qty')]

		Part = Parts.query.get(checkout_id[0])

		#changing part status to pending
		#get ids of rows that match these attributes
		kwargs = {'PR':Part.PR, 
				'PO':Part.PO, 
				'part':Part.part, 
				'project_name':Part.project_name, 
				'requestor':Part.requestor, 
				'supplier':Part.supplier, 
				'supplier_contact':Part.supplier_contact, 
				'item_description':Part.item_description, 
				'CPN':Part.CPN, 'PID':Part.PID, 
				'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 
				'tracking':Part.tracking, 
				'status':Part.status, 
				'location':Part.location, 
				'current_user':Part.current_user, 
				'current_project':Part.current_project, 
				'checkout_date':Part.checkout_date, 
				'return_date':Part.return_date, 
				'times_used':Part.times_used, 
				'SN':Part.SN
			}
		
		ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 

		#   Update part info
		iterator=len(ids)-quantity[0]
		while iterator<len(ids):
			db.engine.execute('update parts set status = :s, checkout_date =:d, return_date =:r\
							 where id=:i', s='Pending', d=time.strftime("%m/%d/%Y"), r=form.return_date.raw_data[0], i=ids[iterator])	
			iterator += 1
		db.session.commit()

		#creating request
		Request = Requests(
			    part_id = ids[len(ids)-quantity[0]],
			    part = Part.part,
			    qty = quantity[0],
				current_user=('admin' if not Part.current_user else Part.current_user),
				requestor=current_user.name,
				request_date=date,
				return_date=form.return_date.raw_data[0],
				project_name=form.project.data,
				location=form.location.data,
				use_detail=form.details.data
				)
		db.session.add(Request)
		db.session.commit()

		# add prev history
		# retrive history data from first id
		prev_history = History.query.filter_by(Part_SN=ids[0]).all()
		for row in prev_history:	
			history = History(
			serial= ids[len(ids)-quantity[0]],
			project= row.project,
			user=row.user,
			checkout_date=row.checkout_date,
			return_date= row.return_date,
			detail= row.detail
			)
			db.session.add(history)
		db.session.commit()

		flash('The request was sent to %s!'%Request.current_user)
		return redirect(url_for('checkout_part'))
	return render_template('confirm_checkout.html', part=part, part_id=part_id, form=form, project_names=project_names, location=location,
							current_user=part['current_user'])


@app.route('/requests/')
@app.route('/requests/<part_id>',methods=['GET','POST'])
@login_required
def show_requests(part_id=None):
	if part_id:
		#delete request
		Requests.query.filter_by(part_id=part_id).delete()
		db.session.commit()
		
		#update part
		Part = Parts.query.get(part_id)
		#get ids of rows that match these attributes
		kwargs = {'PR':Part.PR, 
				'PO':Part.PO, 
				'part':Part.part, 
				'project_name':Part.project_name, 
				'requestor':Part.requestor, 
				'supplier':Part.supplier, 
				'supplier_contact':Part.supplier_contact, 
				'item_description':Part.item_description, 
				'CPN':Part.CPN, 'PID':Part.PID, 
				'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 
				'tracking':Part.tracking, 
				'status':Part.status, 
				'location':Part.location, 
				'current_user':Part.current_user, 
				'current_project':Part.current_project, 
				'checkout_date':Part.checkout_date, 
				'return_date':Part.return_date, 
				'times_used':Part.times_used, 
				'SN':Part.SN
			}
		
		ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 

		#   Update part info
		iterator=0
		while iterator<len(ids):
			db.engine.execute('update parts set status = :s, checkout_date =:d, return_date =:r where id=:i', s='Available', d=None, r=None, i=ids[iterator])	
			iterator += 1
		db.session.commit()

		#remove prev history
		prev_history = History.query.filter_by(Part_SN=part_id).all()
		for row in prev_history:
			db.session.delete(row)
		db.session.commit()

		flash('The request has been canceled')
		redirect(url_for('return_part'))

	requests = Requests.query.filter_by(current_user=current_user.name)
	requests = [dict(
				id=request.id,
				part_id = request.part_id,
				part = request.part,
				qty = request.qty,	
				current_user = request.current_user,
				requestor = request.requestor,
				request_date = request.request_date,
				return_date = request.return_date,
				project_name = request.project_name,
				location = request.location,
				use_detail = request.use_detail
			) for request in requests]

	#retrieve any parts requested by user
	requested_parts = Requests.query.filter(Requests.requestor==current_user.name)
	return render_template('requests.html', requests=requests, user=current_user.name, requested_parts=requested_parts)


@app.route('/confirm_request/<request_id>', methods=['GET', 'POST'])
@login_required
def confirm_request(request_id):
	#Retrieve request
	Request = Requests.query.filter_by(id=request_id).first()
	requestor = Request.requestor
	#Retrieve Part
	Part = Parts.query.filter_by(id=Request.part_id).first()

	#	get ids of rows that match these attributes
	kwargs = {'PR':Part.PR, 
			'PO':Part.PO, 
			'part':Part.part, 
			'project_name':Part.project_name, 
			'requestor':Part.requestor, 
			'supplier':Part.supplier, 
			'supplier_contact':Part.supplier_contact, 
			'item_description':Part.item_description, 
			'CPN':Part.CPN, 'PID':Part.PID, 
			'manufacturer_part_num':Part.manufacturer_part_num, 
			'submit_date':Part.submit_date, 
			'tracking':Part.tracking, 
			'status':Part.status, 
			'location':Part.location, 
			'current_user':Part.current_user, 
			'current_project':Part.current_project, 
			'checkout_date':Part.checkout_date, 
			'return_date':Part.return_date, 
			'times_used':Part.times_used, 
			'SN':Part.SN
		}
	
	ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 

	date = time.strftime("%m/%d/%Y")
	# create History
	if Request.qty!=len(ids): 

		# retrive history data from first id
		prev_history = History.query.filter_by(Part_SN=ids[0]).all()
		
		# store prev_history with new id
		new_id = len(ids)-Request.qty

		for row in prev_history:	
			history = History(
			serial= ids[new_id],
			project= row.project,
			user=row.user,
			checkout_date=row.checkout_date,
			return_date= row.return_date,
			detail= row.detail
			)
			db.session.add(history)
		# Record new history with new id
		history = History(
			serial= ids[new_id],
			project= Request.project_name,
			user=Request.requestor,
			checkout_date=date,
			return_date= Request.return_date,
			detail= Request.use_detail
		)
		db.session.add(history)
		db.session.commit()
	else:			
		#	Record history of part
		history = History(
			serial= (Part.SN if (Part.SN and Request.qty==1) else ids[0]),
			project= Request.project_name,
			user=Request.requestor,
			checkout_date=date,
			return_date= Request.return_date,
			detail= Request.use_detail
		)
		db.session.add(history)
		db.session.commit()

		#   Update part info
	iterator=len(ids)-Request.qty
	while iterator<len(ids):
		db.engine.execute('update parts set status = :s, location =:l, checkout_date =:d, return_date =:r, times_used=times_used+1, \
					current_user=:u, current_project=:p where id=:i', s='Unavailable', d=date, r=Request.return_date,
					u=Request.requestor, p=Request.project_name, l=Request.location, i=ids[iterator])	
		iterator += 1
	db.session.commit()
	app.logger.info('| ACTION: checkout | PART: %s | ID:%s | QUANTITY: %s | BY USER: %s'%(Part.part, ids[len(ids)-Request.qty], Request.qty, Request.requestor))

	#clear request
	Request.query.filter_by(id=request_id).delete()
	db.session.commit()
	requests = Requests.query.filter_by(current_user=current_user.name)
	flash('The request of %s has been confirmed'%requestor)
	return render_template('requests.html', requests=requests, user=current_user.name)


@app.route('/list_checkedout_parts/')
@login_required
@allowed_users('admin')
def list_checkedout_parts():
	#retrieve data where current_user=currentuser and status=unavailable
	checkedout_parts = db.session.query(func.min(Parts.id),
										Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project).filter(or_(Parts.current_user!=current_user.name, Parts.current_user!=None)
							).group_by(Parts.PR, 
										Parts.PO,
										Parts.part,
										Parts.project_name, 
										Parts.requestor, 
										Parts.supplier, 
										Parts.supplier_contact,
										Parts.item_description,
										Parts.CPN, 
										Parts.PID,
										Parts.manufacturer_part_num, 
										Parts.SN, 
										Parts.submit_date, 
										Parts.tracking, 
										Parts.status,
										Parts.location, 
										Parts.checkout_date, 
										Parts.return_date, 
										Parts.times_used, 
										Parts.current_user, 
										Parts.current_project
								).all()

	for i in checkedout_parts:
		print i



	checkedout_parts = [dict(id=part[0], 
					PR=part.PR, 
					PO=part.PO, 
					part=part.part, 
					project_name=part.project_name,
					requestor=part.requestor, 
					supplier=part.supplier, 
					supplier_contact=part.supplier_contact, 
					item_description=part.item_description, 
					CPN=part.CPN, 
					PID=part.PID, 
					SN=part.SN,
					manufacturer_part_num=part.manufacturer_part_num, 
					submit_date=part.submit_date, 
					tracking=part.tracking, 
					status=part.status, 
					location=part.location,
					checkout_date=part.checkout_date,
					return_date=part.return_date,
					times_used=part.times_used,
					current_user=part.current_user,
					current_project=part.current_project
				) for part in checkedout_parts]

	#"""Add quantity variable to each delete_parts"""
	for i in checkedout_parts:
		kwargs = {'PR':i['PR'], 
				'PO':i['PO'], 
				'part':i['part'], 
				'project_name':i['project_name'], 
				'requestor':i['requestor'], 
				'supplier':i['supplier'], 
				'supplier_contact':i['supplier_contact'], 
				'item_description':i['item_description'], 
				'CPN':i['CPN'], 
				'PID':i['PID'], 
				'manufacturer_part_num':i['manufacturer_part_num'], 
				'submit_date':i['submit_date'], 
				'tracking':i['tracking'], 
				'status':i['status'], 
				'location':i['location'], 
				'checkout_date':i['checkout_date'], 
				'return_date':i['return_date'], 
				'times_used':i['times_used'],
				'current_user':i['current_user'], 
				'current_project':i['current_project'], 
				'SN':i['SN']
			}

		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	return render_template('checkedout_parts.html', checkedout_parts=checkedout_parts, user=current_user.name)

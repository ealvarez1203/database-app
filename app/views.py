from flask import render_template, flash, redirect, url_for, request
from flask.ext.login import login_user, login_required, logout_user, current_user
from app import app, db, login_manager, bcrypt
from forms import *
from models import User, Parts, History
import time, xlrd, os
from werkzeug import secure_filename

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

# route for handling the login page logic
@app.route('/', methods=['GET','POST'])
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
			return redirect(url_for('home'))
	return render_template('create_user.html', form=form, error=error)

@app.route('/home')
@login_required
def home():
	return render_template('main.html', user=current_user.name)

@app.route('/History/<serialNumber>/')
@login_required
def show_history(serialNumber):
	cur = db.engine.execute('select project, user, checkout_date, return_date, detail from History where Part_SN=:s', s=serialNumber)
	history = [dict(project=row[0], user=row[1], checkout_date=row[2], return_date=row[3], detail=row[4]) for row in cur.fetchall()]
	print serialNumber
	return render_template('history.html', history=history)

@app.route('/Part/<id>/')
@login_required
def show_part_info(id):
	cur = db.engine.execute('select PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description,\
							 CPN, PID, manufacturer_part_num, submit_date, tracking, status, current_user, current_project,\
							 checkout_date, return_date, times_used, count(*) from parts where id=:i group by PR, PO, part, project_name,\
							 requestor, supplier, supplier_contact, item_description, CPN, PID, manufacturer_part_num,\
							 submit_date, tracking, status', i=id)
	part = [dict(PR=row[0], 
				PO=row[1], 
				part=row[2], 
				project_name=row[3], 
				requestor=row[4], 
				supplier=row[5],
				supplier_contact=row[6], 
				item_description=row[7], 
				CPN=row[8], 
				PID=row[9], 
				manufacturer_part_num=row[10],
				submit_date=row[11], 
				tracking=row[12], 
				status=row[13],
				current_user=row[14],
				current_project=row[15],
				checkout_date=row[16],
				return_date=row[17],
				times_used=row[18],
				qty=row[19]
			) for row in cur.fetchall()]
	return render_template('part_info.html', part=part[0])

@app.route('/Upload', methods=['GET','POST'])
@login_required
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
	            	d = {keys[col_index]: sheet.cell(row_index, col_index).value for col_index in xrange(sheet.ncols)}
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
												time.strftime("%m/%d/%Y"), # xlrd function needed
												(int(i['TRACKING#']) if isinstance(i['TRACKING#'], float) else i['TRACKING#']), 
												'Unavailable'
					          			))
	            	db.session.commit()
	            	flash('The excel file was sucessfully uploaded!')
	            except KeyError, key:
	            	error = 'Column missing: %s'%key
	            	return render_template('upload_file.html', error=error)

	            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename)) #remove file from tmp folder
	            return redirect(url_for('upload_file'))
	        else:
	        	error= " Wrong File Format"

	return render_template('upload_file.html', error=error)

@app.route('/inventory')
@login_required
def inventory():
	cur = db.engine.execute('select PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description,\
							 CPN, PID, manufacturer_part_num, submit_date, tracking, status, id, count(*) from parts group by PR, PO,\
							 part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							 manufacturer_part_num, submit_date, tracking, status')
	parts = [dict(PR=row[0], 
				PO=row[1], 
				part=row[2], 
				project_name=row[3], 
				requestor=row[4], 
				supplier=row[5],
				supplier_contact=row[6], 
				item_description=row[7], 
				CPN=row[8], 
				PID=row[9], 
				manufacturer_part_num=row[10],
				submit_date=row[11], 
				tracking=row[12], 
				status=row[13], 
				id=row[14],
				qty=row[15]
			) for row in cur.fetchall()]
	return render_template('inventory.html', parts=parts)

@app.route('/add_part', methods=['GET', 'POST'])
@login_required
def add_part():
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

	form = AddPart(request.form)
	form.status.choices = [('Available', 'Available'), ('Unavailable', 'Unavailable')]
	form.part.choices = [('DIMM', 'DIMM'), ('CPU', 'CPU'), ('CABLES', 'CABLES'), ('CHASSIS', 'CHASSIS'), ('HDD', 'HDD'),
							('MEZZ-CARD', 'MEZZ-CARD'), ('PROTOTYPE', 'PROTOTYPE'), ('PSU', 'PSU'), ('RAID-UNIT', 'RAID-UNIT'), ('TPM', 'TPM')]
	if request.method == 'POST' and form.validate():
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
				submit_date = form.submit_date.raw_data[0],
				tracking = form.tracking.data,
				status = form.status.data
				)
			db.session.add(part)
		db.session.commit()
		flash("Part was added to the database")
		return redirect(url_for('home'))
	return render_template('add_part.html', form=form, POs=POs, PRs=PRs, project_names=project_names, requestors=requestors,
		suppliers=suppliers, supplier_contacts=supplier_contacts, item_descriptions=item_descriptions, CPNs=CPNs, PIDs=PIDs,
		manufacturer_part_nums=manufacturer_part_nums, tracking=tracking)

@app.route('/delete_part', methods=['GET', 'POST'])
@login_required
def delete_part():
	#query parts by quantities
	cur = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description,\
							 CPN, PID, manufacturer_part_num, submit_date, tracking, status, current_user, current_project,\
							 checkout_date, return_date, times_used, count(*) from parts group by PR, PO, part, project_name,\
							 requestor, supplier, supplier_contact, item_description, CPN, PID, manufacturer_part_num,\
							 submit_date, tracking, status')
	parts = [dict(id=row[0]-(row[20]-1),
				PR=row[1], 
				PO=row[2], 
				part=row[3], 
				project_name=row[4], 
				requestor=row[5], 
				supplier=row[6],
				supplier_contact=row[7], 
				item_description=row[8], 
				CPN=row[9], 
				PID=row[10], 
				manufacturer_part_num=row[11],
				submit_date=row[12], 
				tracking=row[13], 
				status=row[14],
				current_user=row[15],
				current_project=row[16],
				checkout_date=row[17],
				return_date=row[18],
				times_used=row[19],
				qty=row[20]
			) for row in cur.fetchall()]
	
	if request.method == 'POST':
		delete_ids = request.form.getlist("do_delete")
		if delete_ids:
			return redirect(url_for('confirm_delete', delete_ids=delete_ids))
		else:
			flash('No Part was selected')
	return render_template('delete_part.html', parts=parts)

@app.route('/delete_part/confirm', methods=['GET', 'POST'])
@login_required
def confirm_delete():
	#"""Obtain ids from args"""
	delete_ids = [i.encode('utf-8') for i in request.args.getlist('delete_ids')]
	delete_parts = Parts.query.filter(Parts.id.in_(delete_ids)).all()
	delete_parts = [dict(id=delete.id, 
						PR=delete.PR, 
						PO=delete.PO, 
						part=delete.part, 
						requestor=delete.requestor, 
						supplier=delete.supplier, 
						supplier_contact=delete.supplier_contact, 
						item_description=delete.item_description, 
						CPN=delete.CPN, 
						PID=delete.PID, 
						manufacturer_part_num=delete.manufacturer_part_num, 
						submit_date=delete.submit_date, 
						tracking=delete.tracking, 
						status=delete.status, 
						project_name=delete.project_name,
						current_user=delete.current_user,
						current_project=delete.current_project,
						checkout_date=delete.checkout_date,
						return_date=delete.return_date,
						times_used=delete.times_used
					) for delete in delete_parts]

	#"""Add quantity variable to each delete_parts"""
	for i in delete_parts:
		kwargs = {'PR':i['PR'], 'PO':i['PO'], 'part':i['part'], 'requestor':i['requestor'], 'supplier':i['supplier'], 'supplier_contact':i['supplier_contact'],
				'item_description':i['item_description'], 'CPN':i['CPN'], 'PID':i['PID'], 'manufacturer_part_num':i['manufacturer_part_num'], 
				 'submit_date':i['submit_date'], 'tracking':i['tracking'], 'status':i['status'], 'project_name':i['project_name'], 'current_user':i['current_user'],
				 'current_project':i['current_project'], 'checkout_date':i['checkout_date'], 'return_date':i['return_date'], 'times_used':i['times_used']}
		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	if request.method == 'POST':
		delete_ids = sorted([int(i) for i in request.form.getlist("delete_ids")])
		quantities = [int(i) for i in request.form.getlist('qty')]
		print delete_ids
		print quantities

		for i in range(len(delete_ids)):
			#	get all attributes of part
			Part = Parts.query.filter_by(id=delete_ids[i]).first()
			#	get ids of rows that match these attributes
			kwargs = {'PR':Part.PR, 'PO':Part.PO, 'part':Part.part, 'requestor':Part.requestor, 'supplier':Part.supplier, 'supplier_contact':Part.supplier_contact,
				'item_description':Part.item_description, 'CPN':Part.CPN, 'PID':Part.PID, 'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 'tracking':Part.tracking, 'status':Part.status, 'project_name':Part.project_name, 'current_user':Part.current_user,
				'current_project':Part.current_project, 'checkout_date':Part.checkout_date, 'return_date':Part.return_date, 'times_used':Part.times_used}
			ids = [j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()] 
			
			#	iterate through these parts only for specified quantities
			iterator = 1
			while iterator <= quantities[i]:
				Parts.query.filter(Parts.id == ids[iterator-1]).delete()	
				iterator += 1
			db.session.commit()
		flash('The parts were deleted')
		return redirect(url_for('home'))
	return render_template('confirm_delete.html', delete_parts=delete_parts, delete_ids=delete_ids)

@app.route('/update', methods=['GET', 'POST'])
@login_required
def update_part():
	if request.method == 'POST':
		keyword = request.form['keyword']
		if keyword:
			return redirect(url_for('update_keyword_search', keyword=keyword))
		else:
			flash('Please enter a keyword!')
	return render_template('update_part.html')

@app.route('/update_part_search/<type>', methods= ['GET', 'POST'])
@login_required
def update_part_search(type):
	if type=='OTHER':
		cur = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
								manufacturer_part_num, submit_date, current_project, current_user, tracking, status, checkout_date, return_date, times_used,\
								count(*) from parts where (part <> :a and part <> :b and part <> :c and part <> :d and part <> :e and part <> :f\
								and part <> :g and part <> :h and part <> :i and part <> :k and part <> :l) group by part, supplier, item_description,\
								CPN, PID, manufacturer_part_num, PO, PR, project_name, requestor, supplier_contact, tracking, status, checkout_date, return_date,\
								times_used, current_user, current_project', a='DIMM', b='CPU', c='PSU', d='PROTOTYPE', e='MEZZ-CARD', f='HEATSINK', g='HDD',
								h='RAID-UNIT', i='CHASSIS', k='CABLES', l='TPM')
		part = [dict(id=row[0]-(row[20]-1), 
						PR=row[1], 
						PO=row[2], 
						part=row[3], 
						project_name=row[4], 
						requestor=row[5], 
						supplier=row[6],
						supplier_contact=row[7], 
						item_description=row[8], 
						CPN=row[9], 
						PID=row[10], 
						manufacturer_part_num=row[11],
						submit_date=row[12],
						current_project=row[13],
						current_user=row[14], 
						tracking=row[15], 
						status=row[16],
						checkout_date=row[17],
						return_date=row[18], 
						times_used=row[19],
						qty=row[20]
				) for row in cur.fetchall()]  #store them in a list of dictionaries
	else:	
		#retrieve parts where part=type and status=Available
		cur = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
								manufacturer_part_num, submit_date, current_project, current_user, tracking, status, checkout_date, return_date,\
								times_used, count(*) from parts where part=:p group by part, supplier, item_description, CPN, PID, \
								manufacturer_part_num, PO, PR, project_name, requestor, supplier_contact, tracking, status, checkout_date, return_date,\
								times_used, current_user, current_project', p=type)
		part = [dict(id=row[0]-(row[20]-1), 
						PR=row[1], 
						PO=row[2], 
						part=row[3], 
						project_name=row[4], 
						requestor=row[5], 
						supplier=row[6],
						supplier_contact=row[7], 
						item_description=row[8], 
						CPN=row[9], 
						PID=row[10], 
						manufacturer_part_num=row[11],
						submit_date=row[12],
						current_project=row[13], 
						current_user=row[14],
						tracking=row[15], 
						status=row[16],
						checkout_date=row[17],
						return_date=row[18], 
						times_used=row[19],
						qty=row[20]
				) for row in cur.fetchall()]  #store them in a list of dictionaries
	if request.method == 'POST':
		update_id = request.form.getlist("do_update")
		if len(update_id)>1:
			flash('Please select only one item')
		elif len(update_id)==1:
			return redirect(url_for('confirm_update', update_id=update_id))
		else:
			flash('No part was selected')
	return render_template('update_part_search.html', type=type, part=part)

@app.route('/update_keyword_search/<keyword>', methods=['GET', 'POST'])
@login_required
def update_keyword_search(keyword):
	cur = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, times_used,\
							current_user, count(*) from parts where part like :k or project_name like :k or supplier like :k or status \
							like :k or item_description like :k or CPN like :k or PID like :k or manufacturer_part_num like :k or current_project\
							like :k or current_user like :k group by part, supplier, item_description, CPN, PID,\
							manufacturer_part_num, PO, PR, project_name, requestor, supplier_contact, tracking, status, checkout_date, return_date,\
							times_used, current_user, current_project', k='%' + keyword + '%')
	part = [dict(id=row[0]-(row[20]-1), 
				PR=row[1], 
				PO=row[2], 
				part=row[3], 
				project_name=row[4], 
				requestor=row[5], 
				supplier=row[6],
				supplier_contact=row[7], 
				item_description=row[8], 
				CPN=row[9], 
				PID=row[10], 
				manufacturer_part_num=row[11],
				submit_date=row[12],
				current_project=row[13], 
				tracking=row[14], 
				status=row[15],
				checkout_date=row[16],
				return_date=row[17], 
				times_used=row[18],
				current_user=row[19],
				qty=row[20]
			) for row in cur.fetchall()]  #store them in a list of dictionaries
	if request.method == 'POST':
		update_id = request.form.getlist("do_update")
		if len(update_id) >1:
			flash('Please select only one item') 
		elif len(update_id) ==1:
			return redirect(url_for('confirm_update', update_id=update_id))
		else:
			flash('No part was selected')
	return render_template('update_keyword_search.html', keyword=keyword, part=part)

@app.route('/update_part/confirm', methods=['GET', 'POST'])
@login_required
def confirm_update():
	# project names options for autocomplete field
	project_names = ["%s" %i for i in db.session.query(Parts.project_name).group_by(Parts.project_name).all()]
	project_names = [x.encode('utf-8') for x in project_names]
	#   obtain ids from arg list
	update_id = request.args.get('update_id').encode('utf-8')
	update_part = Parts.query.get(update_id)
	update_part = dict(id=update_part.id, 
						PR=update_part.PR, 
						PO=update_part.PO, 
						part=update_part.part, 
						requestor=update_part.requestor, 
						supplier=update_part.supplier, 
						supplier_contact=update_part.supplier_contact, 
						item_description=update_part.item_description, 
						CPN=update_part.CPN, 
						PID=update_part.PID, 
						manufacturer_part_num=update_part.manufacturer_part_num, 
						submit_date=update_part.submit_date, 
						tracking=update_part.tracking, 
						status=update_part.status, 
						project_name=update_part.project_name,
						current_user=update_part.current_user,
						current_project=update_part.current_project,
						times_used=update_part.times_used
					) 
	#   add quantity variable to each update_part
	kwargs = {'PR':update_part['PR'], 'PO':update_part['PO'], 'part':update_part['part'], 'requestor':update_part['requestor'], 'supplier':update_part['supplier'], 'supplier_contact':update_part['supplier_contact'],
			'item_description':update_part['item_description'], 'CPN':update_part['CPN'], 'PID':update_part['PID'], 'manufacturer_part_num':update_part['manufacturer_part_num'], 
			 'submit_date':update_part['submit_date'], 'tracking':update_part['tracking'], 'status':update_part['status'], 'project_name':update_part['project_name'], 'current_project':update_part['current_project'],
			 'current_user':update_part['current_user'], 'times_used':update_part['times_used']}
	qty = Parts.query.filter_by(**kwargs).count()
	update_part['qty'] = qty 

	#setup form class UpdatePart
	form = UpdatePart(request.form)
	form.status.choices = [('Available', 'Available'), ('Unavailable', 'Unavailable')]
	form.status.default = update_part['status'].encode('utf-8')

	if request.method == 'POST' and form.validate():
		update_id = int(request.form.get('update_id'))
		quantity = int(request.form.get('update_qty'))

		#	get all attributes of part
		Part = Parts.query.filter_by(id=update_id).first()
		#	get ids of rows that match these attributes
		kwargs = {'PR':Part.PR, 'PO':Part.PO, 'part':Part.part, 'requestor':Part.requestor, 'supplier':Part.supplier, 'supplier_contact':Part.supplier_contact,
			'item_description':Part.item_description, 'CPN':Part.CPN, 'PID':Part.PID, 'manufacturer_part_num':Part.manufacturer_part_num, 
			'submit_date':Part.submit_date, 'tracking':Part.tracking, 'status':Part.status, 'project_name':Part.project_name, 'current_project':Part.current_project,
			'current_user':Part.current_user, 'times_used':Part.times_used}
		ids = sorted([j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()]) 
		
		#if input form input field is empty keep previous value for column
		form.PR.data = (Part.PR if not form.PR.data else form.PR.data)
		form.PO.data = (Part.PO if not form.PO.data else form.PO.data)
		form.part.data = (Part.part if not form.part.data else form.part.data)
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

		#	iterate through these parts only for specified quantities
		iterator=1
		while iterator<=quantity:
			db.engine.execute('update parts set PR=:a, PO=:b, part=:c, requestor=:d, supplier=:e, supplier_contact=:f, item_description=:g,\
						CPN=:h, PID=:i, manufacturer_part_num=:j, submit_date=:k, tracking=:l, status = :m, project_name=:n where id=:o',
						a=form.PR.data, b=form.PO.data, c=form.part.data, d=form.requestor.data, e=form.supplier.data, f=form.supplier_contact.data,
						g=form.item_description.data, h=form.CPN.data, i=form.PID.data, j=form.manufacturer_part_num.data, k=form.submit_date.data,
						l=form.tracking.data, m=form.status.data, n=form.project_name.data, o=ids[iterator-1])
			iterator += 1

		db.session.commit()
		flash('The part has been updated!')
		return redirect(url_for('home'))
	return render_template('confirm_update.html', part=update_part, update_id=update_id, form=form, project_names=project_names)

@app.route('/return_part', methods=['GET', 'POST'])
@login_required
def return_part():
	#	retrieve data where current_user=currentuser and status=unavailable
	cur = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							manufacturer_part_num, submit_date, current_project, tracking, status, times_used checkout_date, return_date, count(*)\
							from parts where current_user=:user and status=:s group by part, supplier, item_description, CPN, PID, \
							manufacturer_part_num', user=current_user.name, s="Unavailable")
	parts = [dict(id=row[0], 
				PR=row[1], 
				PO=row[2], 
				part=row[3], 
				project_name=row[4], 
				requestor=row[5], 
				supplier=row[6],
				supplier_contact=row[7], 
				item_description=row[8], 
				CPN=row[9], 
				PID=row[10], 
				manufacturer_part_num=row[11],
				submit_date=row[12],
				current_project=row[13], 
				tracking=row[14], 
				status=row[15],
				checkout_date=row[16],
				return_date=row[17], 
				qty=row[18]
			) for row in cur.fetchall()]  #store them in a list of dictionaries

	if request.method == 'POST':
		return_ids = request.form.getlist("do_return")
		if return_ids:
			return redirect(url_for('confirm_return', return_ids=return_ids))
		else:
			flash('No Part was selected')
	return render_template('return_part.html', parts=parts)

@app.route('/return_part/confirm', methods=['GET', 'POST'])
@login_required
def confirm_return():
	#   obtain ids from arg list
	return_ids = [i.encode('utf-8') for i in request.args.getlist('return_ids')]
	return_parts = Parts.query.filter(Parts.id.in_(return_ids)).all()
	return_parts = [dict(id=part.id, 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						project_name=part.project_name
					) for part in return_parts]
	#   add quantity variable to each checkout_parts
	for i in return_parts:
		kwargs = {'PR':i['PR'], 'PO':i['PO'], 'part':i['part'], 'requestor':i['requestor'], 'supplier':i['supplier'], 'supplier_contact':i['supplier_contact'],
				'item_description':i['item_description'], 'CPN':i['CPN'], 'PID':i['PID'], 'manufacturer_part_num':i['manufacturer_part_num'], 
				 'submit_date':i['submit_date'], 'tracking':i['tracking'], 'status':i['status'], 'project_name':i['project_name']}
		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	if request.method == 'POST':
		date = time.strftime("%m/%d/%Y")
		#	get ids and quentities from form
		return_ids = sorted([int(i) for i in request.form.getlist('return_ids')])
		quantities = [int(i) for i in request.form.getlist('qty')]

		for i in range(len(return_ids)):
			#	get all attributes of part
			Part = Parts.query.filter_by(id=return_ids[i]).first()
			#	get ids of rows that match these attributes
			kwargs = {'PR':Part.PR, 'PO':Part.PO, 'part':Part.part, 'requestor':Part.requestor, 'supplier':Part.supplier, 'supplier_contact':Part.supplier_contact,
				'item_description':Part.item_description, 'CPN':Part.CPN, 'PID':Part.PID, 'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 'tracking':Part.tracking, 'status':Part.status, 'project_name':Part.project_name}
			ids = [j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()] 
			
			#	iterate through these parts only for specified quantities
			while quantities[i] > 0:
				db.engine.execute('update parts set status = :s, return_date = :r,\
							current_user=:u, current_project=:p where id=:i', s='Available', r=date,
							u=None, p=None, i=ids[quantities[i]-1])	
				quantities[i] -= 1
			db.session.commit()
		flash('The parts were checked out!')
		return redirect(url_for('home'))
	return render_template('confirm_return.html', return_parts=return_parts, return_ids=return_ids)

@app.route('/checkout_part', methods=['GET', 'POST'])
@login_required
def checkout_part():
	if request.method == 'POST':
		keyword = request.form['keyword']
		if keyword:
			return redirect(url_for('keyword_search', keyword=keyword))
		else:
			flash('Please enter a keyword!')	
	return render_template('checkout_part.html')

@app.route('/search/<type>', methods= ['GET', 'POST'])
@login_required
def part_search(type):
	#retrieve parts where part=type and status=Available
	if type=='OTHER':
		cur1 = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
								manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, times_used,\
								count(*) from parts where status=:s and (part <> :a and part <> :b and part <> :c and part <> :d and part <> :e\
								and part <> :f and part <> :g and part <> :h and part <> :i and part <> :j and part <> :k) group by part,\
								supplier, item_description, CPN, PID, manufacturer_part_num', a='DIMM', b='CPU', c='HEATSINK', d='CHASSIS',
								e='CABLES', f='MEZZ-CARD', g='PSU', h='TPM', i='PROTOTYPE', j='HDD', k='RAID-UNIT', s="Available")
		part_available = [dict(id=row[0], 
								PR=row[1], 
								PO=row[2], 
								part=row[3], 
								project_name=row[4], 
								requestor=row[5], 
								supplier=row[6],
								supplier_contact=row[7], 
								item_description=row[8], 
								CPN=row[9], 
								PID=row[10], 
								manufacturer_part_num=row[11],
								submit_date=row[12],
								current_project=row[13], 
								tracking=row[14], 
								status=row[15],
								checkout_date=row[16],
								return_date=row[17], 
								times_used=row[18],
								qty=row[19]
							) for row in cur1.fetchall()]  #store them in a list of dictionaries
		#retrieve parts where part=type and status=Available
		cur2 = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
								manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, times_used,\
								current_user, count(*) from parts where status=:s and (part <> :a and part <> :b and part <> :c and part <> \
								:d and part <> :e and part <> :f and part <> :g and part <> :h and part <> :i and part <> :j and part <> :k)\
								group by part, supplier, item_description, CPN, PID, manufacturer_part_num', a='DIMM', b='CPU', c='HEATSINK',
								d='CHASSIS', e='CABLES', f='MEZZ-CARD', g='PSU', h='TPM', i='PROTOTYPE', j='HDD', k='RAID-UNIT', s="Unavailable")
		part_unavailable = [dict(id=row[0], 
							PR=row[1], 
							PO=row[2], 
							part=row[3], 
							project_name=row[4], 
							requestor=row[5], 
							supplier=row[6],
							supplier_contact=row[7], 
							item_description=row[8], 
							CPN=row[9], 
							PID=row[10], 
							manufacturer_part_num=row[11],
							submit_date=row[12],
							current_project=row[13], 
							tracking=row[14], 
							status=row[15],
							checkout_date=row[16],
							return_date=row[17], 
							times_used=row[18],
							current_user=row[19],
							qty=row[20]) for row in cur2.fetchall()]  #store them in a list of dictionaries
	else:
		cur1 = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
								manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, times_used,\
								count(*) from parts where (part=:p and status=:s) group by part, supplier, item_description, CPN, PID, \
								manufacturer_part_num', p=type, s="Available")
		part_available = [dict(id=row[0], 
								PR=row[1], 
								PO=row[2], 
								part=row[3], 
								project_name=row[4], 
								requestor=row[5], 
								supplier=row[6],
								supplier_contact=row[7], 
								item_description=row[8], 
								CPN=row[9], 
								PID=row[10], 
								manufacturer_part_num=row[11],
								submit_date=row[12],
								current_project=row[13], 
								tracking=row[14], 
								status=row[15],
								checkout_date=row[16],
								return_date=row[17], 
								times_used=row[18],
								qty=row[19]
							) for row in cur1.fetchall()]  #store them in a list of dictionaries
		#retrieve parts where part=type and status=Available
		cur2 = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
								manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, times_used,\
								current_user, count(*) from parts where part=:p and status=:s group by part, supplier, item_description, CPN, PID, \
								manufacturer_part_num', p=type, s="Unavailable")
		part_unavailable = [dict(id=row[0], 
							PR=row[1], 
							PO=row[2], 
							part=row[3], 
							project_name=row[4], 
							requestor=row[5], 
							supplier=row[6],
							supplier_contact=row[7], 
							item_description=row[8], 
							CPN=row[9], 
							PID=row[10], 
							manufacturer_part_num=row[11],
							submit_date=row[12],
							current_project=row[13], 
							tracking=row[14], 
							status=row[15],
							checkout_date=row[16],
							return_date=row[17], 
							times_used=row[18],
							current_user=row[19],
							qty=row[20]) for row in cur2.fetchall()]  #store them in a list of dictionaries
	if request.method == 'POST':
		checkout_ids = request.form.getlist("do_checkout")
		if checkout_ids:
			return redirect(url_for('confirm_checkout', checkout_ids=checkout_ids))
		else:
			flash('No part was selected')
	return render_template('part_search.html', type=type, part_available=part_available, part_unavailable=part_unavailable)

@app.route('/keyword_search/<keyword>', methods=['GET', 'POST'])
@login_required
def keyword_search(keyword):
	cur1 = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, times_used,\
							current_user, count(*) from parts where status=:s and (part like :k or project_name like :k or supplier\
							like :k or item_description like :k or CPN like :k or PID like :k or manufacturer_part_num like :k or current_project\
							like :k or current_user like :k) group by part, supplier, item_description, CPN, PID,\
							manufacturer_part_num', k='%' + keyword + '%', s="Available")
	part_available = [dict(id=row[0], 
						PR=row[1], 
						PO=row[2], 
						part=row[3], 
						project_name=row[4], 
						requestor=row[5], 
						supplier=row[6],
						supplier_contact=row[7], 
						item_description=row[8], 
						CPN=row[9], 
						PID=row[10], 
						manufacturer_part_num=row[11],
						submit_date=row[12],
						current_project=row[13], 
						tracking=row[14], 
						status=row[15],
						checkout_date=row[16],
						return_date=row[17], 
						times_used=row[18],
						current_user=row[19],
						qty=row[20]
			) for row in cur1.fetchall()]  #store them in a list of dictionaries
	cur2 = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, times_used,\
							current_user, count(*) from parts where status==:s and (part like :k or project_name like :k or supplier\
							like :k or item_description like :k or CPN like :k or PID like :k or manufacturer_part_num like :k or current_project\
							like :k or current_user like :k) group by part, supplier, item_description, CPN, PID,\
							manufacturer_part_num', k='%' + keyword + '%', s="Unavailable")
	part_unavailable = [dict(id=row[0], 
						PR=row[1], 
						PO=row[2], 
						part=row[3], 
						project_name=row[4], 
						requestor=row[5], 
						supplier=row[6],
						supplier_contact=row[7], 
						item_description=row[8], 
						CPN=row[9], 
						PID=row[10], 
						manufacturer_part_num=row[11],
						submit_date=row[12],
						current_project=row[13], 
						tracking=row[14], 
						status=row[15],
						checkout_date=row[16],
						return_date=row[17], 
						times_used=row[18],
						current_user=row[19],
						qty=row[20]
			) for row in cur2.fetchall()]  #store them in a list of dictionaries
	if request.method == 'POST':
		checkout_ids = request.form.getlist("do_checkout")
		if checkout_ids:
			return redirect(url_for('confirm_checkout', checkout_ids=checkout_ids))
		else:
			flash('No part was selected')
	return render_template('keyword_search.html', keyword=keyword, part_available=part_available, part_unavailable=part_unavailable)

@app.route('/checkout_part/confirm', methods=['GET', 'POST'])
@login_required
def confirm_checkout():
	# project names options for autocomplete field
	project_names = ["%s" %i for i in db.session.query(Parts.project_name).group_by(Parts.project_name).all()]
	project_names = [x.encode('utf-8') for x in project_names]
	#   obtain ids from arg list
	checkout_ids = [i.encode('utf-8') for i in request.args.getlist('checkout_ids')]
	checkout_parts = Parts.query.filter(Parts.id.in_(checkout_ids)).all()
	checkout_parts = [dict(id=part.id, 
						PR=part.PR, 
						PO=part.PO, 
						part=part.part, 
						requestor=part.requestor, 
						supplier=part.supplier, 
						supplier_contact=part.supplier_contact, 
						item_description=part.item_description, 
						CPN=part.CPN, 
						PID=part.PID, 
						manufacturer_part_num=part.manufacturer_part_num, 
						submit_date=part.submit_date, 
						tracking=part.tracking, 
						status=part.status, 
						project_name=part.project_name
					) for part in checkout_parts]
	#   add quantity variable to each checkout_parts
	for i in checkout_parts:
		kwargs = {'PR':i['PR'], 'PO':i['PO'], 'part':i['part'], 'requestor':i['requestor'], 'supplier':i['supplier'], 'supplier_contact':i['supplier_contact'],
				'item_description':i['item_description'], 'CPN':i['CPN'], 'PID':i['PID'], 'manufacturer_part_num':i['manufacturer_part_num'], 
				 'submit_date':i['submit_date'], 'tracking':i['tracking'], 'status':i['status'], 'project_name':i['project_name']}
		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	form = CheckoutPart(request.form)
	if request.method == 'POST' and form.validate():
		date = time.strftime("%m/%d/%Y")
		checkout_ids = sorted([int(i) for i in request.form.getlist('checkout_ids')])
		quantities = [int(i) for i in request.form.getlist('qty')]

		for i in range(len(checkout_ids)):
			#	get all attributes of part
			Part = Parts.query.filter_by(id=checkout_ids[i]).first()
			#	get ids of rows that match these attributes
			kwargs = {'PR':Part.PR, 'PO':Part.PO, 'part':Part.part, 'requestor':Part.requestor, 'supplier':Part.supplier, 'supplier_contact':Part.supplier_contact,
				'item_description':Part.item_description, 'CPN':Part.CPN, 'PID':Part.PID, 'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 'tracking':Part.tracking, 'status':Part.status, 'project_name':Part.project_name}
			ids = [j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()] 
			#	record history of part
			history = History(
				serial= ids[quantities[i]],
				project= form.project.data,
				user=current_user.name,
				checkout_date=date,
				return_date= form.return_date.raw_data[0],
				detail= form.details.data
			)
			db.session.add(history)
			db.session.commit()
			#	iterate through these parts only for specified quantities
			while quantities[i] > 0:
				db.engine.execute('update parts set status = :s, checkout_date = :d, return_date = :r, times_used=times_used+1,\
							current_user=:u, current_project=:p where id=:i', s='Unavailable', d=date, r=form.return_date.raw_data[0],
							u=current_user.name, p=form.project.data, i=ids[quantities[i]-1])	
				quantities[i] -= 1
			db.session.commit()
		flash('The parts were checked out!')
		return redirect(url_for('home'))
	return render_template('confirm_checkout.html', checkout_parts=checkout_parts, checkout_ids=checkout_ids, form=form, project_names=project_names)
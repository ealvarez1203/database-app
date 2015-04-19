from flask import render_template, flash, redirect, url_for, request
from flask.ext.login import login_user, login_required, logout_user, current_user
from app import app, db, login_manager, bcrypt
from forms import LoginForm, CreateUserForm, AddPart 
from models import User, Parts
import time

@app.errorhandler(404)
def not_found_error(error):
	return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
	db.session.rollback()
	return render_template('500.html'), 500

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
	form = CreateUserForm()
	if form.validate_on_submit():
		user = User(
			name=form.username.data,
			email=form.email.data,
			password=form.password.data
		)
		db.session.add(user)
		db.session.commit()
		login_user(user)
		return redirect(url_for('home'))
	return render_template('create_user.html', form=form)

@app.route('/home')
@login_required
def home():
	return render_template('main.html')

@app.route('/History/<serialNumber>/')
@login_required
def show_history(serialNumber):
	return "show_history"

@app.route('/inventory')
@login_required
def inventory():
	cur = db.engine.execute('select PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description,\
							 CPN, PID, manufacturer_part_num, submit_date, tracking, status, count(*) from parts group by PR, PO,\
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
				qty=row[14]
			) for row in cur.fetchall()]
	return render_template('inventory.html', parts=parts)

@app.route('/add_part', methods=['GET', 'POST'])
@login_required
def add_part():
	parts = ["%s" %i for i in db.session.query(Parts.part).group_by(Parts.part).all()]
	parts = [x.encode('utf-8') for x in parts]
	project_names = ["%s" %i for i in db.session.query(Parts.project_name).group_by(Parts.project_name).all()]
	project_names = [x.encode('utf-8') for x in project_names]
	requestors = ["%s" %i for i in db.session.query(Parts.requestor).group_by(Parts.requestor).all()]
	requestors = [x.encode('utf-8') for x in requestors]
	suppliers = ["%s" %i for i in db.session.query(Parts.supplier).group_by(Parts.supplier).all()]
	suppliers = [x.encode('utf-8') for x in suppliers]
	supplier_contacts = ["%s" %i for i in db.session.query(Parts.supplier_contact).group_by(Parts.supplier_contact).all()]
	supplier_contacts = [x.encode('utf-8') for x in supplier_contacts]
	item_descriptions = ["%s" %i for i in db.session.query(Parts.item_description).group_by(Parts.item_description).all()]
	item_descriptions = [x.encode('utf-8') for x in item_descriptions]

	form = AddPart(request.form)
	form.status.choices = [('Available', 'Available'), ('Unavailable', 'Unavailable')]
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
	return render_template('add_part.html', form=form, parts=parts, project_names=project_names, requestors=requestors,
		suppliers=suppliers, supplier_contacts=supplier_contacts, item_descriptions=item_descriptions)

@app.route('/delete_part', methods=['GET', 'POST'])
@login_required
def delete_part():
	#query parts by quantities
	cur = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description,\
							 CPN, PID, manufacturer_part_num, submit_date, tracking, status, count(*) from parts group by PR, PO,\
							 part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							 manufacturer_part_num, submit_date, tracking, status')
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
				tracking=row[13], 
				status=row[14], 
				qty=row[15]
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
						project_name=delete.project_name
					) for delete in delete_parts]
	#"""Add quantity variable to each delete_parts"""
	for i in delete_parts:
		kwargs = {'PR':i['PR'], 'PO':i['PO'], 'part':i['part'], 'requestor':i['requestor'], 'supplier':i['supplier'], 'supplier_contact':i['supplier_contact'],
				'item_description':i['item_description'], 'CPN':i['CPN'], 'PID':i['PID'], 'manufacturer_part_num':i['manufacturer_part_num'], 
				 'submit_date':i['submit_date'], 'tracking':i['tracking'], 'status':i['status'], 'project_name':i['project_name']}
		qty = Parts.query.filter_by(**kwargs).count()
		i['qty'] = qty 

	if request.method == 'POST':
		delete_ids = sorted([int(i) for i in request.form.getlist("delete_ids")])
		quantities = [int(i) for i in request.form.getlist('qty')]
		print quantities

		for i in range(len(delete_ids)):
			#	get all attributes of part
			Part = Parts.query.filter_by(id=delete_ids[i]).first()
			#	get ids of rows that match these attributes
			kwargs = {'PR':Part.PR, 'PO':Part.PO, 'part':Part.part, 'requestor':Part.requestor, 'supplier':Part.supplier, 'supplier_contact':Part.supplier_contact,
				'item_description':Part.item_description, 'CPN':Part.CPN, 'PID':Part.PID, 'manufacturer_part_num':Part.manufacturer_part_num, 
				'submit_date':Part.submit_date, 'tracking':Part.tracking, 'status':Part.status, 'project_name':Part.project_name}
			ids = [j[0] for j in db.session.query(Parts.id).filter_by(**kwargs).all()] 
			
			#	iterate through these parts only for specified quantities
			while quantities[i] > 0:
				Parts.query.filter(Parts.id == ids[quantities[i]-1]).delete()	
				quantities[i] -= 1
			db.session.commit()
		flash('The parts were deleted')
		return redirect(url_for('home'))
	return render_template('confirm_delete.html', delete_parts=delete_parts, delete_ids=delete_ids)

@app.route('/return_part', methods=['GET', 'POST'])
@login_required
def return_part():
	#retrieve data where current_user=currentuser and status=unavailable
	cur = db.engine.execute('select id, PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							manufacturer_part_num, submit_date, current_project, tracking, status, checkout_date, return_date, count(*)\
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
	return "confirm_return"

@app.route('/checkout_part', methods=['GET', 'POST'])
@login_required
def checkout_part():
	return render_template('checkout_part.html')

@app.route('/checkout_part/confirm', methods=['GET', 'POST'])
@login_required
def confirm_checkout():
	return "confirm_checkout"

@app.route('/search/<type>', methods= ['GET', 'POST'])
@login_required
def part_search(type):
	kwargs = {'part':type, 'status':'Available'}
	part_available = Parts.query.filter_by(**kwargs).all()
	kwargs = {'part':type, 'status':'Unvailable'}
	part_unavailable = Parts.query.filter_by(**kwargs).all()
	return render_template('part_search.html', type=type, part_available=part_available, part_unavailable=part_unavailable)
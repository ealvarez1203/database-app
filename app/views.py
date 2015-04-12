from flask import render_template, flash, redirect, url_for, request
from flask.ext.login import login_user, login_required, logout_user, current_user
from app import app, db, login_manager, bcrypt
from forms import LoginForm, CreateUserForm
from models import User

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
	"""Displays all parts in database"""
	cur = db.engine.execute('select PR, PO, part, project_name, requestor, supplier, supplier_contact, item_description,\
							 CPN, PID, manufacturer_part_num, submit_date, tracking, status, count(*) from parts group by PR, PO,\
							 part, project_name, requestor, supplier, supplier_contact, item_description, CPN, PID,\
							 manufacturer_part_num, submit_date, tracking, status')
	parts = [dict(PR=row[0], PO=row[1], part=row[2], project_name=row[3], requestor=row[4], supplier=row[5],
				supplier_contact=row[6], item_description=row[7], CPN=row[8], PID=row[9], manufacturer_part_num=row[10],
				submit_date=row[11], tracking=row[12], status=row[13], qty=row[14]) for row in cur.fetchall()]
	return render_template('inventory.html', parts=parts)

@app.route('/add_part', methods=['GET', 'POST'])
@login_required
def add_part():
	return "add_part"

@app.route('/delete_part', methods=['GET', 'POST'])
@login_required
def delete_part():
	return "delete_part"

@app.route('/return_part', methods=['GET', 'POST'])
@login_required
def return_part():
	return "return_part"

@app.route('/return_part/confirm', methods=['GET', 'POST'])
@login_required
def confirm_return():
	return "confirm_return"

@app.route('/checkout_part', methods=['GET', 'POST'])
@login_required
def checkout_part():
	return "checkout_part"

@app.route('/checkout_part/confirm', methods=['GET', 'POST'])
@login_required
def confirm_checkout():
	return "confirm_checkout"
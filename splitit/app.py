from flask import Flask, render_template , flash , redirect , url_for , session , request , logging
from flask_mysqldb import MySQL
from wtforms import Form,  StringField, TextAreaField, PasswordField, validators , IntegerField
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import date


app=Flask(__name__)


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'blackflag'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql=MySQL(app)

def setSessionVariables(data):
	session['logged_in'] = True
	session['id'] = data['id']
	session['name'] = data['name']

class RegisterForm(Form):
	name=StringField('Name', [validators.Length(min=1, max=50)])
	phone=IntegerField('Number', [validators.NumberRange(min=10**9, max=10**10-1)])
	email=StringField('Email', [validators.Length(min=6,max=50)])
	password=PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm',message='Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

def SQLquery(s):
	cur= mysql.connection.cursor()
	res= cur.execute(s)
	if s.split()[0].lower() == 'select':
		if res:
			return cur.fetchall()
		return None
	mysql.connection.commit()

@app.route('/')
def index():
	return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/activities', methods=['GET','POST'])
def activities():
	if request.method == 'POST':
		s = request.form['delete']
		SQLquery("DELETE FROM history WHERE id1='%s' AND id2='%s' AND amount='%s' AND description='%s' AND dateAdded='%s'" %(int(s['id1']),int(s['id2']),int(s['amount']),s['description'],s['dateAdded']) )
		return redirect(url_for('activities'))
	session['data']=SQLquery("SELECT * FROM history WHERE id1='%s' or id2='%s'" %(session['id'],session['id']))
	if not session['data']:
		flash("No activities yet!", 'danger')
		return render_template('activities.html')
	for i in range(len(session['data'])):
		if session['data'][i]['id1'] == session['id']:
			s = SQLquery("SELECT name FROM users WHERE id='%s'" %(session['data'][i]['id2']))
			session['data'][i]['name'] = s[0]['name'] 
		if session['data'][i]['id2'] == session['id']:
			s = SQLquery("SELECT name FROM users WHERE id='%s'" %(session['data'][i]['id1']))
			session['data'][i]['name'] = s[0]['name'] 
	return render_template('activities.html')

@app.route('/newgroup',methods=['GET','POST'])
def newgroup():
	session['friends'] = SQLquery("SELECT name, balance, phone, id FROM users,friends WHERE (id2='%s' AND id=id1) OR (id1='%s' AND id=id2)" %(session['id'],session['id']))
	if request.method == 'POST':
		selected_users = request.form.getlist("users")
		if not selected_users:
			flash("No members selected",'danger')
			return render_template('newgroup.html')
		SQLquery("INSERT INTO groups(name, size) VALUES ('%s', '%s')" %(request.form['name'], len(selected_users)+1 ))
		gr_id = SQLquery("SELECT id FROM groups ORDER BY id")
		gr_id = gr_id[-1]['id']
		SQLquery("INSERT INTO group_data VALUES ('%s','%s')" %(session['id'], gr_id))			
		for i in selected_users:
			SQLquery("INSERT INTO group_data VALUES ('%s','%s')" %(i, gr_id))
		return redirect(url_for('groups'))
	return render_template('newgroup.html')

@app.route('/grouptransactions',methods=['GET','POST'])
def grouptransactions():
	if request.method == 'POST':
		# create new transaction query
		description=request.form['description']
		amount=int(request.form['money'])
		date=request.form['date']
		friend = int(request.form['friend'])
		SQLquery("INSERT INTO group_transactions(id,amount,group_id,description,dateAdded) VALUES ('%s','%s','%s','%s','%s')" %(friend,amount,session['cur_group_id'], description, date) )
		#SQLquery("UPDATE group_transactions SET amount = amount + '%d' WHERE id='%s'" %(amount1,session['id']))
	tr = SQLquery("SELECT * FROM group_transactions WHERE group_id='%s'" %(session['cur_group_id']) )
	group_data = SQLquery("SELECT group_data.id, users.name FROM group_data, users WHERE group_id = '%s' and users.id = group_data.id" %(session['cur_group_id']) )
	session['group_data'] = group_data
	balance = { i['id']:0 for i in group_data }
	mp = { i['id']:i['name'] for i in group_data }
	session['mp']=mp
	session['balance']=balance
	if not tr:
		flash("no transaction", 'danger')
	else:
		s = 0
		for i in tr:
			s += i['amount']/session['cur_group_size']
			balance[i['id']] -= i['amount']
		for i in balance:
			balance[i] += s
	return render_template('grouptransactions.html')


@app.route('/groups',methods=['GET','POST'])
def groups():
	session['groups']=SQLquery("SELECT group_id, size, name FROM groups, group_data WHERE group_data.id='%s' " %(session['id']) )
	if request.method == 'POST':
		if request.form.get('create'):
			return redirect(url_for('newgroup'))
		else:
			session['cur_group_id']=request.form['view']
			a=SQLquery("SELECT * FROM group_data WHERE group_id='%s'" %(session['cur_group_id']))
			session['cur_group_size'] = len(a)
			return redirect(url_for('grouptransactions'))
	return render_template('groups.html')


def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized','danger')
			return redirect(url_for('login'))
	return wrap

@app.route('/transactions', methods=['GET','POST'])
@is_logged_in
def transactions():
	if request.method == 'POST':
		description=request.form['description']
		amount=int(request.form['money'])
		date=request.form['date']
		value=int(request.form['transtype'])
		calc_amount = [-amount,amount,amount/2,-amount/2][value]
		IDcur = session['id']
		IDfriend = session['idFriend']
		IDcur, IDfriend = min(IDcur, IDfriend), max(IDcur, IDfriend)
		print("INSERT INTO history(id1,id2,amount,description,dateAdded) VALUES ('%s','%s','%s','%s','%s')" %(IDcur, IDfriend, calc_amount, description,date))
		SQLquery("UPDATE friends SET balance=balance+'%d' WHERE id1='%s' AND id2='%s'" %(calc_amount, IDcur, IDfriend))
		SQLquery("INSERT INTO history(id1,id2,amount,description,dateAdded) VALUES ('%s','%s','%s','%s','%s')" %(IDcur, IDfriend, calc_amount, description,date))
		return redirect(url_for('dashboard'))
	return render_template('transactions.html')

@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		user = SQLquery("SELECT * FROM users WHERE email='%s'" %(request.form['email']))
		if not user:
			return render_template('login.html', error='Invalid Email Id')
		user = user[0]
		if not sha256_crypt.verify(request.form['password'],user['password']):
			return render_template('login.html', error='Invalid Password')
		setSessionVariables(user)
		flash('You are now logged in.', 'success')
		return redirect(url_for('dashboard'))
	return render_template('login.html')


@app.route('/register', methods=['GET','POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		emailCheck = SQLquery("SELECT * FROM users WHERE email='%s'" %(form.email.data))
		phoneCheck = SQLquery("SELECT * FROM users WHERE phone='%s'" %(form.phone.data))
		if emailCheck or phoneCheck:
			if emailCheck:
				flash("Email Id already in use", 'danger')
			if phoneCheck:
				flash("Phone number already in use", 'danger')
		else:
			passHash = sha256_crypt.encrypt(str(form.password.data))
			SQLquery("INSERT INTO users(name,email,phone,password) VALUES ('%s', '%s', '%s', '%s')" %(form.name.data, form.email.data, form.phone.data, passHash))
			flash("You are now registered", 'success')
			return redirect(url_for('login'))
	return render_template('register.html', form=form)

@app.route('/search', methods=['GET','POST'])
@is_logged_in
def search():
	form = RegisterForm(request.form)
	if request.method == 'POST':
		searchResult = SQLquery("SELECT * FROM users WHERE phone='%s'" %(form.phone.data))
		if searchResult:
			IDfound = searchResult[0]['id']
			IDcur = session['id']
			isFriend = SQLquery("SELECT * FROM friends WHERE (id1='%s' AND id2='%s') OR (id1='%s' AND id2='%s')" %(IDcur,IDfound,IDfound,IDcur))
			if isFriend:
				flash("You are already friends", 'danger')
			else:
				if IDfound != IDcur:
					if IDfound < IDcur:
						IDfound, IDcur = IDcur, IDfound
					SQLquery("INSERT INTO friends VALUES ('%s','%s','%s')" %(IDcur,IDfound,0) )
					flash("You are now friends with " + searchResult[0]['name'], 'success')
				else:
					flash("You cannot send a request to yourself",'danger')
			return redirect(url_for('dashboard'))
		else:
			flash("This number does not exist.", 'danger')
	return render_template('search.html', form=form)

@app.route('/dashboard',methods=['GET','POST'])
@is_logged_in
def dashboard():
	if request.method == 'POST':
		if request.form.get('plus'):
			friend = SQLquery("SELECT id,name FROM users WHERE phone='%s'" %(request.form['plus']))[0]
			session['idFriend'] = friend['id']
			session['nameFriend'] = friend['name']
			return redirect(url_for('transactions'))
		elif request.form.get('settle'):
			friend = SQLquery("SELECT id,name FROM users WHERE phone='%s'" %(request.form['settle']))[0]
			IDfriend = friend['id']
			IDcur = session['id']
#			SQLquery("INSERT INTO history(id1,id2,amount,description,dateAdded) VALUES ('%s','%s','%s','%s','%s')" %(IDcur, IDfriend, 0,"settled up",date.today()))		
			SQLquery("UPDATE friends SET balance='%d' WHERE id1='%s' AND id2='%s'" %(0, IDcur, IDfriend))
			flash("You are now settled up with " + friend['name'],'success')
			return redirect(url_for('dashboard'))
	session['friends'] = SQLquery("SELECT name, balance, phone FROM users,friends WHERE (id2='%s' AND id=id1) OR (id1='%s' AND id=id2)" %(session['id'],session['id']))
	return render_template('dashboard.html')

@app.route('/logout')
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))


if __name__ == '__main__':
	app.secret_key='secret123'
	app.run(debug=True)

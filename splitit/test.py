from flask_mysqldb import MySQL
from flask import Flask, render_template

app=Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'blackflag'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def home():
	cur = mysql.connection.cursor()
	cur.execute('select id from friends where friends.id2 = %s xor friends.id2 = %s', [2,2])
	data = cur.fetchall()
	for row in data:
		print(row['id'])
	return render_template('home.html')
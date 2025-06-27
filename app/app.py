from flask import Flask, render_template
import mysql.connector
import os
from report_submission import bp as reports_bp

app = Flask(__name__)

# SECRET_KEY (for flash messages & sessions)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')

# Initial Configs =================================================
# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'mysql')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'x')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'x')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'flask_db')
print("aaa", flush=True)
print(app.config['MYSQL_HOST'],app.config['MYSQL_USER'],app.config['MYSQL_PASSWORD'],app.config['MYSQL_DB'], flush=True)

app.register_blueprint(reports_bp)

def get_db_connection():
    conn = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    return conn


# App routes ============================================================
@app.route('/')
def index():
    return render_template('0_index.html')


@app.route('/admin_dashboard.html')
def admin():
    return render_template('admin_dashboard.html')

@app.route('/report')
def report():
    return redirect(url_for('reports.submit_report'))

# custom route to test conn to db
@app.route('/test_db.html')
def test_db():
    data = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test;')
        data = cursor.fetchall()
        db_status = 'Connected to MySQL'
        cursor.close()
        conn.close()
    except Exception as e:
        db_status = f'MySQL connection error: {str(e)}'
    return render_template('test_db.html', db_status=db_status, data=data)

# This route is the catch-all so u guys don't have to make a specific route for each page everytime, IT HAS TO BE THE LAST ROUTE
# Not secure, if u want a specific page to be secure OR with custom logic, make a new route above
@app.route('/<filename>')
def catch_all(filename):
    print(filename, flush=True)
    return render_template(filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')


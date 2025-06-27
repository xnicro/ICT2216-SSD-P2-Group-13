import os
from flask import Flask, render_template
from report_submission import bp as reports_bp    # ① import your blueprint

app = Flask(__name__)

# ——————————————
# ② SECRET_KEY (for flash messages & sessions)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')

# MySQL configurations (same as before)
app.config['MYSQL_HOST']     = os.getenv('MYSQL_HOST', 'mysql')
app.config['MYSQL_USER']     = os.getenv('MYSQL_USER', 'x')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'x')
app.config['MYSQL_DB']       = os.getenv('MYSQL_DB', 'flask_db')
print("aaa", flush=True)
print(app.config['MYSQL_HOST'],app.config['MYSQL_USER'],app.config['MYSQL_PASSWORD'],app.config['MYSQL_DB'], flush=True)


# ① register the blueprint *after* you’ve set up config
app.register_blueprint(reports_bp)               

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin_dashboard.html')

# ③ you can either delete this, or keep it if you still want
#     a `/report` shortcut to redirect into the blueprint:
@app.route('/report')
def report():
    return redirect(url_for('reports.submit_report'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

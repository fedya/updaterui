from flask import Flask, render_template, request, redirect
import json
import subprocess
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mytable (
            package TEXT,
            version_rosa TEXT,
            version_upstream TEXT,
            url TEXT,
            status TEXT,
            upgrade TEXT
        )
    ''')
    cursor.execute('''SELECT package, version_rosa, version_upstream, url, status, upgrade FROM mytable''')
    rows = cursor.fetchall()
    conn.close()
    return rows


@app.route('/')
def index():
    rows = get_db_connection()
    return render_template('table.html', rows=rows)

@app.route('/run_command', methods=['POST'])
def run_command():
    package = request.form['package']
    exit_code = subprocess.call(['/bin/echo', 'Hello, World!'])

    with open('output.json', 'r') as f:
        data = json.load(f)
        
    for row in data:
        if row['package'] == package:
            row['upgrade'] = 'done' if exit_code == 0 else 'failed'
    
    with open('output.json', 'w') as f:
        json.dump(data, f)
        
    return redirect('/')

@app.route("/run_single", methods=['POST'])
def run_single():
    package = request.form['package']
    subprocess.run(['./generate.py --generate-single {}'.format(package)], shell=True)
    rows = get_db_connection()
    return render_template('table.html', rows=rows)

@app.route("/check_all")
def check_all():
    subprocess.run(['./generate.py --generate-all'], shell=True)
    rows = get_db_connection()
    return render_template('table.html', rows=rows)

if __name__ == '__main__':
    app.run(debug=True)

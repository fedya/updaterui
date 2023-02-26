from flask import Flask, render_template, request, redirect
import json
import subprocess
import sqlite3

app = Flask(__name__)

@app.route('/')
def index():
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT package, version_rosa, version_upstream, url, status, upgrade FROM mytable''')
    rows = cursor.fetchall()
    conn.close()
    return render_template('table.html', rows=rows)


@app.route('/run_command', methods=['POST'])
def run_command():
    package = request.form['package']
    print(package)
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
    # execute the check_all.py script
    package = request.form['package']
    subprocess.run(['./generate.py --generate-single {}'.format(package)], shell=True)
    # reload data from output.json file
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT package, version_rosa, version_upstream, url, status, upgrade FROM mytable''')
    rows = cursor.fetchall()
    conn.close()
    return render_template('table.html', rows=rows)

@app.route("/check_all")
def check_all():
    # execute the check_all.py script
    subprocess.run(['./generate.py --generate-all'], shell=True)
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT package, version_rosa, version_upstream, url, status, upgrade FROM mytable''')
    rows = cursor.fetchall()
    conn.close()
    return render_template('table.html', rows=rows)

if __name__ == '__main__':
    app.run(debug=True)


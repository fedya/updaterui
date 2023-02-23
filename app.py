from flask import Flask, render_template, request, redirect
import json
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    with open('output.json', 'r') as f:
        data = json.load(f)
    return render_template('table.html', data=data)


@app.route('/run_command', methods=['POST'])
def run_command():
    package = request.form['package']
    print(package)
    exit_code = subprocess.call(['/usr/bin/echo', 'Hello, World!'])

    with open('output.json', 'r') as f:
        data = json.load(f)
        
    for row in data:
        if row['package'] == package:
            row['upgrade'] = 'done' if exit_code == 0 else 'failed'
    
    with open('output.json', 'w') as f:
        json.dump(data, f)
        
    return redirect('/')


@app.route("/check_all")
def check_all():
    # execute the check_all.py script
    subprocess.run(['/home/fdrt/webservice/6/generate.py'])
    # reload data from output.json file
    with open('output.json', 'r') as f:
        data = json.load(f)
    return render_template('table.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)


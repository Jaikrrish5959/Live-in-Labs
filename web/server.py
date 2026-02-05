from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Route for the main dashboard
@app.route('/')
def index():
    return render_template('index.html')

# Route to serve the JSON log
@app.route('/data/log')
def get_log():
    return send_from_directory('static/data', 'simulation_log.json')

if __name__ == '__main__':
    print("Starting server at http://localhost:5000")
    app.run(debug=True, port=5000)

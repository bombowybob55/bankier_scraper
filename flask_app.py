from flask import Flask, send_file
import os

app = Flask(__name__)

@app.route('/')
def home():
    # Serve the generated HTML file
    # Ensure the file exists, otherwise return a message
    if os.path.exists('swetrowo.html'):
        return send_file('swetrowo.html')
    else:
        return "swetrowo.html not found. Please run generate_swetrowo.py first.", 404

if __name__ == '__main__':
    app.run()

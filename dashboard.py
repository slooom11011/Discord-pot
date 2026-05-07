from flask import Flask, render_template_string, request, redirect
import sqlite3, os

app = Flask(__name__)
DB = 'levels.db'
TOKEN = os.environ.get('ADMIN_TOKEN', '1234')

HTML = '''<h1>اللوحة شغالة ✅</h1><p>لو شفت هذا معناها ضبطت</p>'''

@app.route('/')
def home():
    return HTML

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

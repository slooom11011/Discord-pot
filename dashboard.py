from flask import Flask, render_template_string
import aiosqlite, os

app = Flask(__name__)
DB = 'levels.db'

# صفحة HTML بسيطة للوحة
HTML = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <title>لوحة تحكم البوت</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Tahoma; background: #2c2f33; color: white; padding: 20px; }
       .card { background: #23272a; padding: 20px; border-radius: 8px; margin: 10px 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: right; border-bottom: 1px solid #444; }
        h1 { color: #7289da; }
    </style>
</head>
<body>
    <h1>🤖 لوحة تحكم البوت</h1>
    <div class="card">
        <h2>🏆 توب 10 أعضاء</h2>
        <table>
            <tr><th>#</th><th>ID العضو</th><th>XP</th><th>اللفل</th></tr>
            {% for i, user in enumerate(top) %}
            <tr><td>{{ i+1 }}</td><td>{{ user[0] }}</td><td>{{ user[1] }}</td><td>{{ user[2] }}</td></tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

@app.route('/')
async def home():
    async with aiosqlite.connect(DB) as c:
        top = await (await c.execute('SELECT user_id, xp, level FROM levels ORDER BY xp DESC LIMIT 10')).fetchall()
    return render_template_string(HTML, top=top)

def run_dashboard():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

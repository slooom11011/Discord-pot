from flask import Flask, render_template_string, request, redirect
import sqlite3, os

app = Flask(__name__)
DB = 'levels.db'
TOKEN = os.environ.get('admin', '0506078842') # غير 1234 لو ما حطيت متغير

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
        table { width: 100%; border-collapse: collapse; margin-top:10px; }
        th, td { padding: 10px; text-align: right; border-bottom: 1px solid #444; }
        h1 { color: #7289da; }
        input, button { padding: 8px; border-radius: 5px; border: none; margin: 2px; }
        input { background: #40444b; color: white; }
        button { background: #7289da; color: white; cursor: pointer; }
      .danger { background: #e74c3c; }
      .success { background: #43b581; }
      .login { max-width: 300px; margin: 100px auto; text-align: center; }
    </style>
</head>
<body>
    {% if not authed %}
    <div class="card login">
        <h1>تسجيل الدخول</h1>
        <form method="POST">
            <input type="password" name="token" placeholder="كلمة السر" required>
            <button type="submit">دخول</button>
        </form>
        {% if error %}<p style="color:#e74c3c">{{ error }}</p>{% endif %}
    </div>
    {% else %}
    <h1>🤖 لوحة تحكم البوت</h1>
    <div class="card">
        <h2>🏆 توب 10 أعضاء</h2>
        <table>
            <tr><th>#</th><th>ID العضو</th><th>XP</th><th>اللفل</th><th>تحكم</th></tr>
            {% for i, user in enumerate(top) %}
            <tr>
                <td>{{ i+1 }}</td>
                <td>{{ user[0] }}</td>
                <td>{{ user[1] }}</td>
                <td>{{ user[2] }}</td>
                <td>
                    <form method="POST" action="/edit" style="display:inline;">
                        <input type="hidden" name="user_id" value="{{ user[0] }}">
                        <input type="number" name="xp" value="{{ user[1] }}" style="width:80px">
                        <button type="submit" class="success">تعديل XP</button>
                    </form>
                    <form method="POST" action="/reset" style="display:inline;" onsubmit="return confirm('متأكد تبي تصفره؟')">
                        <input type="hidden" name="user_id" value="{{ user[0] }}">
                        <button type="submit" class="danger">تصفير</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
        {% if not top %}<p>مافي بيانات للحين</p>{% endif %}
    </div>
    {% endif %}
</body>
</html>
'''

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

@app.route('/', methods=['GET', 'POST'])
def home():
    authed = request.cookies.get('auth') == TOKEN
    error = None
    top = []

    if request.method == 'POST':
        if request.form.get('token') == TOKEN:
            resp = redirect('/')
            resp.set_cookie('auth', TOKEN)
            return resp
        else:
            error = "كلمة السر غلط"

    if authed:
        try:
            con = get_db()
            top = con.execute('SELECT user_id, xp, level FROM levels ORDER BY xp DESC LIMIT 10').fetchall()
            con.close()
        except: pass

    return render_template_string(HTML, top=top, enumerate=enumerate, authed=authed, error=error)

@app.route('/edit', methods=['POST'])
def edit():
    if request.cookies.get('auth')!= TOKEN: return "ممنوع", 403
    user_id = request.form['user_id']
    xp = int(request.form['xp'])
    level = int(xp ** 0.5) // 10 # نفس معادلة البوت حقك
    con = get_db()
    con.execute('UPDATE levels SET xp=?, level=? WHERE user_id=?', (xp, level, user_id))
    con.commit()
    con.close()
    return redirect('/')

@app.route('/reset', methods=['POST'])
def reset():
    if request.cookies.get('auth')!= TOKEN: return "ممنوع", 403
    user_id = request.form['user_id']
    con = get_db()
    con.execute('UPDATE levels SET xp=0, level=0 WHERE user_id=?', (user_id,))
    con.commit()
    con.close()
    return redirect('/')

def run_dashboard():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

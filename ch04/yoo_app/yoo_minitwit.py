from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash
from contextlib import closing

# 벡자이크에서 제공하는 페스워드 알고리즘
from werkzeug.security import check_password_hash , generate_password_hash

DATABASE = 'yoo_minitwit.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'ydh'

app = Flask(__name__ ,static_url_path='/static')
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    # closing 객체에 연결한 db를 인자로 넘기고 with 블럭이 끝나면 종료하거나 제거하라는 뜻.
    with closing(connect_db()) as db:
        with app.open_resource('ydh_schema.sql',mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select user_id , username from user where user_id = ?' , [session['user_id']],one=True)

@app.teardown_request
def teardown_request(exception):
    if hasattr(g,'db'):
        g.db.close()


@app.route('/')
def hello():
    return render_template('main.html',links={'register':'회원가입','login':'로그인','timeline':'타임라인'})
    # return render_template('main.html',links={'login':{'link':'login','txt':'로그인'}, 'join':{'link':'join','txt':'회원가입'}})


@app.route('/timeline')
def timeline():
    if 'user_id' in session:
        return render_template('timeline.html',userdata=g.user)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    print('logout work')
    flash('You were logged out')
    session.pop('user_id',None)
    session.clear()
    g.user = None
    return redirect(url_for('login'))
      

@app.route('/register',methods=['GET','POST'])
def register():
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                '@' not in  request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'not same password'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            g.db.execute('''insert into user(username , email , pw_hash) values (?,?,?)''',
            [request.form['username'],request.form['email'],generate_password_hash(request.form['password'])])
            g.db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html',error=error)
        
@app.route('/login',methods=['GET','POST'])
def login():
    # session.clear()
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        print('test POST')
        user = query_db('''select * from user where username = ?''',[request.form['username']],one=True)
        if user is None:
            print('test USER NOT DEFINE')
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            
            return redirect(url_for('timeline'))
    return render_template('login.html',error=error)




def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = g.db.execute('select user_id from user where username = ?',
                       [username]).fetchone()
    return rv[0] if rv else None

    
 
#  query_db ( 실행할 질의문(sql) , 질의문에 들어갈 인자가 듀플형태로 들어감(ex. where name=? > ?에 들어갈 인자 바인딩 변수), 
#           결과의 첫번째 요소만 받을 것인지 전체 요소를 받을 것인지 결정하는 인자 (boolean))
def query_db(query, args=(), one=False):
    # g 객체에서 세팅한 db 객체를 활용해 인자로 받은 질의문과 바인딩 변수로 커서를 받는다.
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0],value) for idx, value in enumerate(row)) for row in cur.fetchall()]

    return (rv[0] if rv else None) if one else rv

    
if __name__ == '__main__':
        init_db()
        app.run(host='0.0.0.0',port=5000,debug=True)


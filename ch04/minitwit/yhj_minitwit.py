from __future__ import with_statement
import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from contextlib import closing
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash
from werkzeug.security import check_password_hash, generate_password_hash

# 미니 트윗 개요
"""
* 기능
    - 사용자 등록
    - 로그인/로그아웃
    - 트윗글 등록
    - 팔로우/언팔로우
    - 타임라인(트윗글 목록) 지원
* 기술요소
    - SQLite
    - 이미지를 외부URL(gravata) 이용해 표현
    - 비밀키 이용한 해싱
    - 신사2(Jinja2) 템플릿 엔진
"""

# -*- coding: utf-8 -*-
"""
    MiniTwit
    ~~~~~~~~

    A microblogging application written with Flask and sqlite3.

    :copyright: (c) 2019 by hyunji Yoo
    :license: BSD, see LICENSE for more details.
"""

# configuration
DATABASE = 'minitwit.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__) # 플라스크 애플리케이션 생성
app.config.from_object(__name__) 
app.config.from_envvar('MINITWIT_SETTINGS', silent=True)


# DB 연결
def connect_db():
    """Returns a new connection to the database."""
    # config 속성에 정의된 DATABASE 파일위치를 넘겨줌 > DB 연결
    return sqlite3.connect(app.config['DATABASE']) 


def init_db():
    """Creates the database tables."""
    # 데이터베이스 연결을 closing 클래스의 인자로 넣어줌.
    # with 블럭이 끝나면 closing클래스로 넘어온 객체를 닫거나 제거! 
    # (파일을 with로 열면 닫는 것 생략한 것처럼)
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# return 자료형 : list
def query_db(query, args=(), one=False): # False는 전체 rows (True는 한 개 row)
    """Queries the database and returns a list of dictionaries."""
    # cur는 DB 실행한 결과에 대한 커서
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               # Fetch: 커서에서 전체 레코드를 꺼내서 로우를 한줄씩 읽는다 
               for idx, value in enumerate(row)) for row in cur.fetchall()] 
    return (rv[0] if rv else None) if one else rv


""" 리스트 컴프리핸션
Q. 1부터 10까지 정수 나열하고자 할 때
------------------------------------
numbers = []
for n in range(1, 10+1):
    numbers.append(n)
------------------------------------
[x for x in range(10)]
"""


def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = g.db.execute('select user_id from user where username = ?',
                       [username]).fetchone()
    return rv[0] if rv else None


def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


# gravatar
# 이메일 주소를 해싱해서 같은 이미지를 보여주며, 인터넷에서 글쓴이의 아바타(avatar)처럼 제공된다.
def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), 
         size)


# 각 요청에 앞서서 실행되는 함수 정의
@app.before_request
def before_request():
    """Make sure we are connected to the database each request and look
    up the current user so that we know he's there.
    """
    # print('this is befire request')
    g.db = connect_db()
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?',
                          [session['user_id']], one=True)

"""
** g 객체 = 전역(global) 객체
    - 한 번의 요청에 대해서만 같은 값 유지하고 스레드에 대해 안전
"""

# 응답이 생성된 후에 실행되는 함수 정의
@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()

# 기본 타임라인
@app.route('/')
def timeline():
    """Shows a users timeline or if no user is logged in it will
    redirect to the public timeline.  This timeline shows the user's
    messages as well as all the messages of followed users.
    """
    # 로그인 안했으면 public 타임라인으로 리다이렉트
    if not g.user:
        return redirect(url_for('public_timeline'))
    # 로그인 했으면 기본 타임라인을 보여주면 쿼리 날려준다.
    return render_template('timeline.html', messages=query_db('''
        select message.*, user.* from message, user
        where message.author_id = user.user_id and (
            user.user_id = ? or
            user.user_id in (select whom_id from follower
                                    where who_id = ?))
        order by message.pub_date desc limit ?''',
        [session['user_id'], session['user_id'], PER_PAGE]))


# public 타임라인은 전체 사용자의 트윗 보여주는 화면
@app.route('/public')
def public_timeline():
    """Displays the latest messages of all users."""
    return render_template('timeline.html', messages=query_db('''
        select message.*, user.* from message, user
        where message.author_id = user.user_id
        order by message.pub_date desc limit ?''', [PER_PAGE]))
        # 메세지 쓴 날짜를 내림차순으로 limit 수만큼 message테이블과 user테이블을 조인하여 전체를 가져온다.


# 사용자 타임라인
@app.route('/<username>')
def user_timeline(username):
    """Display's a users tweets."""
    # 매개변수로 넘어온 username으로 profile_user에 저장
    profile_user = query_db('select * from user where username = ?',
                            [username], one=True)
    if profile_user is None:
        abort(404)
    followed = False
    if g.user:
        followed = query_db('''select 1 from follower where
            follower.who_id = ? and follower.whom_id = ?''',
            [session['user_id'], profile_user['user_id']], # 팔로우와 팔로잉이 존재하면 followed에 True 대입
            one=True) is not None
    return render_template('timeline.html', messages=query_db('''
            select message.*, user.* from message, user where
            user.user_id = message.author_id and user.user_id = ?
            order by message.pub_date desc limit ?''',
            [profile_user['user_id'], PER_PAGE]), followed=followed,
            profile_user=profile_user)


# 미니트윗의 중심은 사용자이기때문에 /follow/<username> 보다는 /<username>/follow 로 URI를 설계한다!!
@app.route('/<username>/follow')
def follow_user(username):
    """Adds the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    # follow: insert
    g.db.execute('insert into follower (who_id, whom_id) values (?, ?)',
                [session['user_id'], whom_id])
    g.db.commit()
    flash('You are now following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/<username>/unfollow')
def unfollow_user(username):
    """Removes the current user as follower of the given user."""
    if not g.user:
        abort(401)
    whom_id = get_user_id(username)
    if whom_id is None:
        abort(404)
    # unfollow: delete
    g.db.execute('delete from follower where who_id=? and whom_id=?',
                [session['user_id'], whom_id])
    g.db.commit()
    flash('You are no longer following "%s"' % username)
    return redirect(url_for('user_timeline', username=username))


@app.route('/add_message', methods=['POST'])
def add_message():
    """Registers a new message for the user."""
    if 'user_id' not in session:  # 로그인한 사용자인지 확인
        abort(401) # 401: 권한 없는 요청

    # 로그인된 상태라면 사용자 아이디, 추가할 메세지, 현재시각을 데이터베이스에 저장하고 완료.
    if request.form['text']:
        g.db.execute('''insert into 
            message (author_id, text, pub_date)
            values (?, ?, ?)''', (session['user_id'], 
                                  request.form['text'],
                                  int(time.time())))
        g.db.commit()
        flash('Your message was recorded')
    return redirect(url_for('timeline')) # 등록되면 timeline으로 리다이렉트


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user: # user가 있으면
        return redirect(url_for('timeline')) # timeline페이지로 리디렉션
    error = None
    if request.method == 'POST':
        # 폼 데이터로 넘어온 사용자가 미니 트윗에 존재하는 사용자인지 확인
        user = query_db('''select * from user where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id'] # 세션에 로그인된 사용자의 user_id 값을 저장
            return redirect(url_for('timeline'))
    return render_template('login.html', error=error) # user가 없으면 login.html 렌더링


# GET: 뷰제공 | POST: 정보전달
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:  # g 객체에 user 속성이 있으면 (로그인 된 상태)
        return redirect(url_for('timeline'))
    error = None
    # 폼데이터에 대한 유효성 검사
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                 '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            g.db.execute('''insert into user (
                username, email, pw_hash) values (?, ?, ?)''',
                [request.form['username'], request.form['email'],
                # password의 경우 벡자이크에서 제공하는 해시함수 사용하여 일방향-해싱 적용
                generate_password_hash(request.form['password'])])
            g.db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login')) # 로그인 페이지로 리디렉션 (현재 register 페이지인데 등록을 모두 마치면 login 페이지로 리다이렉션)
    return render_template('register.html', error=error)

""" 리다이렉션(redirection)
: 표준 입력이나 표준 출력을 꼭 키보드나 화면으로 하는 것이 아니라 방향을 바꿔서( == 리다이렉션 ) 파일로 입력을 받거나 파일로 출력하도록 변경하는 것
"""


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None) # pop()으로 user_id 삭제
    return redirect(url_for('public_timeline'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
# gravata URL 생성 함수와 그 함수를 템플릿 엔진인 신사2의 필터로 등록
app.jinja_env.filters['gravatar'] = gravatar_url


if __name__ == '__main__':
    init_db() # DB 초기화
    app.run() # 서버 실행
# -*- coding: utf-8 -*-
#  from {모듈명} import {함수이름}
from flask import Flask, url_for , request , render_template , redirect , make_response

app = Flask(__name__, static_url_path='/static')
@app.route('/params/<param1>/<param2>')
def user_params(param1,param2):
    return 'Hello Flask!'

@app.route('/request')
def user_request():
    elem = '<form method="post" action="/response">'
    elem += '<input name="user_email" /></br>'
    elem += '<input name="user_name" /></br>'
    elem += '<button type="submit">전송dd</button>'
    elem += '</form>'
    return elem

@app.route('/response',methods=['GET','POST'])
def user_response():
    if request.method == 'POST':
        return request.form['user_email']+"<br>"+request.form['user_name']
    elif request.method == 'GET':
        return test(request.args['user_name'])

@app.route('/html_test')
def html_test():
    test={'apple':'red', 'banana':'yellow'}
    return render_template('test1.html',fruits=test)

@app.route('/redirect_test')
def redirect_test():
    return redirect(url_for('re_test'))

@app.route('/re_test')
def re_test():
    return "test"

@app.route('/set_cookie')
def set_cookie():
    resp = make_response(render_template('hello.html',param={'href':{"a.html","b.html","c.html"},'caption':{"1","2","3"}}))
    resp.set_cookie('username','flask')
    return resp
    #resp.set_cookie('username','flask')
    #return resp
@app.route('/get_cookie')
def get_cookie():
    username = request.cookies.get('username')
    return username

def test(param):
    return param
        
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)

# -*- coding: utf-8 -*-

# flask 모듈에 있는 flask 클래스를 import
from flask import Flask
app = Flask(__name__)

# view 함수 localhost:5000/ 요청을 받으면 hello_flask 함수를 연결
# <타입:변수> - type은 default 는 string으로 되어있음.
@app.route('/hello/<int:name_index>')
def hello_flask(name_index):
    if name_index == 1:
        return 'Hello Flask!'
    else:
        return 'error'
if __name__ == '__main__':
    app.run()


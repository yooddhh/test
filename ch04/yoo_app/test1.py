from flask import Flask , request


app = Flask(__name__)
app.autosave = True

@app.before_request
def before_request():
    myStr = 'flask'
    print('start %s'%myStr)

@app.after_request
def after_request(response):
    print('end server work')
    return response

@app.route('/')
def hello():
    return 'hello flask'

if __name__ == '__main__':
    app.run()
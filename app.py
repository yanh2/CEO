from flask import Flask, url_for, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import pandas as pd
import openpyxl
import asyncio
import websockets

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Student(db.Model):
    sname = db.Column(db.String(8))
    sid = db.Column(db.String(8), primary_key=True)
    password = db.Column(db.String(20))

    def __init__(self, sname, sid, password):
        self.sname = sname
        self.sid = sid
        self.password = password


class Professor(db.Model):
    pname = db.Column(db.String(8))
    pid = db.Column(db.String(6), primary_key=True)
    password = db.Column(db.String(20))

    def __init__(self, pname, pid, password):
        self.pname = pname
        self.pid = pid
        self.password = password


class Course(db.Model):
    cid = db.Column(db.String(8), primary_key=True)
    cname = db.Column(db.String(20))
    room = db.Column(db.String(3), primary_key=True)
    pid = db.Column(db.String(8))
    sid = db.Column(db.String(8), primary_key=True)
    ctime = db.Column(db.DateTime())

    def __init__(self, cid, cname, room, pid, sid, ctime):
        self.cid = cid
        self.cname = cname
        self.room = room
        self.pid = pid
        self.sid = sid
        self.ctime = ctime


@app.route('/', methods=['GET', 'POST'])
def home():
    """ Session control"""
    if not session.get('logged_in'):
        return render_template('index.html')
    else:
        if request.method == 'POST':
            return render_template('index.html')
        return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login Form"""
    if request.method == 'GET':
        return render_template('login.html')
    else:
        uid = request.form['userid']
        passw = request.form['password']
        try:
            if len(uid) == 7:
                data = Student.query.filter_by(sid=uid).first()
                if not data:
                    error = "존재하지 않는 사용자입니다."
                elif data.password != passw:
                    error = "비밀번호가 올바르지 않습니다."
                else:
                    session.clear()
                    session['user_id'] = uid
                    session['user_name'] = data.sname
                    session['isPro'] = False
                    return render_template('index.html')

            elif len(uid) == 5:
                data = Professor.query.filter_by(pid=uid).first()
                if not data:
                    error = "존재하지 않는 사용자입니다."
                elif data.password != passw:
                    error = "비밀번호가 올바르지 않습니다."
                else:
                    session.clear()
                    session['user_id'] = uid
                    session['user_name'] = data.pname
                    session['isPro'] = True
                    return render_template('index.html')

            else:
                error = "존재하지 않는 사용자입니다."
            flash(error)
            return render_template('login.html')

        except:
            return render_template('login.html')


@app.route('/register_choice')
def register_choice():
    return render_template('register_choice.html')


@app.route('/register_professor', methods=['GET', 'POST'])
def register_professor():
    """Register Form"""
    if request.method == 'POST':
        uid = request.form['userid']
        if len(uid) != 5:
            error = "알맞는 교번(5글자)을 입력하세요."
            flash(error)
            return render_template('register_professor.html')

        if Professor.query.filter_by(pid=uid).first():
            error = "이미 존재하는 아이디입니다."
            flash(error)
            return render_template('register_professor.html')

        new_user = Professor(pname=request.form['username'], pid=request.form['userid'],
                             password=request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        return render_template('login.html', isPro=1)
    return render_template('register_professor.html')


@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    """Register Form"""
    if request.method == 'POST':
        uid = request.form['userid']
        if len(uid) != 7:
            error = "알맞는 학번(7글자)을 입력하세요."
            flash(error)
            return render_template('register_student.html')

        if Student.query.filter_by(sid=uid).first():
            error = "이미 존재하는 아이디입니다."
            flash(error)
            return render_template('register_student.html')

        new_user = Student(sname=request.form['username'], sid=request.form['userid'],
                           password=request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        return render_template('login.html', isPro=0)
    return render_template('register_student.html')


@app.route("/logout")
def logout():
    """Logout Form"""
    session.clear()
    return redirect(url_for('home'))


@app.route("/course_list")
def list_course():
    if session.get('isPro'):
        pid = session.get('user_id')
        courses = Course.query.filter_by(pid=pid).order_by(Course.cname.asc())
        course_list = []
        for course in courses:
            course_list.append((course.cid, course.cname, course.room, course.ctime))

        if len(course_list):
            course_list = list(set(course_list))
            return render_template('course_list.html', course_list=course_list)
        else:
            return render_template('course_list.html')
    error = "권한이 없습니다."
    flash(error)
    return redirect(url_for('home'))


@app.route("/remove_course/<string:cid>,<string:room>")
def remove_course(cid, room):
    for rem in Course.query.filter_by(cid=cid, room=room):
        db.session.delete(rem)
        db.session.commit()
    return redirect('/list_course')


def parser(string):  # string 예시: 2021-02-27T19:26
    dt = string.replace('T', '-').replace(':', '-').split('-')
    return datetime(year=int(dt[0]), month=int(dt[1]), day=int(dt[2]), hour=int(dt[3]), minute=int(dt[4]))


@app.route("/add_course", methods=['GET', 'POST'])
def add_course():
    if request.method == 'POST':
        cname = request.form['cname']
        cid = request.form['cid']
        room = request.form['room']
        pid = session.get('user_id')
        ctime = parser(request.form['datetime'])
        sids = request.form.getlist(key='sids')

        courses = Course.query.filter_by(cid=cid, room=room).all()
        for course in courses:
            db.session.delete(course)
            db.session.commit()

        for sid in sids:
            new = Course(cname=cname, cid=cid, room=room, sid=sid, ctime=ctime, pid=pid)
            db.session.add(new)
            db.session.commit()
        return redirect('/list_course')
    return render_template('add_course.html')


@app.route("/modify_course/<string:cid>-<string:room>", methods=['GET', 'POST'])
def modify_course(cid, room):
    if request.method == 'POST':
        cname = request.form['cname']
        new_cid = request.form['cid']
        new_room = request.form['room']
        pid = session.get('user_id')
        ctime = parser(request.form['datetime'])
        sids = request.form.getlist(key='sids')

        courses = Course.query.filter_by(cid=cid, room=room).all()
        for course in courses:
            db.session.delete(course)
            db.session.commit()

        for sid in sids:
            new = Course(cname=cname, cid=new_cid, room=new_room, sid=sid, ctime=ctime, pid=pid)
            db.session.add(new)
            db.session.commit()
        return redirect('/list_course')

    course_list = Course.query.filter_by(cid=cid, room=room).all()
    sname_list = []
    sid_list = []
    for course in course_list:
        sid = course.sid
        student = Student.query.filter_by(sid=sid).first()
        sid_list.append(student.sid)
        sname_list.append(student.sname)
    if sid_list is not None:
        ctime = str(course_list[0].ctime)
        ctime = ctime.split()
        ctime = ctime[0] + "T" + ctime[1]
        return render_template('modify_course.html', course=course_list[0], ctime=ctime, student_list=zip(sid_list,sname_list))
    return render_template('modify_course.html', course=course_list[0])


@app.route("/upload", methods=['POST'])
def upload():
    f = request.files['file']
    f.save(secure_filename(f.filename))

    df = pd.read_excel(secure_filename(f.filename), engine='openpyxl')
    students = df[df['역할'] == '학생']
    student_list = zip(students['학번'].astype(str).str.replace(r'\.0', ''), students['이름'])

    cid = request.form['cid']
    cname = request.form['cname']
    room = request.form['room']
    ctime = request.form['datetime']
    course = Course(cname=cname, cid=cid, room=room, pid=None, sid=None, ctime=None)

    return render_template('modify_course.html', course=course, ctime=ctime, student_list=student_list)


@app.route("/supervise/<string:cid>-<string:room>", methods=['GET', 'POST'])
def supervise(cid, room):
    return render_template('supervise.html', cid=cid, room=room)


@app.route("/release")
def release():
    return render_template('release.html')


async def accept(websocket, path):
    while True:
        data_rcv = await websocket.recv()
        data_rcv = data_rcv.split()
        sid = data_rcv[0]
        password = data_rcv[1]
        student = Student.query.filter_by(sid=sid, password=password).first()

        if student is None:
            await websocket.send("False")
        else:
            await websocket.send("True")

if __name__ == '__main__':
    app.debug = True
    db.create_all()
    app.secret_key = "123" #session 사용하려면 필요함
    app.run()
    websoc_svr = websockets.serve(accept, "localhost", 5000)
    asyncio.get_event_loop().run_until_complete(websoc_svr)
    asyncio.get_event_loop().run_forever()

import mysql
from flask import Flask, render_template, request, abort, redirect, flash, url_for
from flask_login import login_required

from mysql_db import MySQL
import flask_login
import hashlib

app = Flask(__name__)
app.secret_key = 'asjdfbajSLDFBhjasbfd'
app.config.from_pyfile('config.py')
db = MySQL(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(login):
    cursor = db.db.cursor(named_tuple=True)
    cursor.execute('select id, login, role_id from users where id = %s', (login,))
    user_db = cursor.fetchone()
    if user_db:
        user = User()
        user.id = user_db.id
        user.login = user_db.login
        user.roles_id = user_db.role_id
        return user
    return None


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template("login.html", authorization=False, login="anonimus", login_false=False)


@app.route('/req/take', methods=['POST'])
@login_required
def take():
    book_id = request.form.get("id")
    user_id = request.form.get("user_id")
    book_title = request.form.get("book_title")
    statuss = db.select(None, "status")
    return render_template("add_book.html", book_title=book_title, book_id=book_id, user_id=user_id, statuss=statuss,
                           authorization=True, login_user=flask_login.current_user.login)


@app.route('/login', methods=['GET'])
def login():
    login: str
    if flask_login.current_user.is_anonymous:
        login_user = "anonymus"
    else:
        login_user = flask_login.current_user.login
    return render_template("login.html", authorization=not flask_login.current_user.is_anonymous, login_user=login_user)


@app.route('/', methods=['POST', 'GET'])
def hello_world():
    if request.method == 'GET':
        roles_id = 0
        if flask_login.current_user.is_anonymous:
            login_user = "anonymus"
        else:
            login_user = flask_login.current_user.login
            roles_id = flask_login.current_user.roles_id
        books = db.select(None, "books")

        return render_template("index.html", authorization=not flask_login.current_user.is_anonymous,
                               login_user=login_user, books=books, roles_id=roles_id,
                               user_id=flask_login.current_user.roles_id)
    elif request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        password_hash = hashlib.sha224(password.encode()).hexdigest()
        if username and password:
            cursor = db.db.cursor(named_tuple=True, buffered=True)
            try:
                cursor.execute(
                    "SELECT id,login,role_id FROM users WHERE `login` = '%s' and `password_hash` = '%s'" % (
                        username, password_hash))
                user = cursor.fetchone()
            except Exception:
                cursor.close()
                return render_template("login.html", authorization=False,
                                       login="anonimus", login_false=True)
            cursor.close()
            if user is not None:
                flask_user = User()
                flask_user.id = user.id
                flask_user.login = user.login
                flask_login.login_user(flask_user, remember=True)
                flask_user.roles_id = user.role_id
                return redirect("/")
            else:
                flash("Не правильный логин или пароль")
                return render_template("login.html", authorization=False,
                                       login="anonimus", login_false=True)
        else:
            flash("Не правильный логин или пароль")
            return render_template("login.html", authorization=False,
                                   login="anonimus", login_false=True)


@app.route('/logout', methods=['GET'])
def logout():
    flask_login.logout_user()
    return render_template("login.html", authorization=not flask_login.current_user.is_anonymous, login="anonimus",
                           login_false=False)


@app.route('/req', methods=['GET'])
@login_required
def req():
    requests = db.select(None, "requests")
    date = db.select("date", "requests")
    login = dict(db.select(["id", "login"], "users"))
    roles_id = flask_login.current_user.roles_id
    support = dict(db.select(["id", "title"], "support"))
    status = dict(db.select(["id", "title"], "status"))
    return render_template("req.html", requests=requests, date=date, login=login, support=support, status=status,
                           authorization=not flask_login.current_user.is_anonymous, roles_id=roles_id,
                           login_user=flask_login.current_user.login)


@app.route('/req/delete', methods=['POST'])
@login_required
def book():
    id = request.form.get("id")
    cursor = db.db.cursor()
    cursor.execute("DELETE FROM `books` WHERE `books`.`id` = '%s'" % id)
    db.db.commit()
    cursor.close()
    return redirect("/")


@app.route('/req/new', methods=['POST', 'GET'])
@login_required
def sub_new():
    date = request.form.get("date")
    user_id = request.form.get("user_id")
    book_id = request.form.get("book_id")
    id_status = request.form.get("id_status")
    if date and user_id and book_id:
        cursor = db.db.cursor(named_tuple=True)
        try:
            cursor.execute(
                "INSERT INTO `journal` (`date`,`user_id`, `book_id`,  `status_id`) VALUES ('%s','%s','%s','%s')" % (date,user_id,book_id,id_status))
            db.db.commit()
            cursor.close()
            return redirect("/")
        except Exception:
            support = db.select(["id", "title"], "support")
            status = db.select(["id", "title"], "status")
            return render_template("new.html", login=flask_login.current_user.login, insert_false=True,
                                   support=support,
                                   status=status, authorization=not flask_login.current_user.is_anonymous)
    else:
        support = db.select(["id", "title"], "support")
        status = db.select(["id", "title"], "status")
        return render_template("new.html", login=flask_login.current_user.login, insert_false=True, support=support,
                               status=status, authorization=not flask_login.current_user.is_anonymous)


@app.route('/req/edit', methods=['POST'])
@login_required
def req_edit():
    try:
        request_id = request.form.get("id")
        date = request.form.get("date")
        support_id = request.form.get("id_support")
        status_id = request.form.get("id_status")
        statuss = db.select(["id", "title"], "status")
        supports = dict(db.select(["id", "title"], "support"))

        sub = {
            'request_id': int(request_id),
            'date': date,
            'support_id': int(support_id),
            'status_id': int(status_id),
        }
        return render_template("req_edit.html", sub=sub, supports=supports, statuss=statuss,
                               login=flask_login.current_user.login, request_id=request_id)

    except Exception:
        return redirect(url_for("req"))


@app.route('/req/edit/submit', methods=['POST'])
@login_required
def req_edit_submit():
    request_id = request.form.get("request_id")
    date = request.form.get("date")
    support_id = request.form.get("id_support")
    status_id = request.form.get("id_status")

    if date and support_id and status_id:
        cursor = db.db.cursor(named_tuple=True)
        try:
            cursor.execute(
                "UPDATE `requests` SET  `date` = '%s',  `id_support` = '%s',`id_status` = '%s' WHERE `requests`.`id` = '%s'" % (
                    date, support_id, status_id, request_id))
            db.db.commit()
            cursor.close()
            return redirect("/req")
        except Exception:
            return redirect("/req")
    else:
        return redirect("/req")

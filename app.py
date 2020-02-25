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
    cursor.execute('select id, login, roles_id from users where id = %s', (login,))
    user_db = cursor.fetchone()
    if user_db:
        user = User()
        user.id = user_db.id
        user.login = user_db.login
        user.roles_id = user_db.roles_id
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
                    "SELECT id,login,roles_id FROM users WHERE `login` = '%s' and `password_hash` = '%s'" % (
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
                flask_user.roles_id = user.roles_id
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
                "INSERT INTO `requests` (`date`,`id_login`, `id_book`,  `id_status `) VALUES ('%s','%s','%s','%s')" % (date,user_id,book_id,id_status))
            db.db.commit()
            cursor.close()
            return redirect("/")
        except Exception:
            support = db.select(["id", "title"], "support")
            status = db.select(["id", "title"], "status")
            return redirect("/")
    else:
        return redirect("/")


@app.route('/req/edit', methods=['POST'])
@login_required
def req_edit():
    try:
        book_id = request.form.get("id")
        book_title = request.form.get("book_title")
        author = request.form.get("author")
        date = request.form.get("date")
        statuss = db.select(None, "status")
        return render_template("req_edit.html", book_title=book_title, book_id=book_id,date = date,
                               author = author,
                               statuss=statuss,
                               authorization=True, login_user=flask_login.current_user.login)
    except Exception:
        return redirect("/")


@app.route('/req/edit/submit', methods=['POST'])
@login_required
def req_edit_submit():
    book_title = request.form.get("book_title")
    author = request.form.get("author")
    date = request.form.get("date")
    book_id = request.form.get("book_id")
    if date and author  and book_id:
        cursor = db.db.cursor(named_tuple=True)
        cursor.execute(
            "UPDATE `books` SET  `year` = '%s',  `title` = '%s',`author` = '%s' WHERE `books`.`id` = '%s'" % (
                date, book_title, author, book_id))
        db.db.commit()
        cursor.close()
        return  redirect("/")
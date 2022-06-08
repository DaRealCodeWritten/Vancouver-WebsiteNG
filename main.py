import ssl
import os
from socketio.asyncio_client import AsyncClient
from utils.configreader import config
from werkzeug.utils import secure_filename
from requests import post, get
from mysql.connector import connect
from flask_login.utils import LocalProxy
from flask import request, redirect, Flask, render_template, Response, abort, url_for, send_file, flash
from flask_login import current_user, login_user, logout_user, UserMixin, AnonymousUserMixin, LoginManager


class ActiveUser(UserMixin):
    def __init__(self, cid: int, rating: int, name: str = None):
        self.cid = cid
        self.rating = rating
        self.name = cid if name is None else name

    @property
    def is_authenticated(self):
        return True

    def get_id(self):
        return self.cid


class AnonymousUser(AnonymousUserMixin):
    def __init__(self):
        pass

    @property
    def is_authenticated(self):
        return False


def to_user_object(user: ActiveUser | LocalProxy) -> ActiveUser: # Convert a LocalProxy to an ActiveUser
    return user._get_current_object()


sock = AsyncClient()
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain("cert.pem", "key.key")
app_config = config()
app = Flask(__name__)
app.secret_key = app_config["FLASK_CLIENT_SECRET"]
manager = LoginManager()
manager.anonymous_user = AnonymousUser
manager.init_app(app)
active_users = {}
active_events = {}
database = connect(
    host="localhost",
    user=app_config["DATABASE_USER"],
    password=app_config["DATABASE_PASSWORD"],
    database="czvr"
)


@sock.on("EVENT POSTED")
async def new_event(data):
    uuid = data["uuid"]
    cursor = database.cursor()
    cursor.execute("SELECT * FROM events WHERE uuid = %s", (uuid,))
    if cursor.rowcount == 0:  # Event does not exist
        await sock.emit("ACK", {"status": "error", "message": "ERR_EVENT_MISSING"})
        return
    else:  # Event exists, add to active events
        constructor = {}
        entry = list(cursor)[0]
        name = entry[1]
        banner_url = entry[2]
        description = entry[3]
        start_time = entry[4]
        end_time = entry[5]
        constructor["name"] = name
        constructor["banner_url"] = banner_url
        constructor["description"] = description
        constructor["start_time"] = start_time
        constructor["end_time"] = end_time
        constructor["uuid"] = uuid
        active_events[uuid] = constructor
        await sock.emit("ACK", {"status": "success"})


@sock.on("EVENT DELETED")
async def delete_event(data):
    uuid = data["uuid"]
    if uuid in active_events:
        del active_events[uuid]
        await sock.emit("ACK", {"status": "success"})
    else:
        await sock.emit("ACK", {"status": "error"})


@manager.user_loader
def load_user(user_id: int):
    return active_users.get(int(user_id))


@app.route("/")
async def index():
    if current_user.is_authenticated is False: # User is not logged in
        return render_template("index.html")
    else: # User is logged in
        return render_template("index_active.html", welcome=f"{current_user.name}")


@app.route('/favicon.ico')
async def favicon():
    return redirect("/static/favicon.ico")


@app.route("/delete_user")
async def delete_user():
    if current_user.is_authenticated is False:
        return abort(Response("You are not logged in.", 401))
    else:
        cuser = to_user_object(current_user)
        cursor = database.cursor()
        cursor.execute(f"DELETE FROM {app_config['DATABASE_TABLE']} WHERE cid = %s", (cuser.cid,))
        database.commit()
        logout_user()
        active_users.pop(cuser.cid)
        sock.emit("USER DELETED", {"cid": cuser.cid})
        msg = "User data successfully deleted, you may now close this window or tab"
        msg += "\nYour data on the roster (if applicable) will NOT be deleted."


@app.route("/uploads/files")
async def uploads():
    try:
        return send_file(os.path.join(app.root_path, "uploads\\")+request.args.get("file"), as_attachment=True)
    except FileNotFoundError:
        return abort(Response("File not found.", 404))
    except TypeError:
        return abort(Response("File name was missing from request", 400))


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(os.path.join(app.root_path, "uploads"), filename))
            flash("File successfully uploaded", "message")
            return redirect(url_for("/upload"))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


@app.route("/logout")
async def logout():
    if current_user.is_authenticated:
        cuser = to_user_object(current_user)
        logout_user()
        active_users.pop(cuser.get_id())
        return redirect("/")
    else:
        return redirect("/")


@app.route("/profile")
async def profile():
    if not current_user.is_authenticated: # User is not logged in, send to login page
        return redirect(
            "https://auth-dev.vatsim.net/oauth/authorize?client_id=383&redirect_uri=https%3A%2F%2Fczvr-bot.xyz%2Fcallback%2Fvatsim&response_type=code&scope=full_name+vatsim_details")
    return render_template("profile.html", name=current_user.name, )


@app.route("/callback/vatsim")
async def login():
    try:
        code = request.args.get("code")
        if code is None: # User did not authorize, or something went wrong
            return abort(Response("VATSIM authentication was aborted", 400))
        rqst = {
            "code": code,
            "client_id": app_config["VATSIM_CLIENT_ID"],
            "client_secret": app_config["VATSIM_CLIENT_SECRET"],
            "grant_type": "authorization_code",
            "redirect_uri": "https://czvr-bot.xyz/callback/vatsim"
        }
        resp = post("https://auth-dev.vatsim.net/oauth/token", data=rqst)
        token = resp.json().get("access_token")
        if token is None: # Endpoint returned an error or something went wrong
            return abort(Response("VATSIM Token endpoint returned a malformed response", 400))
        headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json"
        }
        data = get("https://auth-dev.vatsim.net/api/user", headers=headers)
        jsdata = data.json()
        if jsdata.get("data") is None: # Endpoint returned an error or something went wrong
            return abort(Response("VATSIM API returned a malformed response", 400))
        cid = int(jsdata["data"]["cid"])
        rating = jsdata["data"]["vatsim"]["rating"]["id"]
        personal = jsdata["data"].get("personal")
        if personal is None: # User did not authorize access to personal data
            name = cid
        else:
            name = personal["name_first"]
        cursor = database.cursor(buffered=True)
        cursor.execute(f"SELECT * FROM {app_config['DATABASE_TABLE']} WHERE cid = %s", (cid,))
        if cursor.rowcount == 0:
            pass
        else:
            sock.emit("UPDATE USER", {"cid": cid, "rating": rating})
        cursor.close()
        ncursor = database.cursor()
        ncursor.execute(
            f"INSERT INTO {app_config['DATABASE_TABLE']} VALUES ({cid}, NULL, {rating}, NULL) ON DUPLICATE KEY UPDATE rating = {rating}"
        )
        ncursor.close()
        database.commit()
        user = ActiveUser(cid, rating, name)
        active_users[cid] = user
        login_user(user, True)
    except Exception as e:
        return str(e)
    return redirect("https://czvr-bot.xyz/")


if __name__ == "__main__":
    app.run("0.0.0.0", 443, ssl_context=context)

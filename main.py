from utils.configreader import config
from requests import post
from mysql.connector import connect
from flask import request, redirect, Flask, render_template, Response, abort
from flask_login import current_user, login_user, logout_user, UserMixin, AnonymousUserMixin, LoginManager


class ActiveUser(UserMixin):
    def __init__(self, cid: int, rating: int, name:str = None):
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


app_config = config()
app = Flask(__name__)
app.secret_key = app_config["FLASK_CLIENT_SECRET"]
manager = LoginManager()
manager.anonymous_user = AnonymousUser
manager.init_app(app)
active_users = {}
database = connect(
    host="localhost",
    user=app_config["DATABASE_USER"],
    password=app_config["DATABASE_PASSWORD"],
    database="czvr"
)


@manager.user_loader
def load_user(user_id: int):
    return active_users.get(user_id)


@app.route("/")
def index():
    if current_user.is_authenticated is False:
        return render_template("index.html", welcome="")
    else:
        return render_template("index.html", welcome=f"Welcome, {current_user.name}")


@app.route("/callback/vatsim")
def login():
    try:
        code = request.args.get("code")
        if code is None:
            return abort(Response("VATSIM authentication was aborted", 400))
        rqst = {
            "code": code,
            "client_id": app_config["VATSIM_CLIENT_ID"],
            "client_secret": app_config["VATSIM_CLIENT_ID"],
            "grant_type": "authorization_code",
            "redirect_uri": "http://czvr-bot.xyz:5000/callback/vatsim"
        }
        resp = post("https://auth-dev.vatsim.net/oauth/token", data=rqst)
        token = resp.json().get("access_token")
        if token is None:
            return abort(Response("VATSIM Token endpoint returned a malformed response", 400))
        headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json"
        }
        data = post("https://auth-dev.vatsim.net/api/user", headers=headers)
        jsdata = data.json()
        if jsdata.get("data") is None:
            return abort(Response("VATSIM API returned a malformed response", 400))
        cid = jsdata["data"]["cid"]
        rating = jsdata["data"]["vatsim"]["rating"]["id"]
        personal = jsdata["data"].get("personal")
        if personal is None:
            name = cid
        else:
            name = personal["name_first"]
        cursor = database.cursor()
        cursor.execute(
            f"INSERT INTO {app_config['DATABASE_TABLE']} VALUES ({cid}, NULL, {rating}) ON DUPLICATE KEY UPDATE rating = {rating}"
        )
        cursor.close()
        database.commit()
        user = ActiveUser(cid, rating, name)
        active_users[cid] = user
        login_user(user, True)
    except Exception as e:
        pass
    return redirect("localhost:5000/")


if __name__ == "__main__":
    app.run("0.0.0.0", 5000)
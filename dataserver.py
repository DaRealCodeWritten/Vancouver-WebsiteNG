import mysql.connector
from flask import Flask, Response, request, session
from flask_login import LoginManager, UserMixin, login_required
from utils.configreader import config
from string import Template


class APIUser(UserMixin):
    def __init__(self, key: str):
        self.key = key

    def get_id(self):
        return self.key


conf = config()
app = Flask(__name__)
app.secret_key = conf["DATABASE_CLIENT_SECRET"]
app_login = LoginManager()
app_login.init_app(app)
db = mysql.connector.connect(
    user=conf["DATABASE_USER"],
    host="host.docker.internal",
    password=conf["DATABASE_PASSWORD"],
    database="czvr"
)


@app_login.request_loader
async def loader(rqst):
    token = rqst.headers.get("Authentication")
    if token is None:
        return None
    else:
        temp = Template("$token")
        token = temp.safe_substitute({
            "token": token
        })
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT * FROM apikeys WHERE keystring = %s", (token,))
        if cursor.rowcount == 0:  # API key doesnt exist
            return None
        elif cursor.rowcount == 1:
            usages = list(cursor)[0][1]
            new = usages + 1
            ncurs = db.cursor()
            ncurs.execute("UPDATE apikeys SET usages = %s WHERE keystring = %s", (new, token))
            ncurs.close()
            db.commit()
            return APIUser(token)
        elif cursor.rowcount > 1:  # Somehow, a key collision has occurred
            return None


@login_required
@app.route("/execute", methods=["GET", "POST", "PUT", "DELETE"])
async def execute():
    user = await loader(request)
    if not isinstance(user, APIUser):
        construc = {
            "message": "Unauthorized"
        }
        return construc, 401

    async def get(rqst):
        temp = Template("SELECT $columns FROM $table")
        cols = rqst.headers.get("columns")
        table = rqst.headers.get("table")
        if any([var is None for var in [cols, table]]):
            return {"message": "Missing headers"}, 400
        construct = temp.safe_substitute(
            {
                "columns": cols,
                "table": table
            }
        )
        cursor = db.cursor(buffered=True)
        try:
            cursor.execute(construct)
            cursor.close()
        except mysql.connector.ProgrammingError as e:
            resp = {
                "error": e,
                "message": "An error occurred"
            }
            return resp, 400
        else:
            const = {
                "result": list(cursor),
                "message": "Successfully Executed"
            }
            return const, 200

    async def post(rqst):
        temp = Template("INSERT INTO $table VALUES ($values)")
        values = rqst.headers.get("values")
        table = rqst.headers.get("table")
        if any([var is None for var in [values, table]]):
            return {"message": "Missing headers"}, 400
        construct = temp.substitute(
            {
                "values": values,
                "table": table
            }
        )
        cursor = db.cursor()
        try:
            cursor.execute(construct)
            cursor.close()
            db.commit()
        except mysql.connector.ProgrammingError as e:
            resp = {
                "error": e,
                "message": "An error occurred"
            }
            return resp, 400
        else:
            const = {
                "message": "Successfully Executed"
            }
            return const, 201

    async def put(rqst):
        temp = Template("UPDATE $table SET $column = $value WHERE $where = $wherevar")
        where = rqst.headers.get("where")
        table = rqst.headers.get("table")
        value = rqst.headers.get("value")
        column = rqst.headers.get("column")
        wherevar = rqst.headers.get("wherevar")
        if any([var is None for var in [value, table, where, wherevar, column]]):
            return {"message": "Missing headers"}, 400
        construct = temp.substitute(
            {
                "where": where,
                "table": table,
                "column": column,
                "value": value,
                "wherevar": wherevar
            }
        )
        cursor = db.cursor()
        try:
            cursor.execute(construct)
            cursor.close()
            db.commit()
        except mysql.connector.ProgrammingError as e:
            resp = {
                "error": str(e),
                "debug": construct,
                "message": "An error occurred"
            }
            return resp, 400
        else:
            const = {
                "message": "Successfully Executed"
            }
            return const, 200

    async def delete(rqst):
        temp = Template("DELETE FROM $table WHERE $where = $value")
        values = rqst.headers.get("values")
        table = rqst.headers.get("table")
        where = rqst.headers.get("where")
        if any([var is None for var in [values, table, where]]):
            return {"message": "Missing headers"}, 400
        construct = temp.substitute(
            {
                "value": values,
                "table": table,
                "where": where
            }
        )
        cursor = db.cursor()
        try:
            cursor.execute(construct)
            cursor.close()
            db.commit()
        except mysql.connector.ProgrammingError as e:
            resp = {
                "error": str(e),
                "message": "An error occurred"
            }
            return resp, 400
        else:
            const = {
                "message": "Successfully Deleted"
            }
            return const, 204

    method = request.method
    cases = {
        "GET": get,
        "POST": post,
        "PUT": put,
        "DELETE": delete
    }
    func = cases.get(method)
    if func is None:
        data = {
            "message": "Unknown method"
        }
        return data, 404
    else:
        data, code = await func(request)
        return data, code


if __name__ == "__main__":
    app.run("0.0.0.0", 8080)

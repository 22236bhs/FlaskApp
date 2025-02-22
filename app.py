from flask import Flask, render_template
import sqlite3
app = Flask(__name__)

DATABASE = "database.db"

def ExeQuery(query, params=()):
    with sqlite3.connect(DATABASE) as db:
        return db.cursor().execute(query, params).fetchall()

@app.route("/")
def home():
    return render_template("main.html", string="hello dlrow")


@app.route("/crazy")
def crazy():
    return render_template("main.html", string="crazy")


@app.route("/<int:id>")
def num(id):
    return render_template("main.html", string="hello dlrow" * id)


@app.route("/<string:strin>")
def printstring(strin):
    return render_template("main.html", string=strin)


@app.route("/<string:string>/<int:id>")
def repeatstring(string, id):
    return render_template("main.html", string=string * id)


if __name__ == "__main__":
    app.run(debug=True)
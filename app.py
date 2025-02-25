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
    return render_template("main.html", string="this is crazy")


@app.route("/<int:id>")
def num(id):
    return render_template("main.html", string=" ".join(["hello dlrow" for _ in range(id)]))


@app.route("/<string:strin>")
def printstring(strin):
    return render_template("main.html", string=strin)


@app.route("/<string:string>/<int:id>")
def repeatstring(string, id):
    return render_template("main.html", string=" ".join([string for _ in range(id)]))



@app.route("/lethal")
def lethal():
    return render_template("lethal.html", params=ExeQuery("SELECT name, description, danger_rating, id FROM lethal_company ORDER BY danger_rating DESC;"))


@app.route("/lethal/<int:id>")
def enemy(id):
    return render_template("lethal_enemy.html", params=ExeQuery("SELECT name, description, danger_rating FROM lethal_company WHERE id = ?", (str(id)))[0])


if __name__ == "__main__":
    app.run(debug=True)
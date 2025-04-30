from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DATABASE = "LCdb.db"

@app.route("/") #Home page for selection
def home():
    return render_template("test.html", page="home")


@app.route("/entity")
def entities():
    return render_template("test.html", page="entities")


@app.route("/entity/<int:id>")
def entity(id):
    return render_template("test.html", page="entity")


@app.route("/moons")
def moons():
    return render_template("test.html", page="moons")


@app.route("/moons/<int:id>")
def moon(id):
    return render_template("test.html", page="moon")


@app.route("/tools")
def tools():
    return render_template("test.html", page="tools")


@app.route("/tools/<int:id>")
def tool(id):
    return render_template("test.html", page="tool")


@app.route("/weathers")
def weathers():
    return render_template("test.html", page="weathers")


@app.route("/weathers/<int:id>")
def weather(id):
    return render_template("test.html", page="weather")


@app.route("/interiors")
def interiors():
    return render_template("test.html", page="interiors")


@app.route("/interiors/<int:id>")
def interior(id):
    return render_template("test.html", page="interior")


if __name__ == "__main__":
    app.run(debug=True)
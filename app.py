from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DATABASE = "LCdb.db"

@app.route("/") #Home page for selection
def home():
    return render_template("main.html")


@app.route("/entity") #Entity list
def entities():
    return render_template("entitylist.html")


@app.route("/entity/<int:id>") #Entity data page
def entity(id):
    return render_template("entity.html")


@app.route("/moons") #Moon list
def moons():
    return render_template("moonlist.html")


@app.route("/moons/<int:id>") #Moon data page
def moon(id):
    return render_template("moon.html")


@app.route("/tools") #Tool list
def tools():
    return render_template("toollist.html")


@app.route("/tools/<int:id>") #Tool data page
def tool(id):
    return render_template("tool.html")


@app.route("/weathers") #Weather list
def weathers():
    return render_template("weatherlist.html")


@app.route("/weathers/<int:id>") #Weather data page
def weather(id):
    return render_template("weather.html")


@app.route("/interiors") #Interior list
def interiors():
    return render_template("interiorlist.html")


@app.route("/interiors/<int:id>") #Interior data page
def interior(id):
    return render_template("interior.html")


if __name__ == "__main__":
    app.run(debug=True)
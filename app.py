from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DATABASE = "LCdb.db"

@app.route("/") #Home page for selection
def home():
    params = [("Moons", "The moons the autopilot can route to.", "moons"),
              ("Tools", "The items and upgrades you can buy or find.", "tools"),
              ("Entites", "The entities you may encounter.", "entity"),
              ("Weathers", "The weathers a moon can have.", "weathers"),
              ("Interiors", "The interiors a moon's facility may have.", "interiors")]
    return render_template("main.html", params=params, title="Home")


@app.route("/entity") #Entity list
def entities():
    return render_template("entitylist.html", title="Entity List")


@app.route("/entity/<int:id>") #Entity data page
def entity(id):
    return render_template("entity.html", title="")


@app.route("/moons") #Moon list
def moons():
    return render_template("moonlist.html", title="Moon List")


@app.route("/moons/<int:id>") #Moon data page
def moon(id):
    return render_template("moon.html", title="")


@app.route("/tools") #Tool list
def tools():
    return render_template("toollist.html", title="Tool List")


@app.route("/tools/<int:id>") #Tool data page
def tool(id):
    return render_template("tool.html", title="")


@app.route("/weathers") #Weather list
def weathers():
    return render_template("weatherlist.html", title="Weather List")


@app.route("/weathers/<int:id>") #Weather data page
def weather(id):
    return render_template("weather.html", title="")


@app.route("/interiors") #Interior list
def interiors():
    return render_template("interiorlist.html", title="Interior List")


@app.route("/interiors/<int:id>") #Interior data page
def interior(id):
    return render_template("interior.html", title="")


if __name__ == "__main__":
    app.run(debug=True)
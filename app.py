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
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute("SELECT id, name, setting FROM Entities;").fetchall()
    
    params = []
    for a in range(3):
        params.append([{
            "id": data[i][0],
            "name": data[i][1],
            "setting": data[i][2]
        } for i in range(len(data)) if data[i][2] == a + 1])

    return render_template("entitylist.html", params=params, title="Entity List")


@app.route("/entity/<int:id>") #Entity data page
def entity(id):
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute('''
                                   SELECT Entities.name, danger, bestiary, Setting.name, Moons.name, sp_hp, mp_hp, power, max_spawned, Entities.description, Entities.pictures
                                   FROM Entities
                                   JOIN Moons ON Entities.fav_moon = Moons.id
                                   JOIN Setting ON Entities.setting = Setting.id
                                   WHERE Entities.id = ?;''', (id,)).fetchall()[0]
    params = {
        "name": data[0],
        "danger": data[1],
        "bestiary": data[2],
        "setting": data[3],
        "fav_moon": data[4],
        "sp_hp": data[5],
        "mp_hp": data[6],
        "power": data[7],
        "max_spawned": data[8],
        "description": data[9],
        "pictures": data[10]
    }
    return render_template("entity.html", params=params, title=params["name"])


@app.route("/moons") #Moon list
def moons():
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute('''
                                   SELECT id, name, price, tier
                                   FROM Moons;''').fetchall()
    params = []
    for a in range(3):
        params.append([{
            "id": data[i][0],
            "name": data[i][1],
            "price": data[i][2],
            "tier": data[i][3]
        } for i in range(len(data)) if data[i][3] == a + 1])
    
    return render_template("moonlist.html", params=params, title="Moon List")


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
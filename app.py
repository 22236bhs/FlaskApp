from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DATABASE = "LCdb.db"

#▮

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
        data = db.cursor().execute('''
                                   SELECT id, name, setting 
                                   FROM Entities;''').fetchall()
    
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
    for a in range(4):
        params.append([{
            "id": data[i][0],
            "name": data[i][1],
            "price": data[i][2]
        } for i in range(len(data)) if data[i][3] == a + 1])
    
    return render_template("moonlist.html", params=params, title="Moon List")


@app.route("/moons/<int:id>") #Moon data page
def moon(id):
    with sqlite3.connect(DATABASE) as db:
        cur = db.cursor()
        data = cur.execute('''
                                   SELECT Moons.name, RiskLevels.name, price, Interiors.id, Interiors.name, max_indoor_power, max_outdoor_power, conditions, history, fauna, Moons.description, tier, Moons.pictures
                                   FROM Moons
                                   JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                                   JOIN Interiors ON Moons.interior = Interiors.id
                                   WHERE Moons.id = ?;''', (id,)).fetchall()[0]
        weatherdata = cur.execute('''
                                  SELECT id, name FROM Weathers WHERE id IN (
                                  SELECT weather_id FROM MoonWeathers WHERE moon_id = ?);''', (id,)).fetchall()
        
    params = {
        "name": data[0],
        "risk_level": data[1],
        "price": data[2],
        "interior": {"id": data[3], "name": data[4]},
        "max_indoor_power": data[5],
        "max_outdoor_power": data[6],
        "conditions": data[7],
        "history": data[8],
        "fauna": data[9],
        "description": data[10],
        "tier": data[11],
        "pictures": data[12],
        "weathers": weatherdata
    }
    return render_template("moon.html", params=params, title=params["name"])


@app.route("/tools") #Tool list
def tools():
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute('''
                                   SELECT id, name, upgrade
                                   FROM Tools;''').fetchall()
    params = []
    for a in range(2):
        params.append([{
            "id": data[i][0],
            "name": data[i][1]
        } for i in range(len(data)) if data[i][2] == a])

    return render_template("toollist.html", params=params, title="Tool List")


@app.route("/tools/<int:id>") #Tool data page
def tool(id):
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute('''
                                   SELECT name, price, description, upgrade, weight, pictures
                                   FROM Tools
                                   WHERE id = ?;
                                   ''', (id,)).fetchall()[0]
    params = {
        "name": data[0],
        "price": data[1],
        "description": data[2],
        "upgrade": data[3],
        "weight": data[4],
        "pictures": data[5]
    }
        
    return render_template("tool.html", params=params, title=params["name"])


@app.route("/weathers") #Weather list
def weathers():
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute('''
                                   SELECT id, name
                                   FROM Weathers;''').fetchall()
    params = [{
        "id": data[i][0],
        "name": data[i][1]
    } for i in range(len(data))]

    return render_template("weatherlist.html", params=params, title="Weather List")


@app.route("/weathers/<int:id>") #Weather data page
def weather(id):
    with sqlite3.connect(DATABASE) as db:
        cur = db.cursor()
        data = cur.execute('''
                           SELECT name, description, pictures
                           FROM Weathers
                           WHERE id = ?;''', (id,)).fetchall()[0]
        moondata = cur.execute('''
                               SELECT id, name FROM Moons WHERE id IN (
                               SELECT moon_id FROM MoonWeathers WHERE weather_id = ?);''', (id,)).fetchall()
    
    params = {
        "name": data[0],
        "moons": moondata,
        "description": data[1],
        "pictures": data[2]
    }
    return render_template("weather.html", params=params, title=params["name"])


@app.route("/interiors") #Interior list
def interiors():
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute('''
                                   SELECT id, name
                                   FROM Interiors;''').fetchall()
    params = [{
        "id": data[i][0],
        "name": data[i][1]
    } for i in range(len(data)) if data[i][1] != "N/A"]
    return render_template("interiorlist.html", params=params, title="Interior List")


@app.route("/interiors/<int:id>") #Interior data page
def interior(id):
    with sqlite3.connect(DATABASE) as db:
        data = db.cursor().execute('''
                                   SELECT name, description, pictures
                                   FROM Interiors
                                   WHERE id = ?;''', (id,)).fetchall()[0]
    params = {
        "name": data[0],
        "description": data[1],
        "pictures": data[2]
    }

    return render_template("interior.html", params=params, title=params['name'])


if __name__ == "__main__":
    app.run(debug=True)
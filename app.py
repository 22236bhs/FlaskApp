from flask import Flask, render_template
import sqlite3
app = Flask(__name__)

DATABASE = "lethal_database.db"

def ExeQuery(*querys, params=()):
    with sqlite3.connect(DATABASE) as db:
        returnlist = []
        for query in querys:
            returnlist.append(db.cursor().execute(query, params).fetchall())
        if len(returnlist) == 1:
            return returnlist[0]
        else:
            return returnlist   


#def UnTuple(listt):
#   for i in range(len(listt)):
#        listt[i] = listt[i][0]
#   return listt
        


@app.route("/")
def home():
    params = [["Moons", "moons"], ["Bestiary", "enemies"], ["Weathers", "weathers"]]
    return render_template("main.html", params=params, title="Home")


@app.route("/moons")
def moons():
    data = ExeQuery("SELECT id, name, price FROM Moons;")
    params = [
        {
            "id": data[i][0],
            "name": data[i][1],
            "price": data[i][2]
        } for i in range(len(data))
    ]
    return render_template("lethal_moons.html", params=params, title="Moons")


@app.route("/moons/<int:id>")
def moon(id):
    data = ExeQuery(f'''SELECT Moons.name, Moons.price, RiskLevels.name, Interiors.name, Moons.secret, Moons.max_indoor_power, Moons.max_outdoor_power, Moons.conditions, Moons.history, Moons.fauna
                    FROM Moons
                    JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                    JOIN Interiors ON Interiors.id = Moons.interior
                    WHERE Moons.id = {id};''', f'''SELECT id, name FROM Weathers WHERE id in (
                    SELECT weather_id FROM MoonWeathers WHERE moon_id = (
                    SELECT id FROM Moons WHERE id = {id}))''')
    params = {
        "name": data[0][0][0],
        "price": data[0][0][1],
        "risk_level": data[0][0][2],
        "interior": data[0][0][3],
        "weathers": data[1],
        "secret": data[0][0][4],
        "indoor_power": data[0][0][5],
        "outdoor_power": data[0][0][6] ,
        "conditions": data[0][0][7],
        "history": data[0][0][8],
        "fauna": data[0][0][9]
    }
    return render_template("moon.html", params=params, title=params["name"])


@app.route("/enemies")
def enemies():
    data = ExeQuery("SELECT id, name FROM Entities")
    params = [
        {
            "id": data[i][0],
            "name": data[i][1]
        } for i in range(len(data))
    ]
    return render_template("lethal_enemies.html", params=params, title="Entities")


@app.route("/enemies/<int:id>")
def enemy(id):
    data = ExeQuery('''
    SELECT Entities.name, bestiary, danger, sp_hp, mp_hp, power, Moons.name, Setting.name
    FROM Entities 
    JOIN Moons on Entities.fav_moon = Moons.id
    JOIN Setting on Entities.setting = Setting.id
    WHERE Entities.id = ?''', params=(id,))[0]
    params = {
        "name": data[0],
        "description": data[1],
        "danger_rating": data[2],
        "sp_hp": data[3],
        "mp_hp": data[4],
        "power": data[5],
        "fav_moon": data[6],
        "setting": data[7]
    }
    if params["sp_hp"] == -1:
        params["sp_hp"] = "Invincible"
    if params["mp_hp"] == -1:    
        params["mp_hp"] = "Invincible"
    return render_template("enemy.html", params=params, title=params["name"])


@app.route("/weathers")
def weathers():
    data = ExeQuery("SELECT id, name FROM Weathers")
    params = [
        {"id": data[i][0],
         "name": data[i][1]
        } for i in range(len(data))
    ]
    return render_template("lethal_weathers.html", params=params, title="Weathers")


@app.route("/weathers/<int:id>")
def weather(id):
    data = ExeQuery(f'''SELECT name, description FROM Weathers
                    WHERE id = {id}''', f'''SELECT id, name FROM Moons WHERE id IN (
                    SELECT moon_id FROM MoonWeathers WHERE weather_id = (
                    SELECT id FROM Weathers WHERE id = {id}))''')
    params = {
        "name": data[0][0][0],
        "description": data[0][0][1],
        "moons": data[1]
    }
    print(params)
    return render_template("weather.html", params=params, title=params["name"], )


if __name__ == "__main__":
    app.run(debug=True)
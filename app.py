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


def UnTuple(listt):
    print(listt)
    for i in range(len(listt)):
        listt[i] = listt[i][0]
    return listt
        


@app.route("/")
def home():
    params = [["Moons", "moons"], ["Entities", "enemies"]]
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
    data = ExeQuery(f'''SELECT Moons.name, Moons.price, RiskLevels.name, Interiors.name
                    FROM Moons
                    JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                    JOIN Interiors ON Interiors.id = Moons.interior
                    WHERE Moons.id = {id};''', f'''SELECT name FROM Weathers WHERE id in (
                    SELECT weather_id FROM MoonWeathers WHERE moon_id = (
                    SELECT id FROM Moons WHERE id = {id}))''')
    print(data)
    params = {
        "name": data[0][0][0],
        "price": data[0][0][1],
        "risk_level": data[0][0][2],
        "interior": data[0][0][3],
        "weathers": UnTuple(data[1])
    }
    if len(params["weathers"]) == 0:
        params["weathers"].append("N/A")
    return render_template("moon.html", params=params, title=params["name"])


@app.route("/enemies")
def enemies():
    data = ExeQuery("SELECT id, name FROM Creatures")
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
    SELECT Creatures.name, bestiary, danger, sp_hp, mp_hp, power, Moons.name, Setting.name
    FROM Creatures 
    JOIN Moons on Creatures.fav_moon = Moons.id
    JOIN Setting on Creatures.setting = Setting.id
    WHERE Creatures.id = ?''', params=(id,))[0]
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


if __name__ == "__main__":
    app.run(debug=True)
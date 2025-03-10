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


@app.route("/")
def home():
    params = [["Moons", "moons"], ["Creatures", "enemies"]]
    return render_template("main.html", params=params, title="Home")


@app.route("/moons")
def moons():
    data = ExeQuery("SELECT id, name, price FROM Moons ")
    params = [
        {
            "id": data[i][0],
            "name": data[i][1],
            "price": data[i][2]
        } for i in range(len(data))
    ]
    print(params)
    return render_template("lethal_moons.html", params=params, title="Moons")


@app.route("/moons/<int:id>")
def moon(id):
    data = ExeQuery('''SELECT Moons.name, Moons.price, RiskLevels.name 
                    FROM Moons
                    JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                    WHERE Moons.id = ?;''', params=(id,))[0]
    params = {
        "name": data[0],
        "price": data[1],
        "risk_level": data[2]
    }
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
    return render_template("lethal_enemies.html", params=params, title="Creatures")


@app.route("/enemies/<int:id>")
def enemy(id):
    data = ExeQuery("SELECT name, description, danger_rating FROM Creatures WHERE id = ?", params=(id,))[0]
    params = {
        "name": data[0],
        "description": data[1],
        "danger_rating": data[2]
    }
    return render_template("enemy.html", params=params, title=params["name"])


if __name__ == "__main__":
    app.run(debug=True)
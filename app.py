from flask import Flask, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
DATABASE = "LCdb.db"
USERNAME_MAX_LENGTH = 16
PASSWORD_MAX_LENGTH = 20

admin = False
login_message = ""

def execute_query(query, params=()):
    with sqlite3.connect(DATABASE) as db:
        return db.cursor().execute(query, params).fetchall()


def set_picture_list(picture_string):
    if picture_string:
        return picture_string.split(" ")
    else:
        return []
    

def admin_perms_denied():
    return render_template("adminpermsdenied.html")


@app.route("/") #Home page for selection
def home():
    params = [("Moons", "The moons the autopilot can route to.", "moons"),
              ("Tools", "The items and upgrades you can buy or find.", "tools"),
              ("Entities", "The entities you may encounter.", "entity"),
              ("Weathers", "The weathers a moon can have.", "weathers"),
              ("Interiors", "The interiors a moon's facility may have.", "interiors")]
    return render_template("main.html", params=params, title="Home", admin=admin)


@app.route("/entity", methods=['GET', 'POST']) #Entity list
def entities():
    sort_queries = {
        "0": ("Alphabetical", "ORDER BY name"),
        "1": ("Danger", "ORDER BY danger")
    }
    sortdir = request.form.get("sortdir")
    if not sortdir:
        sortdir = ""
    sort = request.form.get("sort")
    if sort:
        order = sort_queries[sort][1]
    else:
        order = sort_queries["0"][1]
    data = execute_query('''
                            SELECT id, name, setting
                            FROM Entities''' + " " + order + " " + sortdir + ";")
    
    params = []
    for a in range(3):
        params.append([{
            "id": data[i][0],
            "name": data[i][1],
            "setting": data[i][2]
        } for i in range(len(data)) if data[i][2] == a + 1])

    return render_template("entities/entitylist.html", params=params, title="Entity List", sort=sort_queries, admin=admin)


@app.route("/entity/<int:id>") #Entity data page
def entity(id):
    data = execute_query('''
                        SELECT Entities.name, danger, bestiary, Setting.name, Moons.name, sp_hp, mp_hp, power, max_spawned, Entities.description, Entities.pictures
                        FROM Entities
                        JOIN Moons ON Entities.fav_moon = Moons.id
                        JOIN Setting ON Entities.setting = Setting.id
                        WHERE Entities.id = ?;''', (id,))[0]
    
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
        "pictures": set_picture_list(data[10])
    }
    params["bestiary"] = params["bestiary"].replace("\\n", "\n")
    params["description"] = params["description"].replace("\\n", "\n")
    return render_template("entities/entity.html", params=params, title=params["name"])


@app.route("/moons") #Moon list
def moons():
    data = execute_query('''
                        SELECT id, name, price, tier
                        FROM Moons;''')
    params = []
    for a in range(5):
        params.append([{
            "id": data[i][0],
            "name": data[i][1],
            "price": data[i][2]
        } for i in range(len(data)) if data[i][3] == a + 1])
    
    return render_template("moons/moonlist.html", params=params, title="Moon List", admin=admin)


@app.route("/moons/<int:id>") #Moon data page
def moon(id):
    data = execute_query('''
                        SELECT Moons.name, RiskLevels.name, price, Interiors.id, Interiors.name, max_indoor_power, max_outdoor_power, conditions, history, fauna, Moons.description, tier, Moons.pictures
                        FROM Moons
                        JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                        JOIN Interiors ON Moons.interior = Interiors.id
                        WHERE Moons.id = ?;''', (id,))[0]
    
    weatherdata = execute_query('''
                                SELECT id, name FROM Weathers WHERE id IN (
                                SELECT weather_id FROM MoonWeathers WHERE moon_id = ?);''', (id,))
    
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
        "pictures": set_picture_list(data[12]),
        "weathers": weatherdata
    }
    if params["conditions"]:
        params["conditions"] = params["conditions"].replace("\\n", "\n")
    if params["history"]:
        params["history"] = params["history"].replace("\\n", "\n")
    if params["fauna"]:
        params["fauna"] = params["fauna"].replace("\\n", "\n")
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("moons/moon.html", params=params, title=params["name"])


@app.route("/tools", methods=['GET', 'POST']) #Tool list
def tools():
    sort_queries = {
        "0": ("Default", ""),
        "1": ("Alphabetical", "ORDER BY name"),
        "2": ("Price", "ORDER BY price"),
    }
    sort_dir = request.form.get("sortdir")
    if not sort_dir:
        sort_dir = ""
    sort = request.form.get("sort")
    if sort:
        order = sort_queries[sort][1]
    else:
        order = sort_queries["0"][1]
    
    data = execute_query('''
                        SELECT id, name, upgrade, price
                        FROM Tools''' + " " + order + " " + sort_dir + ";")
        
    params = []
    for a in range(2):
        params.append([{
            "id": data[i][0],
            "name": data[i][1],
            "price": data[i][3]
        } for i in range(len(data)) if data[i][2] == a])

    return render_template("tools/toollist.html", params=params, title="Tool List", sort=sort_queries)


@app.route("/tools/<int:id>") #Tool data page
def tool(id):
    data = execute_query('''
                        SELECT name, price, description, upgrade, weight, pictures
                        FROM Tools
                        WHERE id = ?;''', (id,))[0]

    params = {
        "name": data[0],
        "price": data[1],
        "description": data[2],
        "upgrade": data[3],
        "weight": data[4],
        "pictures": set_picture_list(data[5])
    }
    
    return render_template("tools/tool.html", params=params, title=params["name"])


@app.route("/weathers") #Weather list
def weathers():
    data = execute_query('''
                        SELECT id, name
                        FROM Weathers;''')
    
    params = [{
        "id": data[i][0],
        "name": data[i][1]
    } for i in range(len(data))]

    return render_template("weathers/weatherlist.html", params=params, title="Weather List")


@app.route("/weathers/<int:id>") #Weather data page
def weather(id):
    data = execute_query('''
                        SELECT name, description, pictures
                        FROM Weathers
                        WHERE id = ?;''', (id,))[0]
    
    moondata = execute_query('''
                            SELECT id, name FROM Moons WHERE id IN (
                            SELECT moon_id FROM MoonWeathers WHERE weather_id = ?);''', (id,))
    
    params = {
        "name": data[0],
        "moons": moondata,
        "description": data[1],
        "pictures": set_picture_list(data[2])
    }
    return render_template("weathers/weather.html", params=params, title=params["name"])


@app.route("/interiors") #Interior list
def interiors():
    data = execute_query('''
                        SELECT id, name
                        FROM Interiors;''')

    params = [{
        "id": data[i][0],
        "name": data[i][1]
    } for i in range(len(data)) if data[i][1] != "N/A"]

    return render_template("interiors/interiorlist.html", params=params, title="Interior List")


@app.route("/interiors/<int:id>") #Interior data page
def interior(id):
    data = execute_query('''
                        SELECT name, description, pictures
                        FROM Interiors
                        WHERE id = ?;''', (id,))[0]

    params = {
        "name": data[0],
        "description": data[1],
        "pictures": set_picture_list(data[2])
    }

    return render_template("interiors/interior.html", params=params, title=params['name'])


@app.route("/login")
def login():
    global login_message
    current_login_message = login_message
    login_message = ""
    return render_template("login.html", login_message=current_login_message, admin=admin)


@app.route("/loginregister", methods=['GET', 'POST'])
def loginregister():
    global login_message, admin
    success = False
    userid = 0
    username = request.form.get("username")
    password = request.form.get("password")
    userdata = execute_query("SELECT id, username FROM AdminLogins")
    for user in userdata:
        if username == user[1]:
            
            success = True
            userid = user[0]
            break
    if success:
        success = False
        if check_password_hash(execute_query("SELECT passwordhash FROM AdminLogins WHERE id=?", (userid,))[0][0], password):
            admin = True
            login_message = "Login Successful"
            success = True

    if not success:
        login_message = "Invalid Username or Password"
    return app.redirect("/login")


@app.route("/logout")
def logout():
    global admin
    admin = False
    return app.redirect("/")
    

@app.route("/admin/moons/add")
def add_moon_page():
    if admin:
        risk_level_entries = execute_query("SELECT id, name FROM RiskLevels;")
        interior_entries = execute_query("SELECT id, name FROM Interiors;")
        weather_entries = execute_query("SELECT id, name FROM Weathers;")
        return render_template("moons/moonadminadd.html", risk_levels=risk_level_entries, interiors=interior_entries, weathers=weather_entries)
    else:
        return admin_perms_denied()
    

@app.route("/admin/addmoon", methods=['GET', 'POST'])
def add_moon():
    if admin:
        name = request.form.get("name")
        risk_level = request.form.get("risk_level")
        price = request.form.get("price")
        moon_interior = request.form.get("interior")
        max_indoor_power = request.form.get("max_indoor_power")
        max_outdoor_power = request.form.get("max_outdoor_power")
        conditions = request.form.get("conditions")
        history = request.form.get("history")
        fauna = request.form.get("fauna")
        description = request.form.get("description")
        tier = request.form.get("tier")
        conditions = conditions.replace("\n", "\\n")
        history = history.replace("\n", "\\n")
        fauna = fauna.replace("\n", "\\n")
        description = description.replace("\n", "\\n")

        weather_entries = execute_query("SELECT id FROM Weathers;")
        weather_list = []
        for i in range(len(weather_entries)):
            if request.form.get("weather" + str(weather_entries[i][0])):
                weather_list.append(weather_entries[i][0])
        
        
        execute_query(
            '''
            INSERT INTO Moons (name, risk_level, price, interior, max_indoor_power, max_outdoor_power, conditions, history, fauna, description, tier, pictures)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, risk_level, price, moon_interior, max_indoor_power, max_outdoor_power, conditions, history, fauna, description, tier, "placeholder_image")
        )
        moon_id = len(execute_query("SELECT id FROM Moons;"))
        for i in weather_list:
            execute_query("INSERT INTO MoonWeathers (moon_id, weather_id) VALUES (?, ?)", (moon_id, i))
        return app.redirect("/moons")
    else:
        return admin_perms_denied()


@app.route("/admin/moons/delete")
def delete_moon_page():
    if admin:
        moon_list = execute_query("SELECT id, name FROM Moons")
        return render_template("moons/moonadmindelete.html", moons=moon_list)
    else:
        return admin_perms_denied()


@app.route("/admin/deletemoon/<int:id>")
def delete_moon(id):
    if admin:
        execute_query("DELETE FROM Moons WHERE id=?;", (id,))
        execute_query("DELETE FROM MoonWeathers WHERE moon_id=?", (id,))
        return app.redirect("/moons")
    else:
        return admin_perms_denied()


@app.route("/admin/entity/add")
def add_entity_page():
    if admin:
        setting_entries = execute_query("SELECT id, name FROM Setting;")
        moon_entries = execute_query("SELECT id, name FROM Moons;")
        return render_template("entities/entityadminadd.html", settings=setting_entries, moons=moon_entries)
    else:
        return admin_perms_denied()


@app.route("/admin/addentity", methods=["GET", "POST"])
def add_entity():
    if admin:
        name = request.form.get("name")
        danger_rating = request.form.get("danger_rating")
        bestiary = request.form.get("bestiary")
        setting = request.form.get("setting")
        fav_moon = request.form.get("fav_moon")
        sp_hp = request.form.get("sp_hp")
        mp_hp = request.form.get("mp_hp")
        invincible = request.form.get("invincible")
        power = request.form.get("power")
        max_spawned = request.form.get("max_spawned")
        description = request.form.get("description")

        if invincible:
            sp_hp = -1
            mp_hp = -1
        
        bestiary = bestiary.replace("\n", "\\n")
        description = description.replace("\n", "\\n")

        execute_query('''
                      INSERT INTO Entities (name, danger, bestiary, setting, fav_moon, sp_hp, mp_hp, power, max_spawned, description, pictures)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (name, danger_rating, bestiary, setting, fav_moon, sp_hp, mp_hp, power, max_spawned, description, "placeholder_image"))
        return app.redirect("/entity")
    else:
        return admin_perms_denied()


@app.route("/admin/entity/delete")
def delete_entity_page():
    if admin:
        entity_list = execute_query("SELECT id, name FROM Entities;")
        return render_template("entities/entityadmindelete.html", entities=entity_list)
    else:
        return admin_perms_denied()


@app.route("/admin/deleteentity/<int:id>")
def delete_entity(id):
    if admin:
        execute_query("DELETE FROM Entities WHERE id=?;", (id,))
        return app.redirect("/entity")
    else:
        return admin_perms_denied()



@app.errorhandler(404)
def error404(e):
    return render_template("error_page.html", error_code=404), 404


@app.errorhandler(400)
def error400(e):
    return render_template("error_page.html", error_code=400), 400

if __name__ == "__main__":
    app.run(debug=True)
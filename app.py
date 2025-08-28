from flask import Flask, render_template, request, abort
from werkzeug.security import check_password_hash
import sqlite3
import app_content

app = Flask(__name__)
DATABASE = "LCdb.db"

admin = False
login_message = ""


def execute_query(query, params=()):
    '''Executes a query in the database based on parameters'''
    with sqlite3.connect(DATABASE) as db:
        return db.cursor().execute(query, params).fetchall()


def set_picture_list(picture_string):
    '''Formats the picture string into list'''
    if picture_string:
        return picture_string.split(" ")
    else:
        return []


def admin_perms_denied():
    '''Redirects the user to a page that denies admin access'''
    return render_template("adminpermsdenied.html")


def get_title(route):
    return execute_query('''
                         SELECT title
                         FROM PageTitles
                         WHERE route=?''', (route,))[0][0]


def push_error(number, code):
    return render_template("error_page.html",
                           error_code=number,
                           title=f"{number} Error",
                           error=code), number


@app.route("/")  # Home page for selection
def home():
    params = execute_query('''
                           SELECT display_name, description, link
                           FROM HomePageLinks;''')

    return render_template("main.html",
                           params=params,
                           title=get_title("/"),
                           admin=admin)


@app.route("/entity", methods=['GET', 'POST'])  # Entity list
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

    return render_template("entities/entitylist.html",
                           params=params,
                           title=get_title("/entity"),
                           sort=sort_queries, admin=admin)


@app.route("/entity/<int:id>")  # Entity data page
def entity(id):
    data = execute_query('''
                        SELECT Entities.name, danger, bestiary, Setting.name,
                        Moons.name, sp_hp, mp_hp, power, max_spawned,
                        Entities.description, Entities.pictures
                        FROM Entities
                        JOIN Moons ON Entities.fav_moon = Moons.id
                        JOIN Setting ON Entities.setting = Setting.id
                        WHERE Entities.id = ?;''', (id,))
    if not data:
        abort(404)

    data = data[0]

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

    if params["bestiary"]:
        params["bestiary"] = params["bestiary"].replace("\\n", "\n")
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("entities/entity.html",
                           params=params,
                           title=params["name"])


@app.route("/moons")  # Moon list
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

    return render_template("moons/moonlist.html",
                           params=params,
                           title=get_title("/moons"),
                           admin=admin)


@app.route("/moons/<int:id>")  # Moon data page
def moon(id):
    data = execute_query('''
                        SELECT Moons.name, RiskLevels.name, price, Interiors.id,
                        Interiors.name, max_indoor_power, max_outdoor_power,
                        conditions, history, fauna, Moons.description, tier, Moons.pictures, Moons.id
                        FROM Moons
                        JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                        JOIN Interiors ON Moons.interior = Interiors.id
                        WHERE Moons.id = ?;''', (id,))

    if not data:
        abort(404)

    data = data[0]

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
        "weathers": weatherdata,
        "id": data[13]
    }

    if params["conditions"]:
        params["conditions"] = params["conditions"].replace("\\n", "\n")
    if params["history"]:
        params["history"] = params["history"].replace("\\n", "\n")
    if params["fauna"]:
        params["fauna"] = params["fauna"].replace("\\n", "\n")
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("moons/moon.html",
                           params=params,
                           title=params["name"])


@app.route("/tools", methods=['GET', 'POST'])  # Tool list
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

    return render_template("tools/toollist.html",
                           params=params,
                           title=get_title("/tools"),
                           sort=sort_queries,
                           admin=admin)


@app.route("/tools/<int:id>")  # Tool data page
def tool(id):
    data = execute_query('''
                        SELECT name, price, description, upgrade, weight, pictures, id
                        FROM Tools
                        WHERE id = ?;''', (id,))

    if not data:
        abort(404)

    data = data[0]

    params = {
        "name": data[0],
        "price": data[1],
        "description": data[2],
        "upgrade": data[3],
        "weight": data[4],
        "pictures": set_picture_list(data[5]),
        "id": data[6]
    }

    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("tools/tool.html",
                           params=params,
                           title=params["name"])


@app.route("/weathers")  # Weather list
def weathers():
    data = execute_query('''
                        SELECT id, name
                        FROM Weathers;''')

    params = [{
        "id": data[i][0],
        "name": data[i][1]
    } for i in range(len(data))]

    return render_template("weathers/weatherlist.html",
                           params=params,
                           title=get_title("/weathers"),
                           admin=admin)


@app.route("/weathers/<int:id>")  # Weather data page
def weather(id):
    data = execute_query('''
                        SELECT name, description, pictures
                        FROM Weathers
                        WHERE id = ?;''', (id,))

    if not data:
        abort(404)

    data = data[0]

    moondata = execute_query('''
                            SELECT id, name FROM Moons WHERE id IN (
                            SELECT moon_id FROM MoonWeathers WHERE weather_id=?);''', (id,))

    params = {
        "name": data[0],
        "moons": moondata,
        "description": data[1],
        "pictures": set_picture_list(data[2])
    }

    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("weathers/weather.html",
                           params=params,
                           title=params["name"])


@app.route("/interiors")  # Interior list
def interiors():
    data = execute_query('''
                        SELECT id, name
                        FROM Interiors;''')

    params = [{
        "id": data[i][0],
        "name": data[i][1]
    } for i in range(len(data)) if data[i][1] != "N/A"]

    return render_template("interiors/interiorlist.html",
                           params=params,
                           title=get_title("/interiors"),
                           admin=admin)


@app.route("/interiors/<int:id>")  # Interior data page
def interior(id):
    data = execute_query('''
                        SELECT name, description, pictures
                        FROM Interiors
                        WHERE id = ?;''', (id,))

    if not data:
        abort(404)

    data = data[0]

    params = {
        "name": data[0],
        "description": data[1],
        "pictures": set_picture_list(data[2])
    }

    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("interiors/interior.html",
                           params=params,
                           title=params['name'])


@app.route("/login")  # Page for the admin login
def login():
    global login_message
    current_login_message = login_message
    login_message = ""
    return render_template("login.html",
                           login_message=current_login_message,
                           admin=admin,
                           username_max_length=app_content.username_max_length,
                           password_max_length=app_content.password_max_length,
                           title=get_title("/login"))


@app.route("/loginregister", methods=['GET', 'POST'])  # Register the inputted username and password
def loginregister():
    global login_message, admin
    success = False
    userid = 0
    username = request.form.get("username")
    password = request.form.get("password")

    if not username:
        login_message = app_content.login_failure_message
        return app.redirect("/login")

    if not password:
        login_message = app_content.login_failure_message
        return app.redirect("/login")

    if len(username) > app_content.username_max_length:
        login_message = app_content.username_too_large_message
        return app.redirect("/login")

    if len(password) > app_content.password_max_length:
        login_message = app_content.password_too_large_message
        return app.redirect("/login")

    userdata = execute_query("SELECT id, username FROM AdminLogins")
    for user in userdata:
        if username == user[1]:

            success = True
            userid = user[0]
            break
    if success:
        success = False
        if check_password_hash(execute_query("SELECT passwordhash FROM AdminLogins WHERE id=?",
                                             (userid,))[0][0], password):
            admin = True
            login_message = app_content.login_success_message
            success = True

    if not success:
        login_message = app_content.login_failure_message
    return app.redirect("/login")


@app.route("/logout")  # Log the user out
def logout():
    global admin
    admin = False
    return app.redirect("/")


@app.route("/admin/moons/add")  # Page to add details for a new moon
def add_moon_page():
    if admin:
        risk_level_entries = execute_query("SELECT id, name FROM RiskLevels;")
        interior_entries = execute_query("SELECT id, name FROM Interiors;")
        weather_entries = execute_query("SELECT id, name FROM Weathers;")
        return render_template("moons/moonadminadd.html",
                               risk_levels=risk_level_entries,
                               interiors=interior_entries,
                               weathers=weather_entries,
                               title=get_title("/admin/moons/add"))
    else:
        return admin_perms_denied()


@app.route("/admin/addmoon", methods=['GET', 'POST'])  # Add moon to database
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
            INSERT INTO Moons (name, risk_level, price, interior, max_indoor_power,
            max_outdoor_power, conditions, history, fauna, description, tier, pictures)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, risk_level, price, moon_interior, max_indoor_power, max_outdoor_power,
             conditions, history, fauna, description, tier, "placeholder_image")
        )
        moon_id = len(execute_query("SELECT id FROM Moons;"))
        for i in weather_list:
            execute_query('''
                          INSERT INTO MoonWeathers (moon_id, weather_id)
                          VALUES (?, ?)''',
                          (moon_id, i))
        return app.redirect("/moons")
    else:
        return admin_perms_denied()


@app.route("/admin/moons/delete")  # Page to select a moon to delete
def delete_moon_page():
    if admin:
        moon_list = execute_query("SELECT id, name FROM Moons")
        return render_template("moons/moonadmindelete.html",
                               moons=moon_list,
                               title=get_title("/admin/moons/delete"))
    else:
        return admin_perms_denied()


@app.route("/admin/deletemoon/<int:id>")  # Delete the selected moon
def delete_moon(id):
    if admin:
        execute_query("DELETE FROM Moons WHERE id=?;", (id,))
        execute_query("DELETE FROM MoonWeathers WHERE moon_id=?", (id,))
        return app.redirect("/moons")
    else:
        return admin_perms_denied()


@app.route("/admin/entity/add")  # Page to add details for a new entity
def add_entity_page():
    if admin:
        setting_entries = execute_query("SELECT id, name FROM Setting;")
        moon_entries = execute_query("SELECT id, name FROM Moons;")
        return render_template("entities/entityadminadd.html",
                               settings=setting_entries,
                               moons=moon_entries,
                               title=get_title("/admin/entity/add"))
    else:
        return admin_perms_denied()


@app.route("/admin/addentity", methods=["GET", "POST"])  # Add entity to database
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
                      INSERT INTO Entities (name, danger, bestiary, setting,
                      fav_moon, sp_hp, mp_hp, power, max_spawned, description, pictures)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (name, danger_rating, bestiary, setting, fav_moon, sp_hp,
                       mp_hp, power, max_spawned, description, "placeholder_image"))
        return app.redirect("/entity")
    else:
        return admin_perms_denied()


@app.route("/admin/entity/delete")  # Page to select an entity to delete
def delete_entity_page():
    if admin:
        entity_list = execute_query("SELECT id, name FROM Entities;")
        return render_template("entities/entityadmindelete.html",
                               entities=entity_list,
                               title=get_title("/admin/entity/delete"))
    else:
        return admin_perms_denied()


@app.route("/admin/deleteentity/<int:id>")  # Delete selected entity
def delete_entity(id):
    if admin:
        execute_query("DELETE FROM Entities WHERE id=?;", (id,))
        return app.redirect("/entity")
    else:
        return admin_perms_denied()


@app.route("/admin/tools/add")  # Page to add details for a new tool
def add_tool_page():
    if admin:
        return render_template("tools/tooladminadd.html",
                               title=get_title("/admin/tools/add"))
    else:
        return admin_perms_denied()


@app.route("/admin/addtool", methods=["GET", "POST"])  # Add tool to database
def add_tool():
    if admin:
        name = request.form.get("name")
        price = request.form.get("price")
        description = request.form.get("description").replace("\n", "\\n")
        upgrade = request.form.get("upgrade")
        weight = request.form.get("weight")

        if upgrade:
            upgrade = 1
        else:
            upgrade = 0

        execute_query('''
                      INSERT INTO Tools
                      (name, price, description, upgrade, weight, pictures)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                      (name, price, description, upgrade, weight, "placeholder_image"))

        return app.redirect("/tools")
    else:
        return admin_perms_denied()


@app.route("/admin/tools/delete")  # Page to select a tool to delete
def delete_tool_page():
    if admin:
        tool_list = execute_query("SELECT id, name FROM Tools;")
        return render_template("tools/tooladmindelete.html",
                               title=get_title("/admin/tools/delete"),
                               tools=tool_list)
    else:
        return admin_perms_denied()


@app.route("/admin/deletetool/<int:id>")  # Delete selected tool
def delete_tool(id):
    if admin:
        execute_query("DELETE FROM Tools WHERE id=?", (id,))
        return app.redirect("/tools")
    else:
        return admin_perms_denied()


@app.route("/admin/weathers/add")  # Page to add details for a new weather
def add_weather_page():
    if admin:
        return render_template("weathers/weatheradminadd.html",
                               title=get_title("/admin/weathers/add"))
    else:
        return admin_perms_denied()


@app.route("/admin/addweather", methods=["GET", "POST"])  # Add weather to database
def add_weather():
    if admin:
        name = request.form.get("name")
        description = request.form.get("description").replace("\n", "\\n")
        execute_query('''
                      INSERT INTO Weathers (name, description, pictures)
                      VALUES (?, ?, ?)''',
                      (name, description, "placeholder_image"))

        return app.redirect("/weathers")
    else:
        return admin_perms_denied()


@app.route("/admin/weathers/delete")  # Page to select a weather to delete
def delete_weather_page():
    if admin:
        weather_list = execute_query("SELECT id, name FROM Weathers;")
        return render_template("weathers/weatheradmindelete.html",
                               title=get_title("/admin/weathers/delete"),
                               weathers=weather_list)
    else:
        return admin_perms_denied()


@app.route("/admin/deleteweather/<int:id>")  # Delete selected weather
def delete_weather(id):
    if admin:
        execute_query("DELETE FROM Weathers WHERE id=?", (id,))
        return app.redirect("/weathers")
    else:
        return admin_perms_denied()


@app.route("/admin/interiors/add")  # Page to add details for a new interior
def add_interior_page():
    if admin:
        return render_template("interiors/interioradminadd.html",
                               title=get_title("/admin/interiors/add"))
    else:
        return admin_perms_denied()


@app.route("/admin/addinterior", methods=["GET", "POST"])  # Add interior to database
def add_interior():
    if admin:
        name = request.form.get("name")
        description = request.form.get("description").replace("\n", "\\n")
        execute_query('''
                      INSERT INTO Interiors (name, description, pictures)
                      VALUES (?, ?, ?)''',
                      (name, description, "placeholder_image"))
        return app.redirect("/interiors")
    else:
        return admin_perms_denied()


@app.route("/admin/interiors/delete")  # Page to select an interior to delete
def delete_interior_page():
    if admin:
        interior_list = execute_query("SELECT id, name FROM Interiors WHERE NOT id=1;")
        return render_template("interiors/interioradmindelete.html",
                               title=get_title("/admin/interiors/delete"),
                               interiors=interior_list)
    else:
        return admin_perms_denied()


@app.route("/admin/deleteinterior/<int:id>")  # Delete selected interior
def delete_interior(id):
    if admin:
        execute_query("DELETE FROM Interiors WHERE id=?", (id,))
        return app.redirect("/interiors")
    else:
        return admin_perms_denied()


@app.errorhandler(404)  # Page for 404 errors
def error404(e):
    return push_error(404, e)


@app.errorhandler(500)  # Page for 500 errors
def error500(e):
    return push_error(500, e)


if __name__ == "__main__":
    app.run(debug=True)

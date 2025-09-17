from flask import Flask, render_template, request, abort
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import code_params
import os

app = Flask(__name__)
DATABASE = "LCdb.db"
app.config["UPLOAD_FOLDER"] = code_params.upload_folder

#  Boolean to hold if the user is signed in as an admin.
admin = False

#  The message when the user attempts to log in.
#  This is a global variable so that multiple routes can access it easily.
login_message = ""

#  The message when the user fails to use an admin tool properly.
#  This is a global variable so that multiple routes can access it easily.
fail_message = ""


def execute_query(query, params=()):
    '''Executes a query in the database based on parameters'''
    with sqlite3.connect(DATABASE) as db:
        return db.cursor().execute(query, params).fetchall()


def set_picture_list(picture_string):
    '''Formats the picture string into list'''
    #  Check if the string can be split before splitting it to prevent errors.
    if picture_string:
        return picture_string.strip().split(" ")
    else:
        return []


def admin_perms_denied():
    '''Redirects the user to a page that denies admin access'''
    return render_template("adminpermsdenied.html",
                           title="Access Denied")


def get_title(route):
    '''Gets the title of a page based on its route'''
    #  Page titles are stored in the database with the page route as the identifier.
    return execute_query('''
                         SELECT title
                         FROM PageTitles
                         WHERE route=?''', (route,))[0][0]


def push_error(number, code):
    '''Redirect the user to the error page with the given code'''
    #  The error page has a modular design by just displaying a given error code.
    return render_template("error_page.html",
                           error_code=number,
                           title=f"{number} Error",
                           error=code), number


def reject_input(route, message):
    '''Redirect the user to a page with a message'''
    #  The user can mess up admin queries in different ways,
    #  so this is here to tell the user what went wrong.
    global fail_message
    fail_message = message
    return app.redirect(route)


def is_number(x):
    '''Check if the given string is able to be converted to a number'''
    #  This function would only be called a few times on a page load,
    #  so the brute force nature of it doesn't hinder the program.
    try:
        int(x)
    except ValueError:
        return False
    else:
        return True


def process_image(name):
    '''Organise file data from an HTML form using the given name'''

    #  Check if the given name has been sent from the HTML form.
    #  This is to prevent inspect element changes from breaking the code.
    if name not in request.files:
        return False

    #  Get the file data and the name of the file.
    file = request.files[name]
    filename = secure_filename(file.filename)
    #  Check that the data is valid.
    if not (file and filename and file.name):
        return False

    return (file, filename)


def get_image_name(name, directory):
    '''Renames the given file name if it already exists in the given directory'''
    #  If two files with the same file name are uploaded, deleting one will delete the other.
    #  To prevent this, this function will ensure that the returned file name will be unqiue.
    #  For example, if image.png exists already, it will be renamed to image(1).png

    #  Check that the name isn't null to prevent errors.
    if name:

        #  Check if the directory isn't null to prevent errors.
        if not directory:
            return name

        #  If the name is already unique, the function will just return the name.
        if name not in directory:
            return name

        #  Save the original file name so that the name parameter can be modified.
        og_name = name

        #  Search for the last instance of a period, which would be before the file type identifier.
        #  This is to make sure that the file type isn't messed up if the name is changed.
        #  Going backwards through the list should be the most efficient way, because the last period is desired.
        for i in range(len(name)):
            if name[-1 - i] == ".":
                index = len(name) - 1 - i
                break

        #  Keep changing the file name until it is unique.
        #  By adding a number in brackets before the file type identifier,
        #  increasing it would yield a unqiue name at some point.
        count = 1
        while name in directory:
            name = f"{og_name[:index]}({count}){og_name[index:]}"
            count += 1
        return name
    else:
        return False


@app.route("/")  # Home page for selection.
def home():
    #  The home page sections are stored in the database,
    #  so it needs to be accessed.
    params = execute_query('''
                           SELECT display_name, description, link
                           FROM HomePageLinks;''')

    return render_template("main.html",
                           params=params,
                           title=get_title("/"),
                           admin=admin)


@app.route("/entity", methods=['GET', 'POST'])  # Entity list.
def entities():
    #  Gather entities.
    data = execute_query('''
                            SELECT id, name, setting
                            FROM Entities
                            ORDER BY name;''')

    #  The entities need to be grouped by their setting,
    #  so the params list will contain a list of each entity for each setting.
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
                           admin=admin)


@app.route("/entity/<int:id>")  # Entity data page.
def entity(id):
    #  Gather entity data.
    data = execute_query('''
                        SELECT Entities.name, danger, bestiary, Setting.name,
                        Moons.name, sp_hp, mp_hp, power, max_spawned,
                        Entities.description, Entities.pictures, Moons.id,
                        Entities.header_picture, Entities.id
                        FROM Entities
                        JOIN Moons ON Entities.fav_moon = Moons.id
                        JOIN Setting ON Entities.setting = Setting.id
                        WHERE Entities.id = ?;''', (id,))

    #  Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    #  The pictures value will convert the given string to a list.
    #  The picture names are stored as a string in the database,
    #  containing each file name seperated by spaces.
    #  set_picture_list converts this to a list,
    #  to guarantee that the variable is usable and can't be null.
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
        "pictures": set_picture_list(data[10]),
        "fav_moon_id": data[11],
        "header_picture": data[12],
        "id": data[13]
    }

    #  Since new lines cannot be stored properly in a string in sql,
    #  new lines in these strings are replaced with the string "\n".
    #  The new line strings are converted back into actual new lines,
    #  after being fetched from the database.
    #  These variables are also checked to not be null,
    #  so that .replace doesn't break the program.
    if params["bestiary"]:
        params["bestiary"] = params["bestiary"].replace("\\n", "\n")
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("entities/entity.html",
                           params=params,
                           title=params["name"],
                           admin=admin)


@app.route("/moons")  # Moon list.
def moons():
    #  Gather moons.
    data = execute_query('''
                        SELECT id, name, price, tier
                        FROM Moons;''')

    #  The moons need to be grouped by their tier,
    #  so the params list will contain a list of each moon for each tier.
    params = []
    for a in range(len(code_params.moon_tiers)):
        params.append([{
            "id": data[i][0],
            "name": data[i][1],
            "price": data[i][2]
        } for i in range(len(data)) if data[i][3] == a + 1])

    return render_template("moons/moonlist.html",
                           params=params,
                           title=get_title("/moons"),
                           admin=admin,
                           moon_tiers=code_params.moon_tiers)


@app.route("/moons/<int:id>")  # Moon data page.
def moon(id):
    #  Gather moon data.
    data = execute_query('''
                        SELECT Moons.name, RiskLevels.name, price, Interiors.id,
                        Interiors.name, max_indoor_power, max_outdoor_power,
                        conditions, history, fauna, Moons.description, tier,
                        Moons.pictures, Moons.id, Moons.header_picture
                        FROM Moons
                        JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                        JOIN Interiors ON Moons.interior = Interiors.id
                        WHERE Moons.id = ?;''', (id,))
    #  Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    #  Moons will have weathers that they can have,
    #  so this needs to be queried seperately,
    #  since they can have multiple weathers
    weatherdata = execute_query('''
                                SELECT id, name FROM Weathers WHERE id IN (
                                SELECT weather_id FROM MoonWeathers WHERE moon_id = ?);''', (id,))

    #  The pictures value will convert the given string to a list.
    #  The picture names are stored as a string in the database,
    #  containing each file name seperated by spaces.
    #  set_picture_list converts this to a list,
    #  to guarantee that the variable is usable and can't be null.
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
        "id": data[13],
        "header_picture": data[14]
    }

    #  Since new lines cannot be stored properly in a string in sql,
    #  new lines in these strings are replaced with the string "\n".
    #  The new line strings are converted back into actual new lines,
    #  after being fetched from the database.
    #  These variables are also checked to not be null,
    #  so that .replace doesn't break the program.
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
                           title=params["name"],
                           admin=admin)


@app.route("/tools", methods=['GET', 'POST'])  # Tool list.
def tools():
    #  Gather tools.
    data = execute_query('''
                        SELECT id, name, upgrade, price
                        FROM Tools
                        ORDER BY name;''')

    #  The tools need to be grouped by whether they're an upgrade,
    #  so the params list will contain a list of each tool upgrades and not upgrades.
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
                           admin=admin)


@app.route("/tools/<int:id>")  # Tool data page.
def tool(id):
    #  Gather tool data.
    data = execute_query('''
                        SELECT name, price, description, upgrade, weight,
                        pictures, id, header_picture
                        FROM Tools
                        WHERE id = ?;''', (id,))

    #  Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    #  The pictures value will convert the given string to a list.
    #  The picture names are stored as a string in the database,
    #  containing each file name seperated by spaces.
    #  set_picture_list converts this to a list,
    #  to guarantee that the variable is usable and can't be null.
    params = {
        "name": data[0],
        "price": data[1],
        "description": data[2],
        "upgrade": data[3],
        "weight": data[4],
        "pictures": set_picture_list(data[5]),
        "id": data[6],
        "header_picture": data[7]
    }

    #  Since new lines cannot be stored properly in a string in sql,
    #  new lines in these strings are replaced with the string "\n".
    #  The new line strings are converted back into actual new lines,
    #  after being fetched from the database.
    #  This variable is also checked to not be null,
    #  so that .replace doesn't break the program.
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("tools/tool.html",
                           params=params,
                           title=params["name"],
                           admin=admin)


@app.route("/weathers")  # Weather list.
def weathers():
    #  Gather weathers.
    data = execute_query('''
                        SELECT id, name
                        FROM Weathers;''')
    #  Organise weathers into a list of dictionaries.
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
    #  Gather weather data.
    data = execute_query('''
                        SELECT name, description, pictures, header_picture, id
                        FROM Weathers
                        WHERE id = ?;''', (id,))

    #  Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    #  Weathers will have moons that can have them,
    #  so this needs to be queried seperately,
    #  since they can belong to multiple moons.
    moondata = execute_query('''
                            SELECT id, name FROM Moons WHERE id IN (
                            SELECT moon_id FROM MoonWeathers WHERE weather_id=?);''', (id,))

    #  The pictures value will convert the given string to a list.
    #  The picture names are stored as a string in the database,
    #  containing each file name seperated by spaces.
    #  set_picture_list converts this to a list,
    #  to guarantee that the variable is usable and can't be null.
    params = {
        "name": data[0],
        "moons": moondata,
        "description": data[1],
        "pictures": set_picture_list(data[2]),
        "header_picture": data[3],
        "id": data[4]
    }

    #  Since new lines cannot be stored properly in a string in sql,
    #  new lines in these strings are replaced with the string "\n".
    #  The new line strings are converted back into actual new lines,
    #  after being fetched from the database.
    #  This variable is also checked to not be null,
    #  so that .replace doesn't break the program.
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("weathers/weather.html",
                           params=params,
                           title=params["name"],
                           admin=admin)


@app.route("/interiors")  # Interior list
def interiors():
    #  Gather interiors.
    data = execute_query('''
                        SELECT id, name
                        FROM Interiors;''')

    #  Organise interiors into a list of dictionaries.
    #  The first interior in the database is N/A, for moons without an interior.
    #  N/A should be a constant interior and somewhat hidden interior,
    #  which is why it won't be displayed.
    params = [{
        "id": data[i][0],
        "name": data[i][1]
    } for i in range(len(data)) if data[i][1] != "N/A"]

    return render_template("interiors/interiorlist.html",
                           params=params,
                           title=get_title("/interiors"),
                           admin=admin)


@app.route("/interiors/<int:id>")  # Interior data page.
def interior(id):
    #  Gather interior data.
    data = execute_query('''
                        SELECT name, description, pictures, header_picture, id
                        FROM Interiors
                        WHERE id = ?;''', (id,))

    #  Interiors will have moons that have them most commonly,
    #  so this needs to be queried seperately,
    #  since they can belong to multiple moons.
    moon_data = execute_query('''
                              SELECT id, name
                              FROM Moons
                              WHERE interior=?''', (id,))

    #  Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    #  The pictures value will convert the given string to a list.
    #  The picture names are stored as a string in the database,
    #  containing each file name seperated by spaces.
    #  set_picture_list converts this to a list,
    #  to guarantee that the variable is usable and can't be null.
    params = {
        "name": data[0],
        "description": data[1],
        "pictures": set_picture_list(data[2]),
        "header_picture": data[3],
        "id": data[4]
    }

    #  Since new lines cannot be stored properly in a string in sql,
    #  new lines in these strings are replaced with the string "\n".
    #  The new line strings are converted back into actual new lines,
    #  after being fetched from the database.
    #  This variable is also checked to not be null,
    #  so that .replace doesn't break the program.
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("interiors/interior.html",
                           params=params,
                           title=params['name'],
                           admin=admin,
                           moon_data=moon_data)


@app.route("/login")  # Page for the admin login.
def login():
    global login_message
    #  The login message should only be displayed once,
    #  so the current login message is stored, and then reset.
    current_login_message = login_message
    login_message = ""

    return render_template("login.html",
                           login_message=current_login_message,
                           admin=admin,
                           #  The usernames and passwords have maximum lengths,
                           #  so this is passed through as a variable.
                           username_max_length=code_params.username_max_length,
                           password_max_length=code_params.password_max_length,
                           title=get_title("/login"))


@app.route("/loginregister", methods=['GET', 'POST'])  # Register the inputted username and password.
def loginregister():
    global login_message, admin
    #  Boolean to store whether the login was a success.
    success = False

    #  The id of the user with the given username.
    userid = 0

    #  Fetch the HTML input data.
    username = request.form.get("username")
    password = request.form.get("password")

    #  Check if username is null.
    if not username:
        login_message = code_params.login_failure_message
        return app.redirect("/login")

    #  Check if password is null.
    if not password:
        login_message = code_params.login_failure_message
        return app.redirect("/login")

    #  Check if the given username is too long.
    if len(username) > code_params.username_max_length:
        login_message = code_params.username_too_large_message
        return app.redirect("/login")

    #  Check if the given password is too long.
    if len(password) > code_params.password_max_length:
        login_message = code_params.password_too_large_message
        return app.redirect("/login")

    # Gather the admin login data.
    userdata = execute_query("SELECT id, username FROM AdminLogins")

    #  Try to find the given username in the admin usernames.
    #  If the username is found, assign userid to that admin user id.
    for user in userdata:
        if username == user[1]:

            success = True
            userid = user[0]
            break
    #  Check if the given username was found in the admin usernames.
    if success:
        success = False
        #  Hash the given password and compare it with the stored password hash.
        #  Storing a hash in the database is much more secure than storing a password,
        #  and it is still very easy to check if a given password is correct.
        if check_password_hash(execute_query("SELECT passwordhash FROM AdminLogins WHERE id=?",
                                             (userid,))[0][0], password):
            #  If the password is correct the user will be logged in as admin.
            admin = True
            login_message = code_params.login_success_message
            success = True
    #  If username or password was wrong, return a failure message.
    if not success:
        login_message = code_params.login_failure_message
    return app.redirect("/login")


@app.route("/logout")  # Log the user out
def logout():
    global admin
    admin = False
    return app.redirect("/")


@app.route("/admin/moons/add")  # Page to add details for a new moon
def add_moon_page():
    if admin:
        global fail_message
        submit_message = fail_message
        fail_message = ""
        risk_level_entries = execute_query("SELECT id, name FROM RiskLevels;")
        interior_entries = execute_query("SELECT id, name FROM Interiors;")
        weather_entries = execute_query("SELECT id, name FROM Weathers;")
        return render_template("moons/moonadminadd.html",
                               risk_levels=risk_level_entries,
                               interiors=interior_entries,
                               weathers=weather_entries,
                               title=get_title("/admin/moons/add"),
                               message=submit_message,
                               name_max_length=code_params.moon_name_max_length,
                               conditions_max_length=code_params.moon_conditions_max_length,
                               history_max_length=code_params.moon_history_max_length,
                               fauna_max_length=code_params.moon_fauna_max_length,
                               description_max_length=code_params.moon_description_max_length)
    else:
        return admin_perms_denied()


@app.route("/admin/addmoon", methods=['GET', 'POST'])  # Add moon to database
def add_moon():
    if admin:
        global fail_message
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

        if not price:
            price = "0"

        if not max_indoor_power:
            max_indoor_power = "0"

        if not max_outdoor_power:
            max_outdoor_power = "0"

        if not name:
            return reject_input("/admin/moons/add", code_params.invalid_input)

        if len(name) > code_params.moon_name_max_length:
            return reject_input("/admin/moons/add", code_params.invalid_input)

        if not (risk_level in [str(i[0]) for i in execute_query("SELECT id FROM RiskLevels;")]):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        if not is_number(price):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        if not (moon_interior in [str(i[0]) for i in execute_query("SELECT id FROM Interiors;")]):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        if not is_number(max_indoor_power):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        if not is_number(max_outdoor_power):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        if conditions:
            if len(conditions) > code_params.moon_conditions_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        if history:
            if len(history) > code_params.moon_history_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        if fauna:
            if len(fauna) > code_params.moon_fauna_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        if description:
            if len(description) > code_params.moon_description_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        if is_number(tier):
            if int(tier) < 1 or int(tier) > code_params.moon_tier_range:
                return reject_input("/admin/moons/add", code_params.invalid_input)
        else:
            return reject_input("/admin/moons/add", code_params.invalid_input)

        weather_entries = execute_query("SELECT id FROM Weathers;")
        weather_list = []

        for i in range(len(weather_entries)):
            if request.form.get("weather" + str(weather_entries[i][0])):
                weather_list.append(weather_entries[i][0])

        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/moons/add", code_params.invalid_image)

        moon_id = execute_query("SELECT id FROM Moons;")[-1][0] + 1
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Moons/{moon_id}")
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Moons/{moon_id}/",
                                         header_picture_name))

        execute_query(
            '''
            INSERT INTO Moons (name, risk_level, price, interior, max_indoor_power,
            max_outdoor_power, conditions, history, fauna, description, tier, header_picture, pictures)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, risk_level, price, moon_interior, max_indoor_power, max_outdoor_power,
             conditions, history, fauna, description, tier, header_picture_name, "")
        )

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
        if not execute_query("SELECT id FROM Moons WHERE id=?", (id,)):
            abort(404)
        execute_query("DELETE FROM Moons WHERE id=?;", (id,))
        execute_query("DELETE FROM MoonWeathers WHERE moon_id=?", (id,))
        directory = f"{app.config["UPLOAD_FOLDER"]}/Moons/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)
        return app.redirect("/moons")
    else:
        return admin_perms_denied()


@app.route("/admin/moons/addimage/<int:id>")
def add_moon_image_page(id):
    if admin:
        global fail_message
        if not execute_query("SELECT id FROM Moons WHERE id=?", (id,)):
            abort(404)
        moon_name = execute_query("SELECT name FROM Moons WHERE id=?;", (id,))
        submit_message = fail_message
        fail_message = ""
        return render_template("moons/moonadminaddimage.html",
                               name=moon_name[0][0],
                               title=get_title("/admin/moons/addimage"),
                               id=id,
                               message=submit_message)
    else:
        return admin_perms_denied()


@app.route("/admin/moons/addmoonimage/<int:id>", methods=["GET", "POST"])
def add_moon_image(id):
    if admin:
        if not execute_query("SELECT id FROM Moons WHERE id=?", (id,)):
            abort(404)
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Moons/{id}"))

        if not image_data:
            return reject_input(f"/admin/moons/addimage/{id}", code_params.invalid_image)
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Moons/{id}/",
                                        image_name))
        pictures = execute_query("SELECT pictures FROM Moons WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)

        execute_query('''
                      UPDATE Moons
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        return app.redirect(f"/moons/{id}")
    else:
        return admin_perms_denied()


@app.route("/admin/moons/deleteimage/<int:id>")
def delete_moon_image_page(id):
    if admin:
        if not execute_query("SELECT id FROM Moons WHERE id=?;", (id,)):
            abort(404)
        picture_data = execute_query("SELECT pictures FROM Moons WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)
        for i in range(picture_count):
            picture_id.append(i)
        return render_template("moons/moonadmindeleteimage.html",
                               title=get_title("/admin/moons/deleteimage"),
                               pictures=picture_data,
                               ids=picture_id,
                               moon_id=id,
                               size=picture_count,
                               name=execute_query("SELECT name FROM Moons WHERE id=?",
                                                  (id,))[0][0])
    else:
        return admin_perms_denied()


@app.route("/admin/moons/deletemoonimage/<int:moon_id>/<int:picture_id>")
def delete_moon_image(moon_id, picture_id):
    if admin:
        if not execute_query("SELECT id FROM Moons WHERE id=?", (moon_id,)):
            abort(404)
        pictures = execute_query("SELECT pictures FROM Moons WHERE id=?", (moon_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Moons/{moon_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Moons
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, moon_id))

        return app.redirect(f"/moons/{moon_id}")
    else:
        return admin_perms_denied()


@app.route("/admin/entity/add")  # Page to add details for a new entity
def add_entity_page():
    if admin:
        global fail_message
        setting_entries = execute_query("SELECT id, name FROM Setting;")
        moon_entries = execute_query("SELECT id, name FROM Moons;")
        submit_message = fail_message
        fail_message = ""
        return render_template("entities/entityadminadd.html",
                               settings=setting_entries,
                               moons=moon_entries,
                               title=get_title("/admin/entity/add"),
                               message=submit_message)
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

        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/entity/add", code_params.invalid_image)

        entity_id = execute_query("SELECT id FROM Entities;")[-1][0] + 1
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Entities/{entity_id}")
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Entities/{entity_id}/",
                                         header_picture_name))

        execute_query('''
                      INSERT INTO Entities (name, danger, bestiary, setting,
                      fav_moon, sp_hp, mp_hp, power, max_spawned, description, header_picture, pictures)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (name, danger_rating, bestiary, setting, fav_moon, sp_hp,
                       mp_hp, power, max_spawned, description, header_picture_name, ""))
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
        if not execute_query("SELECT id FROM Entities WHERE id=?", (id,)):
            abort(404)
        execute_query("DELETE FROM Entities WHERE id=?;", (id,))
        directory = f"{app.config["UPLOAD_FOLDER"]}/Entities/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)
        return app.redirect("/entity")
    else:
        return admin_perms_denied()


@app.route("/admin/entity/addimage/<int:id>")
def add_entity_image_page(id):
    if admin:
        global fail_message
        if not execute_query("SELECT id FROM Entities WHERE id=?", (id,)):
            abort(404)
        entity_name = execute_query("SELECT name FROM Entities WHERE id=?;", (id,))
        submit_message = fail_message
        fail_message = ""
        return render_template("entities/entityadminaddimage.html",
                               name=entity_name[0][0],
                               title=get_title("/admin/entity/addimage"),
                               id=id,
                               message=submit_message)
    else:
        return admin_perms_denied()


@app.route("/admin/entity/addentityimage/<int:id>", methods=["GET", "POST"])
def add_entity_image(id):
    if admin:
        if not execute_query("SELECT id FROM Entities WHERE id=?", (id,)):
            abort(404)
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Entities/{id}"))
        if not image_data:
            return reject_input(f"/admin/entity/addimage/{id}", code_params.invalid_image)
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Entities/{id}/",
                                        image_name))
        pictures = execute_query("SELECT pictures FROM Entities WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)

        execute_query('''
                      UPDATE Entities
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        return app.redirect(f"/entity/{id}")
    else:
        return admin_perms_denied()


@app.route("/admin/entity/deleteimage/<int:id>")
def delete_entity_image_page(id):
    if admin:
        if not execute_query("SELECT id FROM Entities WHERE id=?;", (id,)):
            abort(404)
        picture_data = execute_query("SELECT pictures FROM Entities WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)
        for i in range(picture_count):
            picture_id.append(i)
        return render_template("entities/entityadmindeleteimage.html",
                               title=get_title("/admin/entity/deleteimage"),
                               pictures=picture_data,
                               ids=picture_id,
                               entity_id=id,
                               size=picture_count,
                               name=execute_query("SELECT name FROM Entities WHERE id=?",
                                                  (id,))[0][0])
    else:
        return admin_perms_denied()


@app.route("/admin/entity/deleteentityimage/<int:entity_id>/<int:picture_id>")
def delete_entity_image(entity_id, picture_id):
    if admin:
        if not execute_query("SELECT id FROM Entities WHERE id=?", (entity_id,)):
            abort(404)
        pictures = execute_query("SELECT pictures FROM Entities WHERE id=?", (entity_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Entities/{entity_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Entities
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, entity_id))

        return app.redirect(f"/entity/{entity_id}")
    else:
        return admin_perms_denied()


@app.route("/admin/tools/add")  # Page to add details for a new tool
def add_tool_page():
    if admin:
        global fail_message
        submit_message = fail_message
        fail_message = ""
        return render_template("tools/tooladminadd.html",
                               title=get_title("/admin/tools/add"),
                               message=submit_message)
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

        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/tools/add", code_params.invalid_image)

        tool_id = execute_query("SELECT id FROM Tools;")[-1][0] + 1
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Tools/{tool_id}")
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Tools/{tool_id}/",
                                         header_picture_name))

        execute_query('''
                      INSERT INTO Tools
                      (name, price, description, upgrade, weight, header_picture, pictures)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (name, price, description, upgrade, weight, header_picture_name, ""))

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
        if not execute_query("SELECT id FROM Tools WHERE id=?", (id,)):
            abort(404)
        execute_query("DELETE FROM Tools WHERE id=?", (id,))
        directory = f"{app.config["UPLOAD_FOLDER"]}/Tools/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)
        return app.redirect("/tools")
    else:
        return admin_perms_denied()


@app.route("/admin/tools/addimage/<int:id>")
def add_tool_image_page(id):
    if admin:
        global fail_message
        if not execute_query("SELECT id FROM Tools WHERE id=?", (id,)):
            abort(404)
        tool_name = execute_query("SELECT name FROM Tools WHERE id=?;", (id,))
        submit_message = fail_message
        fail_message = ""
        return render_template("tools/tooladminaddimage.html",
                               name=tool_name[0][0],
                               title=get_title("/admin/tools/addimage"),
                               id=id,
                               message=submit_message)
    else:
        return admin_perms_denied()


@app.route("/admin/tools/addtoolimage/<int:id>", methods=["GET", "POST"])
def add_tool_image(id):
    if admin:
        if not execute_query("SELECT id FROM Tools WHERE id=?", (id,)):
            abort(404)
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Tools/{id}"))
        if not image_data:
            return reject_input(f"/admin/tools/addimage/{id}", code_params.invalid_image)
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Tools/{id}/",
                                        image_name))
        pictures = execute_query("SELECT pictures FROM Tools WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)

        execute_query('''
                      UPDATE Tools
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        return app.redirect(f"/tools/{id}")
    else:
        return admin_perms_denied()


@app.route("/admin/tools/deleteimage/<int:id>")
def delete_tool_image_page(id):
    if admin:
        if not execute_query("SELECT id FROM Tools WHERE id=?;", (id,)):
            abort(404)
        picture_data = execute_query("SELECT pictures FROM Tools WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)
        for i in range(picture_count):
            picture_id.append(i)
        return render_template("tools/tooladmindeleteimage.html",
                               title=get_title("/admin/tools/deleteimage"),
                               pictures=picture_data,
                               ids=picture_id,
                               tool_id=id,
                               size=picture_count,
                               name=execute_query("SELECT name FROM Tools WHERE id=?",
                                                  (id,))[0][0])
    else:
        return admin_perms_denied()


@app.route("/admin/tools/deletetoolimage/<int:tool_id>/<int:picture_id>")
def delete_tool_image(tool_id, picture_id):
    if admin:
        if not execute_query("SELECT id FROM Tools WHERE id=?", (tool_id,)):
            abort(404)
        pictures = execute_query("SELECT pictures FROM Tools WHERE id=?", (tool_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Tools/{tool_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Tools
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, tool_id))

        return app.redirect(f"/tools/{tool_id}")
    else:
        return admin_perms_denied()


@app.route("/admin/weathers/add")  # Page to add details for a new weather
def add_weather_page():
    if admin:
        global fail_message
        moon_entries = execute_query("SELECT id, name FROM Moons")
        submit_message = fail_message
        fail_message = ""
        return render_template("weathers/weatheradminadd.html",
                               moons=moon_entries,
                               title=get_title("/admin/weathers/add"),
                               message=submit_message)
    else:
        return admin_perms_denied()


@app.route("/admin/addweather", methods=["GET", "POST"])  # Add weather to database
def add_weather():
    if admin:
        name = request.form.get("name")
        description = request.form.get("description").replace("\n", "\\n")

        moon_entries = execute_query("SELECT id FROM Moons;")
        moon_list = []

        for i in range(len(moon_entries)):
            if request.form.get("moon" + str(moon_entries[i][0])):
                moon_list.append(moon_entries[i][0])

        weather_id = execute_query("SELECT id FROM Weathers;")[-1][0] + 1

        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/weathers/add", code_params.invalid_image)

        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{weather_id}")
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{weather_id}/",
                                         header_picture_name))

        execute_query('''
                      INSERT INTO Weathers (name, description, header_picture, pictures)
                      VALUES (?, ?, ?, ?)''',
                      (name, description, header_picture_name, ""))

        for i in range(len(moon_list)):
            execute_query('''
                          INSERT INTO MoonWeathers (moon_id, weather_id)
                          VALUES (?, ?)''',
                          (moon_list[i], weather_id))

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
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (id,)):
            abort(404)
        execute_query("DELETE FROM Weathers WHERE id=?", (id,))
        execute_query("DELETE FROM MoonWeathers WHERE weather_id=?", (id,))
        directory = f"{app.config["UPLOAD_FOLDER"]}/Weathers/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)
        return app.redirect("/weathers")
    else:
        return admin_perms_denied()


@app.route("/admin/weathers/addimage/<int:id>")
def add_weather_image_page(id):
    if admin:
        global fail_message
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (id,)):
            abort(404)
        weather_name = execute_query("SELECT name FROM Weathers WHERE id=?;", (id,))
        submit_message = fail_message
        fail_message = ""
        return render_template("weathers/weatheradminaddimage.html",
                               name=weather_name[0][0],
                               title=get_title("/admin/weathers/addimage"),
                               id=id,
                               message=submit_message)
    else:
        return admin_perms_denied()


@app.route("/admin/weathers/addweatherimage/<int:id>", methods=["GET", "POST"])
def add_weather_image(id):
    if admin:
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (id,)):
            abort(404)
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{id}"))
        if not image_data:
            return reject_input(f"/admin/weathers/addimage/{id}", code_params.invalid_image)
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{id}/",
                                        image_name))
        pictures = execute_query("SELECT pictures FROM Weathers WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)

        execute_query('''
                      UPDATE Weathers
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        return app.redirect(f"/weathers/{id}")
    else:
        return admin_perms_denied()


@app.route("/admin/weathers/deleteimage/<int:id>")
def delete_weather_image_page(id):
    if admin:
        if not execute_query("SELECT id FROM Weathers WHERE id=?;", (id,)):
            abort(404)
        picture_data = execute_query("SELECT pictures FROM Weathers WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)
        for i in range(picture_count):
            picture_id.append(i)
        return render_template("weathers/weatheradmindeleteimage.html",
                               title=get_title("/admin/weathers/deleteimage"),
                               pictures=picture_data,
                               ids=picture_id,
                               weather_id=id,
                               size=picture_count,
                               name=execute_query("SELECT name FROM Weathers WHERE id=?",
                                                  (id,))[0][0])
    else:
        return admin_perms_denied()


@app.route("/admin/weathers/deleteweatherimage/<int:weather_id>/<int:picture_id>")
def delete_weather_image(weather_id, picture_id):
    if admin:
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (weather_id,)):
            abort(404)
        pictures = execute_query("SELECT pictures FROM Weathers WHERE id=?", (weather_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{weather_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Weathers
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, weather_id))

        return app.redirect(f"/weathers/{weather_id}")
    else:
        return admin_perms_denied()


@app.route("/admin/interiors/add")  # Page to add details for a new interior
def add_interior_page():
    if admin:
        global fail_message
        submit_message = fail_message
        return render_template("interiors/interioradminadd.html",
                               title=get_title("/admin/interiors/add"),
                               message=submit_message)
    else:
        return admin_perms_denied()


@app.route("/admin/addinterior", methods=["GET", "POST"])  # Add interior to database
def add_interior():
    if admin:
        name = request.form.get("name")
        description = request.form.get("description").replace("\n", "\\n")

        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/interiors/add", code_params.invalid_image)

        interior_id = execute_query("SELECT id FROM Interiors;")[-1][0] + 1
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{interior_id}")
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{interior_id}/",
                                         header_picture_name))
        execute_query('''
                      INSERT INTO Interiors (name, description, header_picture, pictures)
                      VALUES (?, ?, ?, ?)''',
                      (name, description, header_picture_name, ""))
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
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (id,)):
            abort(404)
        if not id == 1:
            execute_query("DELETE FROM Interiors WHERE id=?", (id,))
            directory = f"{app.config["UPLOAD_FOLDER"]}/Interiors/{id}"
            for file in os.listdir(directory):
                os.remove(f"{directory}/{file}")
            os.rmdir(directory)
            return app.redirect("/interiors")
        else:
            abort(404)
    else:
        return admin_perms_denied()


@app.route("/admin/interiors/addimage/<int:id>")
def add_interior_image_page(id):
    if admin:
        global fail_message
        if id == 1:
            abort(404)
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (id,)):
            abort(404)
        interior_name = execute_query("SELECT name FROM Interiors WHERE id=?;", (id,))
        submit_message = fail_message
        fail_message = ""
        return render_template("interiors/interioradminaddimage.html",
                               name=interior_name[0][0],
                               title=get_title("/admin/interiors/addimage"),
                               id=id,
                               message=submit_message)
    else:
        return admin_perms_denied()


@app.route("/admin/interiors/addinteriorimage/<int:id>", methods=["GET", "POST"])
def add_interior_image(id):
    if admin:
        if id == 1:
            abort(404)
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (id,)):
            abort(404)
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{id}"))
        if not image_data:
            return reject_input(f"/admin/interiors/addimage/{id}", code_params.invalid_image)
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{id}/",
                                        image_name))
        pictures = execute_query("SELECT pictures FROM Interiors WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)

        execute_query('''
                      UPDATE Interiors
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        return app.redirect(f"/interiors/{id}")
    else:
        return admin_perms_denied()


@app.route("/admin/interiors/deleteimage/<int:id>")
def delete_interior_image_page(id):
    if admin:
        if id == 1:
            abort(404)
        if not execute_query("SELECT id FROM Interiors WHERE id=?;", (id,)):
            abort(404)
        picture_data = execute_query("SELECT pictures FROM Interiors WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)
        for i in range(picture_count):
            picture_id.append(i)
        return render_template("interiors/interioradmindeleteimage.html",
                               title=get_title("/admin/interiors/deleteimage"),
                               pictures=picture_data,
                               ids=picture_id,
                               interior_id=id,
                               size=picture_count,
                               name=execute_query("SELECT name FROM Interiors WHERE id=?",
                                                  (id,))[0][0])
    else:
        return admin_perms_denied()


@app.route("/admin/interiors/deleteinteriorimage/<int:interior_id>/<int:picture_id>")
def delete_interior_image(interior_id, picture_id):
    if admin:
        if interior_id == 1:
            abort(404)
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (interior_id,)):
            abort(404)
        pictures = execute_query("SELECT pictures FROM Interiors WHERE id=?", (interior_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{interior_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Interiors
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, interior_id))

        return app.redirect(f"/interiors/{interior_id}")
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

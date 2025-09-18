from flask import Flask, render_template, request, abort
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import code_params
import os

app = Flask(__name__)
DATABASE = "LCdb.db"
app.config["UPLOAD_FOLDER"] = code_params.upload_folder

# List to hold the route history of the user
page_history = []

# Boolean to hold if the user is signed in as an admin.
admin = False

# The message when the user attempts to log in.
# This is a global variable so that multiple routes can access it easily.
login_message = ""

# The message when the user fails to use an admin tool properly.
# This is a global variable so that multiple routes can access it easily.
fail_message = ""


def execute_query(query, params=()):
    '''Executes a query in the database based on parameters'''
    with sqlite3.connect(DATABASE) as db:
        return db.cursor().execute(query, params).fetchall()


def set_picture_list(picture_string):
    '''Formats the picture string into list'''
    # Check if the string can be split before splitting it to prevent errors.
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
    # Page titles are stored in the database with the page route as the identifier.
    return execute_query('''
                         SELECT title
                         FROM PageTitles
                         WHERE route=?''', (route,))[0][0]


def push_error(number, code):
    '''Redirect the user to the error page with the given code'''
    # The error page has a modular design by just displaying a given error code.
    return render_template("error_page.html",
                           error_code=number,
                           title=f"{number} Error",
                           error=code), number


def reject_input(route, message):
    '''Redirect the user to a page with a message'''
    # The user can mess up admin queries in different ways,
    # so this is here to tell the user what went wrong.
    global fail_message
    fail_message = message
    return app.redirect(route)


def is_number(x):
    '''Check if the given string is able to be converted to a number'''
    # This function would only be called a few times on a page load,
    # so the brute force nature of it doesn't hinder the program.
    try:
        int(x)
    except ValueError:
        return False
    else:
        return True


def process_image(name):
    '''Organise file data from an HTML form using the given name'''

    # Check if the given name has been sent from the HTML form.
    # This is to prevent inspect element changes from breaking the code.
    if name not in request.files:
        return False

    # Get the file data and the name of the file.
    file = request.files[name]
    filename = secure_filename(file.filename)
    # Check that the data is valid.
    if not (file and filename and file.name):
        return False

    return (file, filename)


def get_image_name(name, directory):
    '''Renames the given file name if it already exists in the given directory'''
    # If two files with the same file name are uploaded, deleting one will delete the other.
    # To prevent this, this function will ensure that the returned file name will be unqiue.
    # For example, if image.png exists already, it will be renamed to image(1).png

    # Check that the name isn't null to prevent errors.
    if name:

        # Check if the directory isn't null to prevent errors.
        if not directory:
            return name

        # If the name is already unique, the function will just return the name.
        if name not in directory:
            return name

        # Save the original file name so that the name parameter can be modified.
        og_name = name

        # Search for the last instance of a period, which would be before the file type identifier.
        # This is to make sure that the file type isn't messed up if the name is changed.
        # Going backwards through the list should be the most efficient way, because the last period is desired.
        for i in range(len(name)):
            if name[-1 - i] == ".":
                index = len(name) - 1 - i
                break

        # Keep changing the file name until it is unique.
        # By adding a number in brackets before the file type identifier,
        # increasing it would yield a unqiue name at some point.
        count = 1
        while name in directory:
            name = f"{og_name[:index]}({count}){og_name[index:]}"
            count += 1
        return name
    else:
        return False


@app.route("/")  # Home page for selection.
def home():
    # The home page sections are stored in the database,
    # so it needs to be accessed.
    params = execute_query('''
                           SELECT display_name, description, link
                           FROM HomePageLinks;''')

    return render_template("main.html",
                           params=params,
                           title=get_title("/"),
                           admin=admin)


@app.route("/entity", methods=['GET', 'POST'])  # Entity list.
def entities():
    # Gather entities.
    data = execute_query('''
                            SELECT id, name, setting
                            FROM Entities
                            ORDER BY name;''')

    # The entities need to be grouped by their setting,
    # so the params list will contain a list of each entity for each setting.
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
    # Gather entity data.
    data = execute_query('''
                        SELECT Entities.name, danger, bestiary, Setting.name,
                        Moons.name, sp_hp, mp_hp, power, max_spawned,
                        Entities.description, Entities.pictures, Moons.id,
                        Entities.header_picture, Entities.id
                        FROM Entities
                        JOIN Moons ON Entities.fav_moon = Moons.id
                        JOIN Setting ON Entities.setting = Setting.id
                        WHERE Entities.id = ?;''', (id,))

    # Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    # The pictures value will convert the given string to a list.
    # The picture names are stored as a string in the database,
    # containing each file name seperated by spaces.
    # set_picture_list converts this to a list,
    # to guarantee that the variable is usable and can't be null.
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

    # Since new lines cannot be stored properly in a string in sql,
    # new lines in these strings are replaced with the string "\n".
    # The new line strings are converted back into actual new lines,
    # after being fetched from the database.
    # These variables are also checked to not be null,
    # so that .replace doesn't break the program.
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
    # Gather moons.
    data = execute_query('''
                        SELECT id, name, price, tier
                        FROM Moons;''')

    # The moons need to be grouped by their tier,
    # so the params list will contain a list of each moon for each tier.
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
    # Gather moon data.
    data = execute_query('''
                        SELECT Moons.name, RiskLevels.name, price, Interiors.id,
                        Interiors.name, max_indoor_power, max_outdoor_power,
                        conditions, history, fauna, Moons.description, tier,
                        Moons.pictures, Moons.id, Moons.header_picture
                        FROM Moons
                        JOIN RiskLevels ON Moons.risk_level = RiskLevels.id
                        JOIN Interiors ON Moons.interior = Interiors.id
                        WHERE Moons.id = ?;''', (id,))
    # Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    # Moons will have weathers that they can have,
    # so this needs to be queried seperately,
    # since they can have multiple weathers
    weatherdata = execute_query('''
                                SELECT id, name FROM Weathers WHERE id IN (
                                SELECT weather_id FROM MoonWeathers WHERE moon_id = ?);''', (id,))

    # The pictures value will convert the given string to a list.
    # The picture names are stored as a string in the database,
    # containing each file name seperated by spaces.
    # set_picture_list converts this to a list,
    # to guarantee that the variable is usable and can't be null.
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

    # Since new lines cannot be stored properly in a string in sql,
    # new lines in these strings are replaced with the string "\n".
    # The new line strings are converted back into actual new lines,
    # after being fetched from the database.
    # These variables are also checked to not be null,
    # so that .replace doesn't break the program.
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
    # Gather tools.
    data = execute_query('''
                        SELECT id, name, upgrade, price
                        FROM Tools
                        ORDER BY name;''')

    # The tools need to be grouped by whether they're an upgrade,
    # so the params list will contain a list of each tool upgrades and not upgrades.
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
    # Gather tool data.
    data = execute_query('''
                        SELECT name, price, description, upgrade, weight,
                        pictures, id, header_picture
                        FROM Tools
                        WHERE id = ?;''', (id,))

    # Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    # The pictures value will convert the given string to a list.
    # The picture names are stored as a string in the database,
    # containing each file name seperated by spaces.
    # set_picture_list converts this to a list,
    # to guarantee that the variable is usable and can't be null.
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

    # Since new lines cannot be stored properly in a string in sql,
    # new lines in these strings are replaced with the string "\n".
    # The new line strings are converted back into actual new lines,
    # after being fetched from the database.
    # This variable is also checked to not be null,
    # so that .replace doesn't break the program.
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("tools/tool.html",
                           params=params,
                           title=params["name"],
                           admin=admin)


@app.route("/weathers")  # Weather list.
def weathers():
    # Gather weathers.
    data = execute_query('''
                        SELECT id, name
                        FROM Weathers;''')
    # Organise weathers into a list of dictionaries.
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
    # Gather weather data.
    data = execute_query('''
                        SELECT name, description, pictures, header_picture, id
                        FROM Weathers
                        WHERE id = ?;''', (id,))

    # Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    # Weathers will have moons that can have them,
    # so this needs to be queried seperately,
    # since they can belong to multiple moons.
    moondata = execute_query('''
                            SELECT id, name FROM Moons WHERE id IN (
                            SELECT moon_id FROM MoonWeathers WHERE weather_id=?);''', (id,))

    # The pictures value will convert the given string to a list.
    # The picture names are stored as a string in the database,
    # containing each file name seperated by spaces.
    # set_picture_list converts this to a list,
    # to guarantee that the variable is usable and can't be null.
    params = {
        "name": data[0],
        "moons": moondata,
        "description": data[1],
        "pictures": set_picture_list(data[2]),
        "header_picture": data[3],
        "id": data[4]
    }

    # Since new lines cannot be stored properly in a string in sql,
    # new lines in these strings are replaced with the string "\n".
    # The new line strings are converted back into actual new lines,
    # after being fetched from the database.
    # This variable is also checked to not be null,
    # so that .replace doesn't break the program.
    if params["description"]:
        params["description"] = params["description"].replace("\\n", "\n")

    return render_template("weathers/weather.html",
                           params=params,
                           title=params["name"],
                           admin=admin)


@app.route("/interiors")  # Interior list
def interiors():
    # Gather interiors.
    data = execute_query('''
                        SELECT id, name
                        FROM Interiors;''')

    # Organise interiors into a list of dictionaries.
    # The first interior in the database is N/A, for moons without an interior.
    # N/A should be a constant interior and somewhat hidden interior,
    # which is why it won't be displayed.
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
    # Gather interior data.
    data = execute_query('''
                        SELECT name, description, pictures, header_picture, id
                        FROM Interiors
                        WHERE id = ?;''', (id,))

    # Interiors will have moons that have them most commonly,
    # so this needs to be queried seperately,
    # since they can belong to multiple moons.
    moon_data = execute_query('''
                              SELECT id, name
                              FROM Moons
                              WHERE interior=?''', (id,))

    # Return a 404 error if the data doesn't exist.
    if not data:
        abort(404)

    data = data[0]

    # The pictures value will convert the given string to a list.
    # The picture names are stored as a string in the database,
    # containing each file name seperated by spaces.
    # set_picture_list converts this to a list,
    # to guarantee that the variable is usable and can't be null.
    params = {
        "name": data[0],
        "description": data[1],
        "pictures": set_picture_list(data[2]),
        "header_picture": data[3],
        "id": data[4]
    }

    # Since new lines cannot be stored properly in a string in sql,
    # new lines in these strings are replaced with the string "\n".
    # The new line strings are converted back into actual new lines,
    # after being fetched from the database.
    # This variable is also checked to not be null,
    # so that .replace doesn't break the program.
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
    # The login message should only be displayed once,
    # so the current login message is stored, and then reset.
    current_login_message = login_message
    login_message = ""

    return render_template("login.html",
                           login_message=current_login_message,
                           admin=admin,
                           # The usernames and passwords have maximum lengths,
                           # so this is passed through as a variable.
                           username_max_length=code_params.username_max_length,
                           password_max_length=code_params.password_max_length,
                           title=get_title("/login"))


@app.route("/loginregister", methods=['GET', 'POST'])  # Register the inputted username and password.
def loginregister():
    global login_message, admin
    # Boolean to store whether the login was a success.
    success = False

    # The id of the user with the given username.
    userid = 0

    # Fetch the HTML input data.
    username = request.form.get("username")
    password = request.form.get("password")

    # Check if username is null.
    if not username:
        login_message = code_params.login_failure_message
        return app.redirect("/login")

    # Check if password is null.
    if not password:
        login_message = code_params.login_failure_message
        return app.redirect("/login")

    # Check if the given username is too long.
    if len(username) > code_params.username_max_length:
        login_message = code_params.username_too_large_message
        return app.redirect("/login")

    # Check if the given password is too long.
    if len(password) > code_params.password_max_length:
        login_message = code_params.password_too_large_message
        return app.redirect("/login")

    # Gather the admin login data.
    userdata = execute_query("SELECT id, username FROM AdminLogins")

    # Try to find the given username in the admin usernames.
    # If the username is found, assign userid to that admin user id.
    for user in userdata:
        if username == user[1]:

            success = True
            userid = user[0]
            break
    # Check if the given username was found in the admin usernames.
    if success:
        success = False
        # Hash the given password and compare it with the stored password hash.
        # Storing a hash in the database is much more secure than storing a password,
        # and it is still very easy to check if a given password is correct.
        if check_password_hash(execute_query("SELECT passwordhash FROM AdminLogins WHERE id=?",
                                             (userid,))[0][0], password):
            # If the password is correct the user will be logged in as admin.
            admin = True
            login_message = code_params.login_success_message
            success = True
    # If username or password was wrong, return a failure message.
    if not success:
        login_message = code_params.login_failure_message
    return app.redirect("/login")


@app.route("/logout")  # Log the user out.
def logout():
    global admin
    admin = False
    return app.redirect("/")


@app.route("/admin/moons/add")  # Page to add details for a new moon.
def add_moon_page():
    # Check if the user is logged in as admin.
    if admin:
        global fail_message
        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        # The page needs to know the risk levels, interiors, and weathers
        # for the drop down options.
        risk_level_entries = execute_query("SELECT id, name FROM RiskLevels;")
        interior_entries = execute_query("SELECT id, name FROM Interiors;")
        weather_entries = execute_query("SELECT id, name FROM Weathers;")
        return render_template("moons/moonadminadd.html",
                               risk_levels=risk_level_entries,
                               interiors=interior_entries,
                               weathers=weather_entries,
                               title=get_title("/admin/moons/add"),
                               message=submit_message,
                               # Some of the inputs have a max length,
                               # so they are passed through as a variable.
                               name_max_length=code_params.moon_name_max_length,
                               conditions_max_length=code_params.moon_conditions_max_length,
                               history_max_length=code_params.moon_history_max_length,
                               fauna_max_length=code_params.moon_fauna_max_length,
                               description_max_length=code_params.moon_description_max_length)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/addmoon", methods=['GET', 'POST'])  # Add moon to database.
def add_moon():
    # Check if the user is logged in as admin.
    if admin:
        global fail_message
        # Get all of the data from the HTML form.
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

        # The strings need the new lines to be replaced with "\n",
        # so that the new lines can be stored properly in the database.
        conditions = conditions.replace("\n", "\\n")
        history = history.replace("\n", "\\n")
        fauna = fauna.replace("\n", "\\n")
        description = description.replace("\n", "\\n")

        # The function needs to test that all of the inputs are usable.

        # If the price is null, make it 0.
        if not price:
            price = "0"

        # If the max indoor power is null, make it 0.
        if not max_indoor_power:
            max_indoor_power = "0"

        # If the max outdoor power is null, make it 0.
        if not max_outdoor_power:
            max_outdoor_power = "0"

        # If the name is null, reject the submission.
        if not name:
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the name is too long, reject the submission.
        if len(name) > code_params.moon_name_max_length:
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the risk level doesn't exist in the database, reject the submission.
        if not (risk_level in [str(i[0]) for i in execute_query("SELECT id FROM RiskLevels;")]):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the price isn't a number, reject the submission.
        if not is_number(price):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the interior doesn't exist, reject the submission.
        if not (moon_interior in [str(i[0]) for i in execute_query("SELECT id FROM Interiors;")]):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the max indoor power isn't a number, reject the submission.
        if not is_number(max_indoor_power):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the max outdoor power isn't a number, reject the submission.
        if not is_number(max_outdoor_power):
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the conditions string is too long, reject the submission.
        # The conditions is checked to not be null, so that len doesn't break the program.
        if conditions:
            if len(conditions) > code_params.moon_conditions_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the history string is too long, reject the submission.
        # The history is checked to not be null, so that len doesn't break the program.
        if history:
            if len(history) > code_params.moon_history_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the fauna string is too long, reject the submission.
        # The fauna is checked to not be null, so that len doesn't break the program.
        if fauna:
            if len(fauna) > code_params.moon_fauna_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the description string is too long, reject the submission.
        # The description is checked to not be null, so that len doesn't break the program.
        if description:
            if len(description) > code_params.moon_description_max_length:
                return reject_input("/admin/moons/add", code_params.invalid_input)

        # If the tier isn't a number, reject the submission.
        # If the tier isn't in the right number range, reject the submission.
        if is_number(tier):
            if int(tier) < 1 or int(tier) > code_params.moon_tier_range:
                return reject_input("/admin/moons/add", code_params.invalid_input)
        else:
            return reject_input("/admin/moons/add", code_params.invalid_input)

        # Gather all of the weathers in the database.
        weather_entries = execute_query("SELECT id FROM Weathers;")
        weather_list = []

        # This checks which weathers in the database are selected in the HTML form.
        # This is done by storing the weather ids that match ticked checkboxes
        # in a list.
        for i in range(len(weather_entries)):
            if request.form.get("weather" + str(weather_entries[i][0])):
                weather_list.append(weather_entries[i][0])

        # Fetch the header picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/moons/add", code_params.invalid_image)

        # Get the next usable id in the Moons table.
        # The base order is by id, so the last id + 1
        # will always be unique.
        moon_id = execute_query("SELECT id FROM Moons;")[-1][0] + 1

        # Create a folder with the moon id as the name in the Moons folder.
        # UPLOAD_FOLDER is the base directory of the images, being static/images.
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Moons/{moon_id}")

        # Save the picture in the created folder.
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Moons/{moon_id}/",
                                         header_picture_name))

        # This query inserts the Moon data collected from the HTML form,
        # into a new moon.
        # pictures is kept blank, because they need to be added through
        # the website.
        execute_query(
            '''
            INSERT INTO Moons (name, risk_level, price, interior, max_indoor_power,
            max_outdoor_power, conditions, history, fauna, description, tier, header_picture, pictures)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, risk_level, price, moon_interior, max_indoor_power, max_outdoor_power,
             conditions, history, fauna, description, tier, header_picture_name, "")
        )

        # Insert the bridging entries between the new moon and the weathers,
        # into the bridging table.
        for i in weather_list:
            execute_query('''
                          INSERT INTO MoonWeathers (moon_id, weather_id)
                          VALUES (?, ?)''',
                          (moon_id, i))
        # Redirect the user to the moon list.
        return app.redirect("/moons")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/moons/delete")  # Page to select a moon to delete.
def delete_moon_page():
    # Check if the user is logged in as admin.
    if admin:
        # Gather the moon names and ids.
        moon_list = execute_query("SELECT id, name FROM Moons")
        return render_template("moons/moonadmindelete.html",
                               moons=moon_list,
                               title=get_title("/admin/moons/delete"))
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/deletemoon/<int:id>")  # Delete the selected moon.
def delete_moon(id):
    # Check if the user is logged in as admin.
    if admin:
        # If the id does not belong in the Moons table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Moons WHERE id=?", (id,)):
            abort(404)

        # Delete the moon and the moon-weather bridging entries,
        # that have the moon id.
        execute_query("DELETE FROM Moons WHERE id=?;", (id,))
        execute_query("DELETE FROM MoonWeathers WHERE moon_id=?", (id,))

        # Delete every file in the moon's folder, and delete the folder.
        directory = f"{app.config["UPLOAD_FOLDER"]}/Moons/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)

        # Redirect the user to the moon list.
        return app.redirect("/moons")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/moons/addimage/<int:id>")  # Page to add an image to a moon.
def add_moon_image_page(id):
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # If the id does not belong to the moons table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Moons WHERE id=?", (id,)):
            abort(404)

        # Get the name of the moon.
        moon_name = execute_query("SELECT name FROM Moons WHERE id=?;", (id,))

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("moons/moonadminaddimage.html",
                               name=moon_name[0][0],
                               title=get_title("/admin/moons/addimage"),
                               id=id,
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/moons/addmoonimage/<int:id>", methods=["GET", "POST"])  # Add an image to the moon.
def add_moon_image(id):
    # Check if the user is logged in as admin.
    if admin:
        # If the id doesn't belong to the Moons table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Moons WHERE id=?", (id,)):
            abort(404)

        # Fetch the picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("image")
        if not image_data:
            return reject_input(f"/admin/moons/addimage/{id}", code_params.invalid_image)

        # Make the file name unique.
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Moons/{id}"))

        # Save the picture in the created folder.
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Moons/{id}/",
                                        image_name))

        # Update the pictures column in the Moons table.
        # The string is converted to a list, the new picture name is appended,
        # it is converted back to a string and put back in the database.
        pictures = execute_query("SELECT pictures FROM Moons WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Moons
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        # Redirect the user to the moon data page.
        return app.redirect(f"/moons/{id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/moons/deleteimage/<int:id>")  # Page to select an image to delete.
def delete_moon_image_page(id):
    # Check if the user is logged in as admin.
    if admin:
        # If the id doesn't belong to the Moons table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Moons WHERE id=?;", (id,)):
            abort(404)

        # Fetch the picture string for the moon, and convert it to a list.
        picture_data = execute_query("SELECT pictures FROM Moons WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)

        # Add all of the picture indexes to a list.
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
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/moons/deletemoonimage/<int:moon_id>/<int:picture_id>")  # Delete a picture.
def delete_moon_image(moon_id, picture_id):
    # Check if the user is logged in as admin.
    if admin:
        # If the id doesn't belong to the Moons table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Moons WHERE id=?", (moon_id,)):
            abort(404)

        # Fetch the picture string, convert it to a list.
        # Return a 404 error if the picture index doesn't exist.
        pictures = execute_query("SELECT pictures FROM Moons WHERE id=?", (moon_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)

        # Delete the picture from the moon folder, remove it from the list,
        # and re-add the string to the database.
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Moons/{moon_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Moons
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, moon_id))

        # Redirect the user to the moon data page
        return app.redirect(f"/moons/{moon_id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/entity/add")  # Page to add details for a new entity.
def add_entity_page():
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # The page needs to know the settings and moons
        # for the drop down options.
        setting_entries = execute_query("SELECT id, name FROM Setting;")
        moon_entries = execute_query("SELECT id, name FROM Moons;")

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("entities/entityadminadd.html",
                               settings=setting_entries,
                               moons=moon_entries,
                               title=get_title("/admin/entity/add"),
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/addentity", methods=["GET", "POST"])  # Add entity to database.
def add_entity():
    # Check if the user is logged in as admin.
    if admin:

        # Get all of the data from the HTML form.
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

        # if the entity is invincible, make the health values -1,
        # because entity page will display invincible if its health is -1.
        if invincible:
            sp_hp = -1
            mp_hp = -1

        # The strings need the new lines to be replaced with "\n",
        # so that the new lines can be stored properly in the database.
        bestiary = bestiary.replace("\n", "\\n")
        description = description.replace("\n", "\\n")

        # Fetch the header picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/entity/add", code_params.invalid_image)

        # Get the next usable id in the Entities table.
        # The base order is by id, so the last id + 1
        # will always be unique.
        entity_id = execute_query("SELECT id FROM Entities;")[-1][0] + 1

        # Create a folder with the entity id as the name in the Entities folder.
        # UPLOAD_FOLDER is the base directory of the images, being static/images.
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Entities/{entity_id}")

        # Save the picture in the created folder.
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Entities/{entity_id}/",
                                         header_picture_name))

        # This query inserts the entity data collected from the HTML form,
        # into a new entity.
        # pictures is kept blank, because they need to be added through
        # the website.
        execute_query('''
                      INSERT INTO Entities (name, danger, bestiary, setting,
                      fav_moon, sp_hp, mp_hp, power, max_spawned, description, header_picture, pictures)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (name, danger_rating, bestiary, setting, fav_moon, sp_hp,
                       mp_hp, power, max_spawned, description, header_picture_name, ""))

        # Redirect the user to the entity list
        return app.redirect("/entity")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/entity/delete")  # Page to select an entity to delete.
def delete_entity_page():
    # Check if the user is logged in as admin.
    if admin:

        # Gather the entity names and ids.
        entity_list = execute_query("SELECT id, name FROM Entities;")
        return render_template("entities/entityadmindelete.html",
                               entities=entity_list,
                               title=get_title("/admin/entity/delete"))
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/deleteentity/<int:id>")  # Delete selected entity.
def delete_entity(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Entities table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Entities WHERE id=?", (id,)):
            abort(404)

        # Delete the entity.
        execute_query("DELETE FROM Entities WHERE id=?;", (id,))

        # Delete every file in the entity's folder, and delete the folder.
        directory = f"{app.config["UPLOAD_FOLDER"]}/Entities/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)

        # Redirect the user to the entity list.
        return app.redirect("/entity")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/entity/addimage/<int:id>")  # Page to add entity image.
def add_entity_image_page(id):
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # If the id doesn't belong to the Entities table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Entities WHERE id=?", (id,)):
            abort(404)

        # Fetch the entity name.
        entity_name = execute_query("SELECT name FROM Entities WHERE id=?;", (id,))

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("entities/entityadminaddimage.html",
                               name=entity_name[0][0],
                               title=get_title("/admin/entity/addimage"),
                               id=id,
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/entity/addentityimage/<int:id>", methods=["GET", "POST"])  # Add entity image.
def add_entity_image(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Entities table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Entities WHERE id=?", (id,)):
            abort(404)

        # Fetch the picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Entities/{id}"))
        if not image_data:
            return reject_input(f"/admin/entity/addimage/{id}", code_params.invalid_image)

        # Save the picture to entity's folder.
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Entities/{id}/",
                                        image_name))

        # Update the pictures column in the Entities table.
        # The string is converted to a list, the new picture name is appended,
        # it is converted back to a string and put back in the database.
        pictures = execute_query("SELECT pictures FROM Entities WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Entities
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        # Redirect the user to the entity data page.
        return app.redirect(f"/entity/{id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/entity/deleteimage/<int:id>")  # Page for entity image deleting.
def delete_entity_image_page(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Entities table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Entities WHERE id=?;", (id,)):
            abort(404)

        # Fetch the picture string for the entity, and convert it to a list.
        picture_data = execute_query("SELECT pictures FROM Entities WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)

        # Add all of the picture indexes to a list.
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
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/entity/deleteentityimage/<int:entity_id>/<int:picture_id>")  # Delete entity image.
def delete_entity_image(entity_id, picture_id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Entities table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Entities WHERE id=?", (entity_id,)):
            abort(404)

        # Fetch the picture string, convert it to a list.
        # Return a 404 error if the picture index doesn't exist.
        pictures = execute_query("SELECT pictures FROM Entities WHERE id=?", (entity_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)

        # Delete the picture from the entity folder, remove it from the list,
        # and re-add the string to the database.
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Entities/{entity_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Entities
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, entity_id))

        # Redirect the user to the entity data page.
        return app.redirect(f"/entity/{entity_id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/tools/add")  # Page to add details for a new tool.
def add_tool_page():
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("tools/tooladminadd.html",
                               title=get_title("/admin/tools/add"),
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/addtool", methods=["GET", "POST"])  # Add tool to database
def add_tool():
    # Check if the user is logged in as admin.
    if admin:
        name = request.form.get("name")
        price = request.form.get("price")
        upgrade = request.form.get("upgrade")
        weight = request.form.get("weight")

        # The string needs the new lines to be replaced with "\n",
        # so that the new lines can be stored properly in the database.
        description = request.form.get("description").replace("\n", "\\n")

        # Checkboxes return "on" if they are ticked,
        # so it needs to be converted to a number.
        if upgrade:
            upgrade = 1
        else:
            upgrade = 0

        # Fetch the header picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/tools/add", code_params.invalid_image)

        # Get the next usable id in the Tools table.
        # The base order is by id, so the last id + 1
        # will always be unique.
        tool_id = execute_query("SELECT id FROM Tools;")[-1][0] + 1

        # Create a folder with the tool id as the name in the Tools folder.
        # UPLOAD_FOLDER is the base directory of the images, being static/images.
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Tools/{tool_id}")

        # Save the picture in the created folder.
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Tools/{tool_id}/",
                                         header_picture_name))

        # This query inserts the tool data collected from the HTML form,
        # into a new tool.
        # pictures is kept blank, because they need to be added through
        # the website.
        execute_query('''
                      INSERT INTO Tools
                      (name, price, description, upgrade, weight, header_picture, pictures)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (name, price, description, upgrade, weight, header_picture_name, ""))

        # Redirect the user to the tool list
        return app.redirect("/tools")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/tools/delete")  # Page to select a tool to delete.
def delete_tool_page():
    # Check if the user is logged in as admin.
    if admin:

        # Gather the tool names and ids.
        tool_list = execute_query("SELECT id, name FROM Tools;")
        return render_template("tools/tooladmindelete.html",
                               title=get_title("/admin/tools/delete"),
                               tools=tool_list)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/deletetool/<int:id>")  # Delete selected tool.
def delete_tool(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Tools table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Tools WHERE id=?", (id,)):
            abort(404)

        # Delete the entity.
        execute_query("DELETE FROM Tools WHERE id=?", (id,))

        # Delete every file in the tools's folder, and delete the folder.
        directory = f"{app.config["UPLOAD_FOLDER"]}/Tools/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)

        # Redirect the user to the tool list.
        return app.redirect("/tools")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/tools/addimage/<int:id>")  # Page to add tool images.
def add_tool_image_page(id):
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # If the id doesn't belong to the Entities table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Tools WHERE id=?", (id,)):
            abort(404)

        # Fetch the tool name.
        tool_name = execute_query("SELECT name FROM Tools WHERE id=?;", (id,))

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("tools/tooladminaddimage.html",
                               name=tool_name[0][0],
                               title=get_title("/admin/tools/addimage"),
                               id=id,
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/tools/addtoolimage/<int:id>", methods=["GET", "POST"])  # Add tool image.
def add_tool_image(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Tools table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Tools WHERE id=?", (id,)):
            abort(404)

        # Fetch the picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Tools/{id}"))
        if not image_data:
            return reject_input(f"/admin/tools/addimage/{id}", code_params.invalid_image)

        # Save the picture to tool's folder.
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Tools/{id}/",
                                        image_name))

        # Update the pictures column in the Tools table.
        # The string is converted to a list, the new picture name is appended,
        # it is converted back to a string and put back in the database.
        pictures = execute_query("SELECT pictures FROM Tools WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Tools
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))
        # Redirect the user to the tool data page.
        return app.redirect(f"/tools/{id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/tools/deleteimage/<int:id>")  # Page for tool image deleting.
def delete_tool_image_page(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Tools table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Tools WHERE id=?;", (id,)):
            abort(404)

        # Fetch the picture string for the tool, and convert it to a list.
        picture_data = execute_query("SELECT pictures FROM Tools WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)

        # Add all of the picture indexes to a list.
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
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/tools/deletetoolimage/<int:tool_id>/<int:picture_id>")  # Delete tool image.
def delete_tool_image(tool_id, picture_id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Tools table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Tools WHERE id=?", (tool_id,)):
            abort(404)

        # Fetch the picture string, convert it to a list.
        # Return a 404 error if the picture index doesn't exist.
        pictures = execute_query("SELECT pictures FROM Tools WHERE id=?", (tool_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)

        # Delete the picture from the tool folder, remove it from the list,
        # and re-add the string to the database.
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Tools/{tool_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Tools
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, tool_id))

        # Redirect the user to the tool data page.
        return app.redirect(f"/tools/{tool_id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/weathers/add")  # Page to add details for a new weather.
def add_weather_page():
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        moon_entries = execute_query("SELECT id, name FROM Moons")
        submit_message = fail_message
        fail_message = ""
        return render_template("weathers/weatheradminadd.html",
                               moons=moon_entries,
                               title=get_title("/admin/weathers/add"),
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/addweather", methods=["GET", "POST"])  # Add weather to database.
def add_weather():
    # Check if the user is logged in as admin.
    if admin:
        name = request.form.get("name")

        # The string needs the new lines to be replaced with "\n",
        # so that the new lines can be stored properly in the database.
        description = request.form.get("description").replace("\n", "\\n")

        # Gather all of the moons in the database.
        moon_entries = execute_query("SELECT id FROM Moons;")
        moon_list = []

        # This checks which moons in the database are selected in the HTML form.
        # This is done by storing the moon ids that match ticked checkboxes
        # in a list.
        for i in range(len(moon_entries)):
            if request.form.get("moon" + str(moon_entries[i][0])):
                moon_list.append(moon_entries[i][0])

        # Fetch the header picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/weathers/add", code_params.invalid_image)

        # Get the next usable id in the Weathers table.
        # The base order is by id, so the last id + 1
        # will always be unique.
        weather_id = execute_query("SELECT id FROM Weathers;")[-1][0] + 1

        # Create a folder with the weather id as the name in the Weathers folder.
        # UPLOAD_FOLDER is the base directory of the images, being static/images.
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{weather_id}")

        # Save the picture in the created folder.
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{weather_id}/",
                                         header_picture_name))

        # This query inserts the Weather data collected from the HTML form,
        # into a new weather.
        # pictures is kept blank, because they need to be added through
        # the website.
        execute_query('''
                      INSERT INTO Weathers (name, description, header_picture, pictures)
                      VALUES (?, ?, ?, ?)''',
                      (name, description, header_picture_name, ""))

        # Insert the bridging entries between the new weathers and the moons,
        # into the bridging table.
        for i in range(len(moon_list)):
            execute_query('''
                          INSERT INTO MoonWeathers (moon_id, weather_id)
                          VALUES (?, ?)''',
                          (moon_list[i], weather_id))

        # Redirect the user to the weather list.
        return app.redirect("/weathers")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/weathers/delete")  # Page to select a weather to delete.
def delete_weather_page():
    # Check if the user is logged in as admin.
    if admin:

        # Gather the weather names and ids.
        weather_list = execute_query("SELECT id, name FROM Weathers;")
        return render_template("weathers/weatheradmindelete.html",
                               title=get_title("/admin/weathers/delete"),
                               weathers=weather_list)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/deleteweather/<int:id>")  # Delete selected weather.
def delete_weather(id):
    # Check if the user is logged in as admin.
    if admin:
        # If the id does not belong in the Moons table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (id,)):
            abort(404)

        # Delete the weather and the moon-weather bridging entries,
        # that have the weather id.
        execute_query("DELETE FROM Weathers WHERE id=?", (id,))
        execute_query("DELETE FROM MoonWeathers WHERE weather_id=?", (id,))

        # Delete every file in the weather's folder, and delete the folder.
        directory = f"{app.config["UPLOAD_FOLDER"]}/Weathers/{id}"
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)

        # Redirect the user to the weather list.
        return app.redirect("/weathers")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/weathers/addimage/<int:id>")  # Page to add an image to a weather.
def add_weather_image_page(id):
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # If the id does not belong to the weathers table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (id,)):
            abort(404)

        # Get the name of the moon.
        weather_name = execute_query("SELECT name FROM Weathers WHERE id=?;", (id,))

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("weathers/weatheradminaddimage.html",
                               name=weather_name[0][0],
                               title=get_title("/admin/weathers/addimage"),
                               id=id,
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/weathers/addweatherimage/<int:id>", methods=["GET", "POST"])  # Add an image to the weather.
def add_weather_image(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Weathers table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (id,)):
            abort(404)

        # Fetch the picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("image")
        if not image_data:
            return reject_input(f"/admin/weathers/addimage/{id}", code_params.invalid_image)

        # Make the file name unique.
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{id}"))

        # Save the picture in the created folder.
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{id}/",
                                        image_name))

        # Update the pictures column in the Weathers table.
        # The string is converted to a list, the new picture name is appended,
        # it is converted back to a string and put back in the database.
        pictures = execute_query("SELECT pictures FROM Weathers WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Weathers
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        # Redirect the user to the weather data page.
        return app.redirect(f"/weathers/{id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/weathers/deleteimage/<int:id>")  # Page to select an image to delete.
def delete_weather_image_page(id):
    # Check if the user is logged in as admin.
    if admin:
        # If the id doesn't belong to the Weathers table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Weathers WHERE id=?;", (id,)):
            abort(404)

        # Fetch the picture string for the weather, and convert it to a list.
        picture_data = execute_query("SELECT pictures FROM Weathers WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)

        # Add all of the picture indexes to a list.
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
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/weathers/deleteweatherimage/<int:weather_id>/<int:picture_id>")  # Delete a picture
def delete_weather_image(weather_id, picture_id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Weathers table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Weathers WHERE id=?", (weather_id,)):
            abort(404)

        # Fetch the picture string, convert it to a list.
        # Return a 404 error if the picture index doesn't exist.
        pictures = execute_query("SELECT pictures FROM Weathers WHERE id=?", (weather_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)

        # Delete the picture from the weathers folder, remove it from the list,
        # and re-add the string to the database.
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Weathers/{weather_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Weathers
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, weather_id))

        # Redirect the user to the weather data page
        return app.redirect(f"/weathers/{weather_id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/interiors/add")  # Page to add details for a new interior.
def add_interior_page():
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("interiors/interioradminadd.html",
                               title=get_title("/admin/interiors/add"),
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/addinterior", methods=["GET", "POST"])  # Add interior to database.
def add_interior():
    # Check if the user is logged in as admin.
    if admin:

        # Get all of the data from the HTML form.
        name = request.form.get("name")

        # This string needs the new lines to be replaced with "\n",
        # so that the new lines can be stored properly in the database.
        description = request.form.get("description").replace("\n", "\\n")

        # Fetch the header picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("header_picture")
        if image_data:
            header_picture = image_data[0]
            header_picture_name = image_data[1]
        else:
            return reject_input("/admin/interiors/add", code_params.invalid_image)

        # Get the next usable id in the Interiors table.
        # The base order is by id, so the last id + 1
        # will always be unique.
        interior_id = execute_query("SELECT id FROM Interiors;")[-1][0] + 1

        # Create a folder with the interior id as the name in the Interiors folder.
        # UPLOAD_FOLDER is the base directory of the images, being static/images.
        os.mkdir(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{interior_id}")

        # Save the picture in the created folder.
        header_picture.save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{interior_id}/",
                                         header_picture_name))

        # This query inserts the interior data collected from the HTML form,
        # into a new interior.
        # pictures is kept blank, because they need to be added through
        # the website.
        execute_query('''
                      INSERT INTO Interiors (name, description, header_picture, pictures)
                      VALUES (?, ?, ?, ?)''',
                      (name, description, header_picture_name, ""))
        return app.redirect("/interiors")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/interiors/delete")  # Page to select an interior to delete.
def delete_interior_page():
    # Check if the user is logged in as admin.
    if admin:

        # Gather the entity names and ids.
        interior_list = execute_query("SELECT id, name FROM Interiors WHERE NOT id=1;")
        return render_template("interiors/interioradmindelete.html",
                               title=get_title("/admin/interiors/delete"),
                               interiors=interior_list)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/deleteinterior/<int:id>")  # Delete selected interior.
def delete_interior(id):
    # Check if the user is logged in as admin.
    if admin:

        # If the id doesn't belong to the Interiors table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (id,)):
            abort(404)

        # The interior "N/A" has an id of 1,
        # and it isn't supposed to be deleted,
        # so if the id is 1, a 404 error will be returned.
        if not id == 1:
            # Delete the interior.
            execute_query("DELETE FROM Interiors WHERE id=?", (id,))
            # Delete every file in the interior's folder, and delete the folder.
            directory = f"{app.config["UPLOAD_FOLDER"]}/Interiors/{id}"
            for file in os.listdir(directory):
                os.remove(f"{directory}/{file}")
            os.rmdir(directory)
            # Redirect the user to the interior list.
            return app.redirect("/interiors")
        else:
            abort(404)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/interiors/addimage/<int:id>")  # Page to add interior image.
def add_interior_image_page(id):
    # Check if the user is logged in as admin.
    if admin:
        global fail_message

        # Return a 404 error if the id is 1,
        # because the interior shouldn't be edited.
        if id == 1:
            abort(404)

        # If the id doesn't belong to the Entities table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (id,)):
            abort(404)

        # Fetch the interior name.
        interior_name = execute_query("SELECT name FROM Interiors WHERE id=?;", (id,))

        # The fail message should only be displayed once,
        # so the current fail message is stored, and then reset.
        submit_message = fail_message
        fail_message = ""
        return render_template("interiors/interioradminaddimage.html",
                               name=interior_name[0][0],
                               title=get_title("/admin/interiors/addimage"),
                               id=id,
                               message=submit_message)
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/interiors/addinteriorimage/<int:id>", methods=["GET", "POST"])  # Add entity image.
def add_interior_image(id):
    # Check if the user is logged in as admin.
    if admin:

        # Return a 404 error if the id is 1,
        # because the interior shouldn't be edited.
        if id == 1:
            abort(404)

        # If the id doesn't belong to the Interiors table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (id,)):
            abort(404)

        # Fetch the picture data,
        # and reject the submission if it is invalid.
        image_data = process_image("image")
        image_name = get_image_name(image_data[1],
                                    os.listdir(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{id}"))
        if not image_data:
            return reject_input(f"/admin/interiors/addimage/{id}", code_params.invalid_image)

        # Save the picture to interiors's folder.
        image_data[0].save(os.path.join(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{id}/",
                                        image_name))

        # Update the pictures column in the Interiors table.
        # The string is converted to a list, the new picture name is appended,
        # it is converted back to a string and put back in the database.
        pictures = execute_query("SELECT pictures FROM Interiors WHERE id=?", (id,))[0][0]
        pictures = set_picture_list(pictures)
        pictures.append(image_name)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Interiors
                      SET pictures = ?
                      WHERE id = ?;''', (pictures, id))

        # Redirect the user to the entity data page.
        return app.redirect(f"/interiors/{id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/interiors/deleteimage/<int:id>")
def delete_interior_image_page(id):
    # Check if the user is logged in as admin.
    if admin:

        # Return a 404 error if the id is 1,
        # because the interior shouldn't be edited.
        if id == 1:
            abort(404)

        # If the id doesn't belong to the Interiors table,
        # return a 404 error.
        if not execute_query("SELECT id FROM Interiors WHERE id=?;", (id,)):
            abort(404)

        # Fetch the picture string for the interior, and convert it to a list.
        picture_data = execute_query("SELECT pictures FROM Interiors WHERE id=?;", (id,))
        picture_data = set_picture_list(picture_data[0][0])
        picture_id = []
        picture_count = len(picture_data)

        # Add all of the picture indexes to a list.
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
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.route("/admin/interiors/deleteinteriorimage/<int:interior_id>/<int:picture_id>")
def delete_interior_image(interior_id, picture_id):
    # Check if the user is logged in as admin.
    if admin:

        # Return a 404 error if the id is 1,
        # because the interior shouldn't be edited.
        if interior_id == 1:
            abort(404)

        # Fetch the picture string, convert it to a list.
        # Return a 404 error if the picture index doesn't exist.
        if not execute_query("SELECT id FROM Interiors WHERE id=?", (interior_id,)):
            abort(404)
        pictures = execute_query("SELECT pictures FROM Interiors WHERE id=?", (interior_id,))
        pictures = set_picture_list(pictures[0][0])
        if picture_id < 0 or picture_id >= len(pictures):
            abort(404)

        # Delete the picture from the interior folder, remove it from the list,
        # and re-add the string to the database.
        os.remove(f"{app.config["UPLOAD_FOLDER"]}/Interiors/{interior_id}/{pictures[picture_id]}")
        pictures.pop(picture_id)
        pictures = " ".join(pictures)
        execute_query('''
                      UPDATE Interiors
                      SET pictures = ?
                      WHERE id=?''',
                      (pictures, interior_id))

        # Redirect the user to the interior data page.
        return app.redirect(f"/interiors/{interior_id}")
    else:
        # Redirect the user to a page denying admin access.
        return admin_perms_denied()


@app.errorhandler(404)  # Page for 404 errors.
def error404(e):
    # Redirect the user to the error page with a 404 error code.
    return push_error(404, e)


@app.errorhandler(500)  # Page for 500 errors.
def error500(e):
    # Redirect the user to the error page with a 500 error code.
    return push_error(500, e)


# Run the code if it is the file being run.
if __name__ == "__main__":
    app.run(debug=True)

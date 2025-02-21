from flask import Flask, render_template
import sqlite3
app = Flask(__name__)

DATABASE = "database.db"

def ExeQuery(query, params=()):
    with sqlite3.connect(DATABASE) as db:
        return db.cursor().execute(query, params).fetchall()

@app.route("/")
def home():
    return render_template("main.html")

if __name__ == "__main__":
    app.run(debug=True)
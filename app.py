from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "super_secret_key_123"


# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "admin@taskflow.com" and password == "admin123":
            session["user"] = email
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "error")

    return render_template("auth.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    tasks = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()

    return render_template("dashboard.html", tasks=tasks)


# ---------------- UPDATE TASK ----------------
@app.route("/update-task", methods=["POST"])
def update_task():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET title = ?, description = ?, status = ?
        WHERE id = ?
    """, (
        data["title"],
        data["description"],
        data["status"],
        data["id"]
    ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

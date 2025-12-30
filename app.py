from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "super_secret_key_123"  # Change in production


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Temporary credentials (replace with DB later)
        if email == "admin@vektora.com" and password == "admin123":
            session["user"] = email
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")

    return render_template("auth.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    projects = [
        {
            "title": "Prototipi Mobile App",
            "status": "todo",
            "priority": "Medium",
            "description": "Evaluate and improve performance",
            "members": 2
        },
        {
            "title": "YellyBox Project",
            "status": "progress",
            "priority": "Low",
            "description": "Collaboration platform",
            "members": 3
        },
        {
            "title": "Minicam Exploration",
            "status": "progress",
            "priority": "High",
            "description": "Explore camera optimization",
            "members": 2
        },
        {
            "title": "Mantraman Branding",
            "status": "complete",
            "priority": "High",
            "description": "Brand identity system",
            "members": 4
        }
    ]

    return render_template("dashboard.html", projects=projects)


# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "taskflow_secret_key"

# ================= DATABASE CONNECTION =================
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Projects (✅ added status)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT CHECK(status IN ('todo','in_progress','done')) DEFAULT 'todo',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Tasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        status TEXT CHECK(status IN ('todo','in_progress','done')) DEFAULT 'todo',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    conn.commit()
    conn.close()

# ================= AUTH =================
@app.route('/')
def home():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.form['password'] != request.form['confirm_password']:
            return "Passwords do not match"

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (
                    request.form['name'],
                    request.form['email'],
                    generate_password_hash(request.form['password'])
                )
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return "Email already exists"
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (request.form['email'],)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))

        return "Invalid credentials"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()

    total_projects = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    total_tasks = conn.execute("""
        SELECT COUNT(*) FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ?
    """, (user_id,)).fetchone()[0]

    in_progress = conn.execute("""
        SELECT COUNT(*) FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ? AND tasks.status='in_progress'
    """, (user_id,)).fetchone()[0]

    completed = conn.execute("""
        SELECT COUNT(*) FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ? AND tasks.status='done'
    """, (user_id,)).fetchone()[0]

    recent_tasks = conn.execute("""
        SELECT tasks.title, tasks.status
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ?
        ORDER BY tasks.created_at DESC
        LIMIT 5
    """, (user_id,)).fetchall()

    weekly_data = [0]*7
    rows = conn.execute("""
        SELECT strftime('%w', tasks.created_at) as day, COUNT(*) as count
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ? AND tasks.status='done'
        GROUP BY day
    """, (user_id,)).fetchall()

    for r in rows:
        weekly_data[int(r['day'])] = r['count']

    conn.close()

    return render_template(
        "dashboard.html",
        name=session['user_name'],
        total_projects=total_projects,
        total_tasks=total_tasks,
        in_progress=in_progress,
        completed=completed,
        weekly_data=weekly_data,
        recent_tasks=recent_tasks
    )

# ================= PROJECTS =================
@app.route("/projects")
def projects():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    projects = conn.execute("""
        SELECT p.*, COUNT(t.id) as task_count
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("projects.html", name=session["user_name"], projects=projects)

@app.route("/projects/create", methods=["POST"])
def create_project():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute("""
        INSERT INTO projects (user_id, title, description, status)
        VALUES (?, ?, ?, 'todo')
    """, (
        session["user_id"],
        request.form["title"],
        request.form.get["description"]
    ))
    conn.commit()
    conn.close()

    return redirect(url_for("projects"))

@app.route("/projects/<int:project_id>")
def project_details(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    project = conn.execute("""
        SELECT * FROM projects
        WHERE id = ? AND user_id = ?
    """, (project_id, session["user_id"])).fetchone()

    if not project:
        conn.close()
        return "Project not found", 404

    tasks = conn.execute("""
        SELECT * FROM tasks
        WHERE project_id = ?
        ORDER BY created_at DESC
    """, (project_id,)).fetchall()

    conn.close()

    return render_template(
        "project_details.html",
        name=session["user_name"],
        project=project,
        tasks=tasks
    )

@app.route("/projects/<int:project_id>/delete")
def delete_project(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    conn.execute(
        "DELETE FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("projects"))

@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    project = conn.execute(
        "SELECT * FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session["user_id"])
    ).fetchone()

    if not project:
        conn.close()
        return "Project not found", 404

    if request.method == "POST":
        conn.execute("""
            UPDATE projects
            SET title = ?, description = ?
            WHERE id = ? AND user_id = ?
        """, (
            request.form["title"],
            request.form["description"],
            project_id,
            session["user_id"]
        ))
        conn.commit()
        conn.close()
        return redirect(url_for("project_details", project_id=project_id))

    conn.close()
    return render_template(
        "edit_project.html",
        project=project,
        name=session["user_name"]
    )


# ================= RUN =================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

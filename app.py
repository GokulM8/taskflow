from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, date

app = Flask(__name__)
app.secret_key = "taskflow_secret_key"

# 🔐 Session stability
app.config["SESSION_PERMANENT"] = True
app.permanent_session_lifetime = timedelta(days=1)

# ================= DATABASE CONNECTION =================
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ================= PROJECT HELPERS =================
def get_project(project_id, user_id):
    conn = get_db()
    project = conn.execute(
        "SELECT * FROM projects WHERE id = ? AND user_id = ?",
        (project_id, user_id)
    ).fetchone()
    conn.close()
    return project

def get_tasks_by_project(project_id):
    conn = get_db()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,)
    ).fetchall()
    conn.close()
    return tasks

# ================= ACTIVITY LOG HELPERS =================
def log_activity(user_id, action, task_id=None):
    conn = get_db()
    conn.execute("""
        INSERT INTO activity_logs (user_id, task_id, action)
        VALUES (?, ?, ?)
    """, (user_id, task_id, action))
    conn.commit()
    conn.close()


def get_recent_activity(user_id, limit=5):
    conn = get_db()
    logs = conn.execute("""
        SELECT action, created_at
        FROM activity_logs
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return logs


# ================= DATABASE INIT =================
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT CHECK(status IN ('todo','in_progress','completed')) DEFAULT 'todo',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    # ✅ ENHANCED TASKS TABLE (Best of both codes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT CHECK(status IN ('todo','in_progress','completed')) DEFAULT 'todo',
        priority TEXT CHECK(priority IN ('low','medium','high')) DEFAULT 'medium',
        due_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER,
        action TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    )
    """)

    
    conn.commit()
    conn.close()

# ================= AUTH =================
@app.route("/")
def home():
    return redirect(url_for("dashboard")) if "user_id" in session else redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if request.form["password"] != request.form["confirm_password"]:
            flash("Passwords do not match", "error")
            return redirect(url_for("register"))
        
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
            """, (
                request.form["name"],
                request.form["email"],
                generate_password_hash(request.form["password"])
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
            return redirect(url_for("register"))
        finally:
            conn.close()
        
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user["password"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for("login"))
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    conn = get_db()
    
    total_projects = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    
    total_tasks = conn.execute("""
        SELECT COUNT(*)
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ?
    """, (user_id,)).fetchone()[0]
    
    in_progress = conn.execute("""
        SELECT COUNT(*)
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ? AND tasks.status='in_progress'
    """, (user_id,)).fetchone()[0]
    
    completed = conn.execute("""
        SELECT COUNT(*)
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ? AND tasks.status='completed'
    """, (user_id,)).fetchone()[0]
    
    recent_tasks = conn.execute("""
        SELECT tasks.title, tasks.status, tasks.priority, tasks.due_date, tasks.created_at
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ?
        ORDER BY tasks.created_at DESC
        LIMIT 5
    """, (user_id,)).fetchall()
    
    # ✅ WEEKLY DATA
    weekly_data = [0] * 7
    rows = conn.execute("""
        SELECT strftime('%w', tasks.created_at) as day, COUNT(*) as count
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ? AND tasks.status='completed'
        GROUP BY day
    """, (user_id,)).fetchall()
    
    for r in rows:
        weekly_data[int(r["day"])] = r["count"]
    
    conn.close()
    
    return render_template(
        "dashboard.html",
        name=session["user_name"],
        total_projects=total_projects,
        total_tasks=total_tasks,
        in_progress=in_progress,
        completed=completed,
        weekly_data=weekly_data,
        tasks=recent_tasks,
        today_date=date.today().isoformat()
    )

# ================= PROJECTS =================
@app.route("/projects")
def projects():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    projects = conn.execute("""
        SELECT p.*, COUNT(t.id) AS task_count
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.created_at DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    
    return render_template("projects.html",
                           name=session["user_name"],
                           projects=projects)

@app.route("/projects/create", methods=["POST"])
def create_project():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    title = request.form.get("title")
    description = request.form.get("description")
    
    if not title:
        flash("Project title is required", "error")
        return redirect(url_for("projects"))
    
    conn = get_db()
    conn.execute("""
        INSERT INTO projects (user_id, title, description, status)
        VALUES (?, ?, ?, 'todo')
    """, (session["user_id"], title, description))
    conn.commit()
    conn.close()
    
    flash("Project created successfully", "success")
    return redirect(url_for("projects"))

@app.route("/projects/<int:project_id>")
def project_dashboard(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    project = get_project(project_id, session["user_id"])
    if project is None:
        flash("Project not found", "error")
        return redirect(url_for("projects"))
    
    tasks = get_tasks_by_project(project_id)
    
    # ✅ Enhanced stats with priority breakdown
    total_tasks = len(tasks)
    completed_tasks = sum(t["status"] == "completed" for t in tasks)

    progress = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    stats = {
        "total": total_tasks,
        "completed": completed_tasks,
        "in_progress": sum(t["status"] == "in_progress" for t in tasks),
        "todo": sum(t["status"] == "todo" for t in tasks),
        "progress": progress
    }
    
    return render_template(
        "project_dashboard.html",
        name=session["user_name"],
        project=project,
        tasks=tasks,
        stats=stats,
        today_date=date.today().isoformat()
    )

# ================= EDIT PROJECT =================
@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    project = conn.execute(
        "SELECT * FROM projects WHERE id = ? AND user_id = ?",
        (project_id, session["user_id"])
    ).fetchone()
    
    if project is None:
        conn.close()
        flash("Project not found", "error")
        return redirect(url_for("projects"))
    
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        status = request.form["status"]
        
        if not title:
            flash("Project title is required", "error")
            return redirect(url_for("edit_project", project_id=project_id))
        
        conn.execute("""
            UPDATE projects
            SET title = ?, description = ?, status = ?
            WHERE id = ? AND user_id = ?
        """, (title, description, status, project_id, session["user_id"]))
        conn.commit()
        conn.close()
        
        flash("Project updated successfully", "success")
        return redirect(url_for("project_dashboard", project_id=project_id))
    
    conn.close()
    return render_template(
        "edit_project.html",
        name=session["user_name"],
        project=project
    )

@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    project = get_project(project_id, session["user_id"])
    if project is None:
        flash("Project not found", "error")
        return redirect(url_for("projects"))
    
    conn = get_db()
    # Delete all tasks in the project first
    conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
    # Then delete the project
    conn.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", 
                 (project_id, session["user_id"]))
    conn.commit()
    conn.close()
    
    flash("Project deleted successfully", "success")
    return redirect(url_for("projects"))

# ================= TASK CRUD (ENHANCED) =================
@app.route("/projects/<int:project_id>/tasks/create", methods=["POST"])
def create_task(project_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    project = get_project(project_id, session["user_id"])
    if project is None:
        flash("Project not found", "error")
        return redirect(url_for("projects"))

    title = request.form.get("title")
    if not title:
        flash("Task title is required", "error")
        return redirect(url_for("project_dashboard", project_id=project_id))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (project_id, title, description, priority, due_date, status)
        VALUES (?, ?, ?, ?, ?, 'todo')
    """, (
        project_id,
        title,
        request.form.get("description", ""),
        request.form.get("priority", "medium"),
        request.form.get("due_date", "")
    ))

    task_id = cursor.lastrowid   # 🔵 ADDED
    conn.commit()
    conn.close()

    log_activity(session["user_id"], "Task created", task_id)  # 🔵 ADDED

    flash("Task created successfully", "success")
    return redirect(url_for("project_dashboard", project_id=project_id))


@app.route("/tasks/<int:task_id>/update", methods=["POST"])
def update_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    task = conn.execute("""
        SELECT tasks.*, projects.user_id
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE tasks.id = ?
    """, (task_id,)).fetchone()

    if task is None or task["user_id"] != session["user_id"]:
        conn.close()
        flash("Task not found", "error")
        return redirect(url_for("projects"))

    conn.execute("""
        UPDATE tasks
        SET title = ?, description = ?, status = ?, priority = ?, due_date = ?
        WHERE id = ?
    """, (
        request.form.get("title"),
        request.form.get("description", ""),
        request.form.get("status"),
        request.form.get("priority"),
        request.form.get("due_date", ""),
        task_id
    ))

    conn.commit()
    conn.close()

    log_activity(session["user_id"], "Task updated", task_id)  # 🔵 ADDED

    flash("Task updated successfully", "success")
    return redirect(request.referrer or url_for("projects"))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    task = conn.execute("""
        SELECT tasks.*, projects.user_id
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE tasks.id = ?
    """, (task_id,)).fetchone()

    if task is None or task["user_id"] != session["user_id"]:
        conn.close()
        flash("Task not found", "error")
        return redirect(url_for("projects"))

    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    log_activity(session["user_id"], "Task deleted", task_id)  # 🔵 ADDED

    flash("Task deleted successfully", "success")
    return redirect(request.referrer or url_for("projects"))


# ================= TASKS PAGE =================
@app.route("/tasks")
def tasks():
    if "user_id" not in session:
        return redirect(url_for("login"))

    status = request.args.get("status")
    priority = request.args.get("priority")
    search = request.args.get("search")

    query = """
        SELECT tasks.*, projects.title as project_title
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.user_id = ?
    """
    params = [session["user_id"]]

    if status:
        query += " AND tasks.status = ?"
        params.append(status)

    if priority:
        query += " AND tasks.priority = ?"
        params.append(priority)

    if search:
        query += " AND tasks.title LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY tasks.created_at DESC"

    conn = get_db()
    all_tasks = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "tasks.html",
        name=session["user_name"],
        tasks=all_tasks,
        status_filter=status,
        priority_filter=priority,
        search_query=search
    )

# ================= RUN =================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
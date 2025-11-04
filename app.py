from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
from werkzeug.utils import secure_filename
import mysql.connector
from agents.sql_agent import AgentState
# from agents.langgraph_app import ai_app
from agents.agentic_workflow import ai_app
from tools.db_tools import create_temp_mysql_db_from_dump, drop_temp_mysql_db

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"sql"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

schemas = {}
db_cache = {}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    sql_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".sql")]
    return render_template("index.html", sql_files=sql_files)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        flash("No file uploaded.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        try:
            db_config = create_temp_mysql_db_from_dump(file_path)
            db_cache[filename] = db_config
            schema_info = {}

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
            """, (db_config["database"],))
            rows = cursor.fetchall()
            for table, column, col_type in rows:
                schema_info.setdefault(table, []).append(f"{column} ({col_type})")
            conn.close()

            schemas[filename] = {
                "filename": filename,
                "schema": schema_info,
                "db_config": db_config
            }

            flash(f"File '{filename}' uploaded and schema loaded successfully.", "success")
        except Exception as e:
            flash(f"Error processing file: {str(e)}", "error")

        return redirect(url_for("index"))

    flash("Invalid file type. Only .sql allowed.", "error")
    return redirect(url_for("index"))

@app.route("/load_schema", methods=["POST"])
def load_schema():
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": f"File '{filename}' not found."}), 404

    db_config = db_cache.get(filename)
    if not db_config:
        db_config = create_temp_mysql_db_from_dump(file_path)
        db_cache[filename] = db_config

    schema_info = {}
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
    """, (db_config["database"],))
    rows = cursor.fetchall()
    for table, column, col_type in rows:
        schema_info.setdefault(table, []).append(f"{column} ({col_type})")
    conn.close()

    schemas[filename] = {
        "filename": filename,
        "schema": schema_info,
        "db_config": db_config
    }

    return jsonify({"message": f"Loaded schema for {filename}", "schema": schema_info})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data.get("query", "")
    filename = data.get("filename")

    if not query:
        return jsonify({"error": "Missing query"}), 400
    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    schema_entry = schemas.get(filename)
    if not schema_entry:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if not os.path.exists(file_path):
            return jsonify({"error": f"File '{filename}' not found."}), 404

        db_config = db_cache.get(filename)
        if not db_config:
            db_config = create_temp_mysql_db_from_dump(file_path)
            db_cache[filename] = db_config

        schema_info = {}
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
        """, (db_config["database"],))
        rows = cursor.fetchall()
        for table, column, col_type in rows:
            schema_info.setdefault(table, []).append(f"{column} ({col_type})")
        conn.close()

        schemas[filename] = {
            "filename": filename,
            "schema": schema_info,
            "db_config": db_config
        }
        schema_entry = schemas[filename]

    initial_state = AgentState(
        user_query=query,
        schema=schema_entry,
        db_config=schema_entry.get("db_config")
    )
    result_state = ai_app.invoke(initial_state)

    return jsonify({
        "dataset": filename,
        "sql": result_state.get("generated_sql"),
        "result": result_state.get("result"),
        "answer": result_state.get("answer")
    })

@app.route("/cleanup_db", methods=["POST"])
def cleanup_db():
    for filename, cfg in list(db_cache.items()):
        try:
            drop_temp_mysql_db(cfg)
        except Exception as e:
            print(f"Failed to drop {filename}: {e}")
    db_cache.clear()
    return jsonify({"message": "All temporary databases dropped."})

@app.route("/delete_dataset", methods=["POST"])
def delete_dataset():
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db_cfg = db_cache.get(filename)
    if db_cfg:
        try:
            drop_temp_mysql_db(db_cfg)
            del db_cache[filename]
        except Exception as e:
            print(f"Error dropping DB for {filename}: {e}")

    schemas.pop(filename, None)
    return jsonify({"message": f"{filename} and its temporary database deleted successfully."})

if __name__ == "__main__":
    app.run(debug=True)

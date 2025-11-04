import os
import tempfile
import mysql.connector
import subprocess
import uuid
import re
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USERNAME")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_PORT = os.getenv("MYSQL_PORT")


def create_temp_mysql_db_from_dump(dump_file_path: str) -> dict:
    """
    Creates or reuses a MySQL database named after the uploaded .sql file.
    Loads the dump into it (overwrites any old data if present).
    Returns connection info.
    """
    # ✅ Use the uploaded filename (without .sql) as DB name
    base_name = os.path.basename(dump_file_path)
    db_name = os.path.splitext(base_name)[0]
    db_name = re.sub(r"[^0-9a-zA-Z_]", "_", db_name)  # sanitize name

    # Step 1: Connect to MySQL
    conn = mysql.connector.connect(
        host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, port=MYSQL_PORT
    )
    cursor = conn.cursor()

    # Step 2: Check if DB already exists
    cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
    db_exists = cursor.fetchone()

    if not db_exists:
        print(f"📘 Creating new database: {db_name}")
        cursor.execute(f"CREATE DATABASE `{db_name}`")
        conn.commit()
    else:
        print(f"♻️ Database {db_name} already exists — reusing it.")

    cursor.close()
    conn.close()

    # Step 3: Load the dump into the DB
    #    Remove any "USE <db>;" lines so it loads into our db_name
    with open(dump_file_path, "r", encoding="utf-8", errors="ignore") as f:
        dump_content = f.read()

    dump_content = re.sub(r"(?i)USE\s+`?\w+`?;", "", dump_content)

    # Write to a temporary file for clean import
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as temp_f:
        temp_f.write(dump_content)
        temp_path = temp_f.name

    cmd = [
        "mysql",
        f"--host={MYSQL_HOST}",
        f"--user={MYSQL_USER}",
        f"--password={MYSQL_PASSWORD}",
        f"--port={MYSQL_PORT}",
        db_name,
    ]

    subprocess.run(
        cmd, stdin=open(temp_path, "r", encoding="utf-8", errors="ignore"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    os.remove(temp_path)

    return {
        "host": MYSQL_HOST,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "port": MYSQL_PORT,
        "database": db_name,
    }


def drop_temp_mysql_db(mysql_config: dict):
    """
    Drops the MySQL database created for an uploaded .sql file.
    """
    db_name = mysql_config.get("database")
    if not db_name:
        return

    print(f"🗑️ Dropping database: {db_name}")
    conn = mysql.connector.connect(
        host=mysql_config["host"],
        user=mysql_config["user"],
        password=mysql_config["password"],
        port=mysql_config["port"],
    )
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
    conn.commit()
    cursor.close()
    conn.close()

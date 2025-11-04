# tools/query_executor.py
import mysql.connector

def execute_sql_query(db_config: dict, sql: str):
    """
    Executes an SQL query on a temporary MySQL database.
    db_config: {
        "host": str,
        "user": str,
        "password": str,
        "database": str
    }
    """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)

        # Fetch rows only for SELECT-type queries
        if cursor.with_rows:
            rows = cursor.fetchall()
            result = rows
        else:
            conn.commit()
            result = [{"message": f"{cursor.rowcount} rows affected."}]

        conn.close()
        return result
    except Exception as e:
        return [{"error": str(e)}]


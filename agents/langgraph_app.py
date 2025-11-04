# a langgraph workflow without tools uses, runs entirely on single call as a sequential workflow.

import os
import mysql.connector
from flask import current_app
from langgraph.graph import StateGraph
from agents.sql_agent import AgentState
from tools.db_tools import create_temp_mysql_db_from_dump, drop_temp_mysql_db
from tools.query_generator import generate_sql_chain
from tools.data_reasoner import reason_chain


# === Utility ===
def update_state(state: AgentState, **kwargs) -> AgentState:
    """Return a new AgentState dict with merged updates."""
    new_state = dict(state)
    new_state.update(kwargs)
    return new_state


# === Nodes ===
def node_create_db(state: AgentState) -> AgentState:
    upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
    file_path = os.path.join(upload_dir, state["schema"]["filename"])

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Uploaded SQL file not found: {file_path}")

    db_config = create_temp_mysql_db_from_dump(file_path)
    return update_state(state, db_config=db_config)


def node_generate_sql(state: AgentState) -> AgentState:
    sql = generate_sql_chain.invoke({
        "schema": state["schema"].get("schema", ""),
        "question": state["user_query"]
    })
    return update_state(state, generated_sql=sql)


def node_execute_sql(state: AgentState) -> AgentState:
    try:
        conn = mysql.connector.connect(**state["db_config"])
        cursor = conn.cursor(dictionary=True)
        cursor.execute(state["generated_sql"])
        rows = cursor.fetchall()
        conn.close()
        return update_state(state, result=rows, error=None)
    except Exception as e:
        return update_state(state, result=None, error=str(e))


def node_fix_sql(state: AgentState) -> AgentState:
    if not state.get("error"):
        return state

    fix_prompt = f"""
    The SQL query failed with the following error:
    {state['error']}

    Original query:
    {state['generated_sql']}

    Schema:
    {state['schema']}

    User question:
    {state['user_query']}

    Return ONLY the corrected SQL query.
    """

    fixed_sql = generate_sql_chain.invoke({
        "schema": state["schema"].get("schema", ""),
        "question": fix_prompt
    })

    retry_count = state.get("retry_count", 0) + 1
    if retry_count > 2:
        return update_state(state, error="Too many retries", retry_count=retry_count)

    return update_state(state, generated_sql=fixed_sql, error=None, retry_count=retry_count)


def node_reason(state: AgentState) -> AgentState:
    answer = reason_chain.invoke({
        "question": state["user_query"],
        "result": state["result"]
    })

    # optional cleanup: drop temp MySQL DB
    try:
        drop_temp_mysql_db(state["db_config"]["database"])
    except Exception as e:
        print(f"Warning: failed to drop temp DB - {e}")

    return update_state(state, answer=answer)


def has_error(state: AgentState) -> bool:
    return bool(state.get("error"))


# === Graph Setup ===
graph = StateGraph(AgentState)
graph.add_node("create_db", node_create_db)
graph.add_node("generate_sql", node_generate_sql)
graph.add_node("execute_sql", node_execute_sql)
graph.add_node("fix_sql", node_fix_sql)
graph.add_node("reason", node_reason)

graph.set_entry_point("create_db")
graph.add_edge("create_db", "generate_sql")
graph.add_edge("generate_sql", "execute_sql")

graph.add_conditional_edges(
    "execute_sql",
    lambda state: "fix_sql" if has_error(state) else "reason"
)

graph.add_edge("fix_sql", "execute_sql")

ai_app = graph.compile()

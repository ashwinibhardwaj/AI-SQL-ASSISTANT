import os
import mysql.connector
from flask import current_app
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from agents.sql_agent import AgentState

# === Local tools ===
from tools.db_tools import create_temp_mysql_db_from_dump, drop_temp_mysql_db
from tools.query_generator import generate_sql_chain
from tools.data_reasoner import reason_chain


api_key = os.getenv("HUGGINGFACEHUB_ACCESS_TOCKEN")

llm_endpoint = HuggingFaceEndpoint(
    repo_id="openai/gpt-oss-20b",
    task="text-generation",
    huggingfacehub_api_token=api_key
)
llm = ChatHuggingFace(llm=llm_endpoint)



# nodes definition
def node_create_db(state: AgentState) -> AgentState:
    """Create temporary DB from uploaded SQL file."""
    upload_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
    file_path = os.path.join(upload_dir, state["schema"]["filename"])

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Uploaded SQL file not found: {file_path}")

    db_config = create_temp_mysql_db_from_dump(file_path)
    new_state = dict(state)
    new_state["db_config"] = db_config
    return new_state


def node_generate_sql(state: AgentState) -> AgentState:
    """Generate SQL from schema and natural question."""
    sql = generate_sql_chain.invoke({
        "schema": state["schema"].get("schema", ""),
        "question": state["user_query"]
    })
    new_state = dict(state)
    new_state["generated_sql"] = sql
    return new_state


def node_execute_sql(state: AgentState) -> AgentState:
    """Execute generated SQL query and store results."""
    try:
        conn = mysql.connector.connect(**state["db_config"])
        cursor = conn.cursor(dictionary=True)
        cursor.execute(state["generated_sql"])
        rows = cursor.fetchall()
        conn.close()
        new_state = dict(state)
        new_state["result"] = rows
        new_state["error"] = None
        return new_state
    except Exception as e:
        new_state = dict(state)
        new_state["error"] = str(e)
        new_state["result"] = None
        return new_state


def node_fix_sql(state: AgentState) -> AgentState:
    """Fix invalid SQL when execution fails."""
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

    retry_count = (state.get("retry_count") or 0) + 1
    if retry_count > 2:
        new_state = dict(state)
        new_state["error"] = "Too many retries"
        new_state["retry_count"] = retry_count
        return new_state

    new_state = dict(state)
    new_state["generated_sql"] = fixed_sql
    new_state["error"] = None
    new_state["retry_count"] = retry_count
    return new_state


def node_reason(state: AgentState) -> AgentState:
    """Generate final human-readable answer."""
    answer = reason_chain.invoke({
        "question": state["user_query"],
        "result": state["result"]
    })

    try:
        drop_temp_mysql_db(state["db_config"]["database"])
    except Exception as e:
        print(f"Warning: could not drop temp DB - {e}")

    new_state = dict(state)
    new_state["answer"] = answer
    return new_state


def has_error(state: AgentState) -> str:
    """Conditional edge: fix SQL if error, else reason."""
    return "fix_sql" if state.get("error") else "reason"

# langgraph workflow creation
graph = StateGraph(AgentState)
graph.add_node("create_db", node_create_db)
graph.add_node("generate_sql", node_generate_sql)
graph.add_node("execute_sql", node_execute_sql)
graph.add_node("fix_sql", node_fix_sql)
graph.add_node("reason", node_reason)

graph.set_entry_point("create_db")
graph.add_edge("create_db", "generate_sql")
graph.add_edge("generate_sql", "execute_sql")
graph.add_conditional_edges("execute_sql", has_error)
graph.add_edge("fix_sql", "execute_sql")

ai_app = graph.compile()
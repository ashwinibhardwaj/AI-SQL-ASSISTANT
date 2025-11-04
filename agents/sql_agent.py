from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Optional[List[BaseMessage]]     
    user_query: Optional[str]
    schema: Optional[Dict[str, Any]] 
    db_config: Optional[Dict[str, Any]] 
    generated_sql: Optional[str]
    result: Optional[List[Any]]
    error: Optional[str]
    answer: Optional[str]
    retry_count: Optional[int]

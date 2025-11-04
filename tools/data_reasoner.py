# tools/data_reasoner.py
from langchain_core.prompts import ChatPromptTemplate
from agents.simple_bot import model, parser

reason_prompt = ChatPromptTemplate.from_template("""
You are a data analysis assistant.
The user asked: {question}
Here is the query result:
{result}
Give a concise answer to the user's question.
""")

reason_chain = reason_prompt | model | parser

# tools/query_generator.py
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

api_key = os.getenv("HUGGINGFACEHUB_ACCESS_TOCKEN")
llm = HuggingFaceEndpoint(
    repo_id="openai/gpt-oss-20b",
    task="text-generation",
    huggingfacehub_api_token=api_key
)
model = ChatHuggingFace(llm=llm)



prompt = ChatPromptTemplate.from_template("""
You are an expert SQL assistant.
Given the following database schema and user question, write a valid SQL query.
Schema:
{schema}
Question:
{question}
SQL:
""")

parser = StrOutputParser()
generate_sql_chain = prompt | model | parser

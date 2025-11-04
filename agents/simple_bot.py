from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HUGGINGFACEHUB_ACCESS_TOCKEN")

llm = HuggingFaceEndpoint(
    repo_id="openai/gpt-oss-120b",
    task = "text-generation",
    huggingfacehub_api_token=api_key
)

model = ChatHuggingFace(llm = llm)


system_message = SystemMessagePromptTemplate.from_template(
    """You are an expert SQL assistant. 
    Use the given dataset schema to generate and execute SQL queries accurately.
    Answer for only the given query, dont include any exesive information in your answer."""
)

human_message = HumanMessagePromptTemplate.from_template(
    "{query}, {schema_context}"
)

prompt = ChatPromptTemplate.from_messages([
    system_message,
    human_message
])

parser = StrOutputParser()

chain = prompt | model | parser

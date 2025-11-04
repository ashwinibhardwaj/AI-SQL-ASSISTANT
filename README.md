🧠 AI SQL ASSISTANT
    Natural Language → SQL → Instant Results on Your Database

  -> An AI-powered web application that lets you query your own databases in plain English.
  -> Upload a .sql dump, and the app will:
  -> Create a live MySQL database
  -> Generate accurate SQL queries using an LLM (Hugging Face)
  -> Execute them instantly
  -> Fix errors if needed
  -> Display results and insights — all from a clean web UI

⚙️ Tech Stack
  Python (Flask) – Web Framework
  LangGraph / LangChain – Agentic Reasoning
  Hugging Face LLM – Query Understanding & Generation
  MySQL – Dynamic Database Execution

🚀 Setup & Installation
# 1. Clone the repo
git clone https://github.com/<your-username>/AI-SQL-ASSISTANT.git
cd AI-SQL-ASSISTANT

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# or
source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

🧩 Create .env File
FLASK_APP=app.py
UPLOAD_FOLDER=uploads
HUGGINGFACEHUB_ACCESS_TOCKEN=your_huggingface_api_key
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword

▶️ Run the Application
python app.py


Open your browser and visit:
👉 http://127.0.0.1:5000

💻 How It Works

Upload a .sql dump file

Ask questions in plain English

The AI creates a temp database, writes SQL, and executes it

View results + natural language explanations in the UI

🌟 Key Features

🧠 AI-generated SQL Queries

⚙️ Auto Database Creation from SQL Dumps

💬 Conversational Query Interface

🔁 Error Handling & SQL Fixing

📊 Smart Result Visualization

🧩 Built on LangGraph for Agentic Workflow

👩‍💻 Author

Ashwini Bhardwaj
AI & LLM Engineer | Building Agentic Systems 🚀

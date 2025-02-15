import os
import json
import shutil
import uvicorn
import subprocess
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests
from datetime import datetime
import sqlite3

# Initialize FastAPI app
app = FastAPI()

# AI Proxy API URL (GPT-4o-Mini)
AI_PROXY_URL = "https://aiproxy.sanand.workers.dev/openai/"
AI_PROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "your_token_here")

# Directory security constraints
DATA_DIR = "/data"

# Ensure /data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Helper function to ensure security
def validate_path(file_path: str):
    abs_path = os.path.abspath(file_path)
    if not abs_path.startswith(DATA_DIR):
        raise HTTPException(status_code=400, detail="Access denied outside /data")
    return abs_path

# Function to communicate with AI Proxy
def call_ai_proxy(prompt):
    headers = {"Authorization": f"Bearer {AI_PROXY_TOKEN}"}
    payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post(AI_PROXY_URL, json=payload, headers=headers)
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()

# POST /run - Executes a task
@app.post("/run")
def run_task(task: str = Query(..., description="Task description in plain English")):
    try:
        # Use AI Proxy to parse the task
        task_response = call_ai_proxy(f"Parse this task and return structured steps: {task}")

        # Logging
        print(f"Parsed Task: {task_response}")

        # Simulated execution based on parsed task
        if "install uv" in task.lower():
            subprocess.run(["pip", "install", "uv"], check=True)
        elif "format /data/format.md" in task.lower():
            subprocess.run(["npx", "prettier@3.4.2", "--write", validate_path(f"{DATA_DIR}/format.md")])
        elif "count wednesdays" in task.lower():
            with open(validate_path(f"{DATA_DIR}/dates.txt"), "r") as f:
                count = sum(1 for line in f if datetime.strptime(line.strip(), "%Y-%m-%d").weekday() == 2)
            with open(validate_path(f"{DATA_DIR}/dates-wednesdays.txt"), "w") as f:
                f.write(str(count))
        elif "sort contacts" in task.lower():
            with open(validate_path(f"{DATA_DIR}/contacts.json"), "r") as f:
                contacts = json.load(f)
            contacts.sort(key=lambda x: (x["last_name"], x["first_name"]))
            with open(validate_path(f"{DATA_DIR}/contacts-sorted.json"), "w") as f:
                json.dump(contacts, f, indent=4)
        elif "extract sender email" in task.lower():
            with open(validate_path(f"{DATA_DIR}/email.txt"), "r") as f:
                email_content = f.read()
            sender_email = call_ai_proxy(f"Extract sender email from this text: {email_content}")
            with open(validate_path(f"{DATA_DIR}/email-sender.txt"), "w") as f:
                f.write(sender_email)
        elif "total sales gold tickets" in task.lower():
            conn = sqlite3.connect(validate_path(f"{DATA_DIR}/ticket-sales.db"))
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type='Gold'")
            total_sales = cursor.fetchone()[0]
            with open(validate_path(f"{DATA_DIR}/ticket-sales-gold.txt"), "w") as f:
                f.write(str(total_sales))
            conn.close()
        else:
            raise HTTPException(status_code=400, detail="Unknown task")
        
        return {"status": "success", "task": task}
    
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))

# GET /read - Returns the content of a file
@app.get("/read")
def read_file(path: str = Query(..., description="Path to the file")):
    try:
        file_path = validate_path(path)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

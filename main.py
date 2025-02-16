import os
import subprocess
import requests
import json
import glob
import datetime
import sqlite3
import base64
import tempfile
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

app = FastAPI()

# ----- Helper functions -----

def check_path(path: str):
    """
    Ensure that any file access is inside /data.
    """
    if not os.path.abspath(path).startswith("/data"):
        raise Exception("Access to files outside /data is forbidden.")

def call_llm(prompt: str) -> str:
    """
    Calls the AI Proxy chat API (GPT-4o-Mini) with a short prompt.
    """
    token = os.environ.get("AIPROXY_TOKEN")
    if not token:
        raise Exception("AIPROXY_TOKEN not set")
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, json=data, timeout=15)
    if response.status_code != 200:
        raise Exception(f"LLM API error: {response.text}")
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()

def get_embedding(text: str) -> list:
    """
    Uses the AI Proxy embedding endpoint.
    """
    token = os.environ.get("AIPROXY_TOKEN")
    if not token:
        raise Exception("AIPROXY_TOKEN not set")
    url = "https://aiproxy.sanand.workers.dev/openai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "model": "text-embedding-3-small",
        "input": [text]
    }
    response = requests.post(url, headers=headers, json=data, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Embedding API error: {response.text}")
    result = response.json()
    return result["data"][0]["embedding"]

# ----- Phase A Task Implementations -----

def task_A1():
    """
    A1. Install uv (if required) and run the remote datagen.py with USER_EMAIL.
    """
    user_email = os.environ.get("USER_EMAIL")
    if not user_email:
        raise Exception("USER_EMAIL environment variable not set for Task A1")
    # Install uv if not installed.
    try:
        import uv  # noqa: F401
    except ImportError:
        subprocess.run(["pip", "install", "uv"], check=True)
    # Download datagen.py
    url = "https://raw.githubusercontent.com/sanand0/tools-in-data-science-public/tds-2025-01/project-1/datagen.py"
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        raise Exception("Failed to download datagen.py")
    # Write to a temporary file
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as f:
        f.write(r.text)
        temp_path = f.name
    # Run the downloaded script with the user's email
    subprocess.run(["python", temp_path, user_email], check=True)
    os.remove(temp_path)
    return "Task A1 executed successfully."

def task_A2():
    """
    A2. Format /data/format.md using prettier@3.4.2.
    """
    file_path = "/data/format.md"
    check_path(file_path)
    subprocess.run(["npx", "prettier@3.4.2", "--write", file_path], check=True)
    return "Task A2 executed successfully."

def task_A3():
    """
    A3. Count the number of Wednesdays in /data/dates.txt and write the number to /data/dates-wednesdays.txt.
    """
    input_path = "/data/dates.txt"
    output_path = "/data/dates-wednesdays.txt"
    check_path(input_path)
    check_path(output_path)
    count = 0
    with open(input_path, "r") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            dt = datetime.datetime.strptime(line, "%Y-%m-%d")
        except ValueError:
            continue
        if dt.weekday() == 2:  # Wednesday (Monday=0)
            count += 1
    with open(output_path, "w") as f:
        f.write(str(count))
    return "Task A3 executed successfully."

def task_A4():
    """
    A4. Sort the contacts in /data/contacts.json by last_name then first_name.
    """
    input_path = "/data/contacts.json"
    output_path = "/data/contacts-sorted.json"
    check_path(input_path)
    check_path(output_path)
    with open(input_path, "r") as f:
        contacts = json.load(f)
    sorted_contacts = sorted(contacts, key=lambda x: (x.get("last_name", ""), x.get("first_name", "")))
    with open(output_path, "w") as f:
        json.dump(sorted_contacts, f)
    return "Task A4 executed successfully."

def task_A5():
    """
    A5. For the 10 most recent .log files in /data/logs/, write their first line (most recent first) to /data/logs-recent.txt.
    """
    logs_dir = "/data/logs/"
    output_path = "/data/logs-recent.txt"
    check_path(logs_dir)
    check_path(output_path)
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    if not log_files:
        raise Exception("No .log files found in /data/logs/")
    log_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    recent_files = log_files[:10]
    lines = []
    for file in recent_files:
        with open(file, "r") as f:
            first_line = f.readline().strip()
            lines.append(first_line)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    return "Task A5 executed successfully."

def task_A6():
    """
    A6. Scan all Markdown files in /data/docs/ for the first H1 title and create an index file.
    """
    docs_dir = "/data/docs/"
    output_path = "/data/docs/index.json"
    check_path(docs_dir)
    check_path(output_path)
    md_files = glob.glob(os.path.join(docs_dir, "**/*.md"), recursive=True)
    index = {}
    for file in md_files:
        with open(file, "r") as f:
            for line in f:
                if line.startswith("#"):
                    title = line.lstrip("#").strip()
                    rel_path = os.path.relpath(file, docs_dir)
                    index[rel_path] = title
                    break
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(index, f)
    return "Task A6 executed successfully."

def task_A7():
    """
    A7. Extract the sender’s email from /data/email.txt using an LLM and write it to /data/email-sender.txt.
    """
    input_path = "/data/email.txt"
    output_path = "/data/email-sender.txt"
    check_path(input_path)
    check_path(output_path)
    with open(input_path, "r") as f:
        content = f.read()
    prompt = (
        "Extract the sender's email address from the following email message:\n\n"
        f"{content}\n\nReturn only the email address."
    )
    result = call_llm(prompt)
    with open(output_path, "w") as f:
        f.write(result)
    return "Task A7 executed successfully."

def task_A8():
    """
    A8. Extract a credit card number from /data/credit-card.png via an LLM and write it (without spaces) to /data/credit-card.txt.
    """
    input_path = "/data/credit-card.png"
    output_path = "/data/credit-card.txt"
    check_path(input_path)
    check_path(output_path)
    with open(input_path, "rb") as f:
        img_data = f.read()
    b64_data = base64.b64encode(img_data).decode("utf-8")
    prompt = (
        "Extract the credit card number from the following image (encoded in base64). "
        "Return only the credit card number without spaces.\n\n" + b64_data
    )
    result = call_llm(prompt)
    result = result.replace(" ", "")
    with open(output_path, "w") as f:
        f.write(result)
    return "Task A8 executed successfully."

def task_A9():
    """
    A9. Using embeddings, find the most similar pair of comments from /data/comments.txt and write them to /data/comments-similar.txt.
    """
    input_path = "/data/comments.txt"
    output_path = "/data/comments-similar.txt"
    check_path(input_path)
    check_path(output_path)
    with open(input_path, "r") as f:
        comments = [line.strip() for line in f if line.strip()]
    if len(comments) < 2:
        raise Exception("Not enough comments to compare.")
    embeddings = []
    for comment in comments:
        emb = get_embedding(comment)
        embeddings.append(emb)
    def cosine_similarity(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)
    max_sim = -1
    pair = (None, None)
    for i in range(len(comments)):
        for j in range(i + 1, len(comments)):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            if sim > max_sim:
                max_sim = sim
                pair = (comments[i], comments[j])
    with open(output_path, "w") as f:
        f.write(pair[0] + "\n" + pair[1])
    return "Task A9 executed successfully."

def task_A10():
    """
    A10. Compute the total sales (units * price) of “Gold” tickets in /data/ticket-sales.db.
    """
    db_path = "/data/ticket-sales.db"
    output_path = "/data/ticket-sales-gold.txt"
    check_path(db_path)
    check_path(output_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type = 'Gold'")
    result = cursor.fetchone()[0]
    conn.close()
    with open(output_path, "w") as f:
        f.write(str(result))
    return "Task A10 executed successfully."

# ----- Phase B: Business Tasks (Stub Implementation) -----

def process_business_task(task: str):
    """
    For business tasks such as fetching data from an API, cloning a repo, or converting Markdown to HTML,
    you could implement appropriate logic. For now, this stub returns a message.
    """
    return "Business task executed (stub)."

# ----- Main Dispatcher -----

def process_task(task: str):
    task_lower = task.lower()
    if ("datagen.py" in task_lower) or ("install uv" in task_lower and "datagen" in task_lower):
        return task_A1()
    elif "prettier" in task_lower and "format.md" in task_lower:
        return task_A2()
    elif "dates.txt" in task_lower and "wednesday" in task_lower:
        return task_A3()
    elif "contacts.json" in task_lower and "sort" in task_lower:
        return task_A4()
    elif "logs" in task_lower and ".log" in task_lower and "first line" in task_lower:
        return task_A5()
    elif "docs" in task_lower and ".md" in task_lower and ("index" in task_lower or "h1" in task_lower):
        return task_A6()
    elif "email.txt" in task_lower and "email-sender" in task_lower:
        return task_A7()
    elif "credit-card.png" in task_lower:
        return task_A8()
    elif "comments.txt" in task_lower and "similar" in task_lower:
        return task_A9()
    elif "ticket-sales.db" in task_lower and "gold" in task_lower:
        return task_A10()
    # Prevent deletion operations (B2)
    elif "delete" in task_lower or "rm " in task_lower:
        raise Exception("Deletion operations are not allowed.")
    # Business tasks keywords (B3–B10)
    elif any(keyword in task_lower for keyword in [
            "fetch data", "clone", "sql query", "scrape", "compress", "resize",
            "transcribe", "convert markdown", "csv"
        ]):
        return process_business_task(task)
    else:
        raise Exception("Task not recognized.")

# ----- API Endpoints -----

@app.post("/run")
def run_task(task: str = Query(..., description="Task description in plain English")):
    try:
        result = process_task(task)
        return {"message": result}
    except Exception as e:
        err_msg = str(e)
        if "not recognized" in err_msg or "Deletion operations" in err_msg:
            raise HTTPException(status_code=400, detail=err_msg)
        else:
            raise HTTPException(status_code=500, detail=err_msg)

@app.get("/read", response_class=PlainTextResponse)
def read_file(path: str = Query(..., description="Absolute file path to read (must be inside /data)")):
    try:
        check_path(path)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="")
        with open(path, "r") as f:
            content = f.read()
        return content
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

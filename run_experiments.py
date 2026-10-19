import json
import os
import time
from openai import OpenAI
from lookup import calculate, lookup
from agent import run_react_agent

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Автоматическая проверка пути к файлу вопросов
questions_path = "questions.json"
if not os.path.exists(questions_path):
    questions_path = "data/questions.json"

with open(questions_path, "r", encoding="utf-8") as f:
    questions = json.load(f)

print(f"Loaded {len(questions)} questions from '{questions_path}'. Starting evaluation...\n")

results = []

for q in questions:
    q_id = q.get("id", "Q-XX")
    q_text = q.get("question", "")
    
    print(f"Processing {q_id}...")
    
    start_time = time.time()
    try:
        s3_answer = run_react_agent(q_text)
    except Exception as e:
        s3_answer = f"Error: {e}"
    elapsed = round(time.time() - start_time, 2)
    
    results.append({
        "id": q_id,
        "question": q_text,
        "s3_answer": s3_answer,
        "time_sec": elapsed
    })

print("\n--- Summary Results ---")
for r in results:
    print(f"{r['id']} ({r['time_sec']}s): {r['s3_answer'][:80]}...")
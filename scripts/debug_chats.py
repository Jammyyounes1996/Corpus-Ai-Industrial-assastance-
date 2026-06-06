import httpx
import subprocess
import time
import sys


proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8012"],
    cwd=r"C:\Users\Mohamed ALi\Desktop\Industrial Ai assiatant",
    stderr=open("backend_error.log", "w"),
)
time.sleep(8)

try:
    # Test 1: empty body
    r1 = httpx.post("http://127.0.0.1:8012/api/chats", json={})
    print(f"Empty body: {r1.status_code} {r1.text}")

    # Test 2: with title
    r2 = httpx.post("http://127.0.0.1:8012/api/chats", json={"title": "test"})
    print(f"With title: {r2.status_code} {r2.text}")

    if r2.status_code == 201:
        chat_id = r2.json().get("id")
        r3 = httpx.post(
            f"http://127.0.0.1:8012/api/chat/{chat_id}/stream",
            json={"query": "test", "attached_files": [], "model_provider": "ollama", "model_name": "gemma4:latest"},
            timeout=30,
        )
        print(f"Stream: {r3.status_code} {r3.text[:500]}")
finally:
    proc.terminate()

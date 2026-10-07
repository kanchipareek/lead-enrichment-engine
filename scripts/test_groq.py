import os, json, urllib.request, urllib.error

key = os.environ.get("GROQ_API_KEY", "")
print("key length:", len(key))
print("starts with gsk_:", key.startswith("gsk_"))
print("has leading/trailing space:", key != key.strip())

body = json.dumps({
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "say ok"}],
}).encode()
req = urllib.request.Request(
    "https://api.groq.com/openai/v1/chat/completions",
    data=body,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("SUCCESS", r.status)
        print(r.read().decode()[:300])
except urllib.error.HTTPError as e:
    print("HTTP ERROR", e.code)
    print(e.read().decode("utf-8", "replace"))
except Exception as e:
    print("OTHER:", type(e).__name__, e)

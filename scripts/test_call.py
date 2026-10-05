import json, os, urllib.request, urllib.error

# show the URL line as it actually exists in extract.py
try:
    for l in open("scripts/extract.py"):
        if "generativelanguage" in l:
            print("extract.py URL line:", l.strip())
except Exception as e:
    print("could not read scripts/extract.py:", e)

k = os.environ.get("GEMINI_API_KEY", "")
if not k:
    raise SystemExit("no GEMINI_API_KEY in this terminal")

model = "gemini-3.8-flash"
body = json.dumps({"contents":[{"parts":[{"text":"Reply with the single word: ok"}]}]}).encode()

for ver in ("v1beta", "v1"):
    url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={k}"
    print("---", ver, "---")
    print("URL:", url.replace(k, "KEY"))
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            print("HTTP", r.status, "->", r.read().decode()[:400])
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, "->", e.read().decode()[:400])
    except Exception as e:
        print("failed:", repr(e))

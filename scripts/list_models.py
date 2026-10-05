import json, os, urllib.request, urllib.error

k = os.environ.get("GEMINI_API_KEY", "")
if not k:
    raise SystemExit("no GEMINI_API_KEY in this terminal - export it first")

for ver in ("v1beta", "v1"):
    url = f"https://generativelanguage.googleapis.com/{ver}/models?key={k}"
    try:
        d = json.load(urllib.request.urlopen(url, timeout=30))
        names = [m["name"] for m in d.get("models", [])]
        print(f"[{ver}] OK - {len(names)} models available:")
        for n in names:
            print("   ", n)
    except urllib.error.HTTPError as e:
        print(f"[{ver}] HTTP {e.code}: {e.read().decode()[:300]}")
    except Exception as e:
        print(f"[{ver}] failed: {e}")

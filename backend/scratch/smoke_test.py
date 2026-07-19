"""
End-to-end smoke test for all Phase 1 endpoints.
Run from: backend/ directory with venv activated.
"""
import urllib.request
import urllib.parse
import json
import sys

BASE = "http://127.0.0.1:8001"

def req(method, path, data=None, token=None, content_type="application/json"):
    url = BASE + path
    body = None
    if data:
        if content_type == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode()
        else:
            body = json.dumps(data).encode()
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", content_type)
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

ok = True
def check(name, status, body, expect=200):
    global ok
    passed = status == expect
    if not passed: ok = False
    icon = "✓" if passed else "✗"
    print(f"{icon} [{status}] {name}")
    if not passed:
        print(f"    Response: {json.dumps(body)[:200]}")
    return passed

print("=" * 50)
print("MotherCare AI — Smoke Test")
print("=" * 50)

# 1. Health
s, b = req("GET", "/health")
check("GET /health", s, b)

# 2. Register
s, b = req("POST", "/auth/register",
           {"username": "smokeuser", "email": "smoke@test.com", "password": "Test1234!"},
           content_type="application/x-www-form-urlencoded")
check("POST /auth/register", s, b, expect=200)

# 3. Login
s, b = req("POST", "/auth/login",
           {"username": "smokeuser", "password": "Test1234!"},
           content_type="application/x-www-form-urlencoded")
if not check("POST /auth/login", s, b):
    print("Cannot continue without token"); sys.exit(1)
token = b.get("access_token")
print(f"  Token: {token[:30]}...")

# 4. GET /ai/twin (creates twin)
s, b = req("GET", "/ai/twin", token=token)
check("GET /ai/twin", s, b)

# 5. PUT /ai/twin (update biomarkers)
s, b = req("PUT", "/ai/twin",
           {"current_week": 24, "systolic_bp": 118, "glucose_level": 95, "hemoglobin": 11.5, "bmi": 23.0},
           token=token)
check("PUT /ai/twin", s, b)
if s == 200:
    risks = b["data"].get("risk_analysis", {}).get("risk_scores", {})
    print(f"  Risk scores: {risks}")

# 6. POST /ai/chat
s, b = req("POST", "/ai/chat", {"query": "What foods are good for iron during pregnancy?", "language": "English"}, token=token)
check("POST /ai/chat", s, b)
if s == 200:
    agent = b["data"].get("agent")
    rag   = b["data"].get("rag_context_used")
    resp  = b["data"].get("response", "")[:80]
    print(f"  Agent: {agent} | RAG: {rag}")
    print(f"  Response preview: {resp}...")

# 7. GET /ai/records
s, b = req("GET", "/ai/records", token=token)
check("GET /ai/records", s, b)
if s == 200:
    print(f"  Records: {len(b['data'])} entries")

# 8. POST /analyze
import urllib.request, urllib.parse
boundary = "----TestBoundary123"
body_parts = [
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"symptoms\"\r\n\r\nfever and headache for 3 days\r\n".encode(),
    f"--{boundary}--\r\n".encode()
]
body_bytes = b"".join(body_parts)
r2 = urllib.request.Request(BASE + "/analyze", data=body_bytes, method="POST")
r2.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
r2.add_header("Authorization", f"Bearer {token}")
try:
    with urllib.request.urlopen(r2, timeout=30) as resp:
        s2, b2 = resp.status, json.loads(resp.read())
except urllib.error.HTTPError as e:
    s2, b2 = e.code, json.loads(e.read())
check("POST /analyze (symptom triage)", s2, b2)
if s2 == 200:
    d = b2.get("data", {})
    print(f"  Condition: {d.get('condition')} | Urgency: {d.get('urgency')}")

print("=" * 50)
print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
print("=" * 50)

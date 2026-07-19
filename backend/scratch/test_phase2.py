import requests
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_phase2():
    print("--- PHASE 2 VERIFICATION START ---")
    
    # 1. Register User A
    user_a = f"user_a_{uuid.uuid4().hex[:4]}"
    print(f"\n[1] Registering User A: {user_a}")
    reg_a = requests.post(f"{BASE_URL}/auth/register", data={
        "username": user_a,
        "email": f"{user_a}@example.com",
        "password": "password123"
    })
    print(f"Status: {reg_a.status_code}, Response: {reg_a.json()}")

    # 2. Login User A
    print(f"\n[2] Logging in User A")
    login_a = requests.post(f"{BASE_URL}/auth/login", data={
        "username": user_a,
        "password": "password123"
    })
    token_a = login_a.json()["access_token"]
    print(f"Login Success. Token: {token_a[:10]}...")

    # 3. Authenticated Analysis for User A
    print(f"\n[3] Authenticated Analysis for User A")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    analyze_a = requests.post(f"{BASE_URL}/analyze", data={"symptoms": "I have a sharp fever and headache"}, headers=headers_a)
    print(f"Status: {analyze_a.status_code}")
    print(f"Condition: {analyze_a.json()['data']['condition']}")

    # 4. Check for 'Similar Symptoms' alert for User A (Should show on second call)
    print(f"\n[4] Submitting similar symptoms for User A")
    analyze_a2 = requests.post(f"{BASE_URL}/analyze", data={"symptoms": "High fever and bad headache again"}, headers=headers_a)
    note_a = analyze_a2.json()['data'].get('history_note')
    print(f"History Note for User A: {note_a}")

    # 5. Register and Login User B
    user_b = f"user_b_{uuid.uuid4().hex[:4]}"
    print(f"\n[5] Registering and Logging in User B: {user_b}")
    requests.post(f"{BASE_URL}/auth/register", data={
        "username": user_b,
        "email": f"{user_b}@example.com",
        "password": "password123"
    })
    login_b = requests.post(f"{BASE_URL}/auth/login", data={
        "username": user_b,
        "password": "password123"
    })
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 6. Verify isolation (User B should NOT see User A's history alert)
    print(f"\n[6] Submitting same symptoms for User B (Isolation Check)")
    analyze_b = requests.post(f"{BASE_URL}/analyze", data={"symptoms": "High fever and bad headache"}, headers=headers_b)
    note_b = analyze_b.json()['data'].get('history_note')
    print(f"History Note for User B: {note_b}")
    
    if note_b is None:
        print("\nSUCCESS: User B history is isolated from User A.")
    else:
        print("\nFAILURE: User B saw history from another user.")

    print("\n--- PHASE 2 VERIFICATION END ---")

if __name__ == "__main__":
    try:
        test_phase2()
    except Exception as e:
        print(f"Test failed: {e}. Is the server running?")

"""
Load Testing for MotherCare AI

Run with: locust -f backend/tests/load_test.py -u 100 -r 10 --run-time 5m

Or with k6:
  k6 run backend/tests/load_test.js

This test simulates realistic user behavior:
1. User registers
2. User logs in
3. User makes chat requests
4. User views digital twin
"""

import random
import time
from locust import HttpUser, task, between, constant_pacing


class MotherCareUser(HttpUser):
    """Simulates a MotherCare AI user."""
    
    wait_time = between(1, 5)
    
    def on_start(self):
        """Initialize user with test data."""
        self.token = None
        self.username = f"loadtest_user_{random.randint(1000, 9999)}"
        self.email = f"{self.username}@example.com"
        self.password = "TestPassword123!"
        
        # Register user
        self.register()
        # Login
        self.login()
    
    def register(self):
        """Register a new user."""
        response = self.client.post(
            "/auth/register",
            data={
                "username": self.username,
                "email": self.email,
                "password": self.password
            }
        )
        if response.status_code != 201:
            print(f"Registration failed: {response.status_code}")
    
    def login(self):
        """Login and get JWT token."""
        response = self.client.post(
            "/auth/login",
            data={
                "username": self.username,
                "password": self.password
            }
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data["data"]["access_token"]
        else:
            print(f"Login failed: {response.status_code}")
    
    def get_headers(self):
        """Get headers with JWT token."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @task(10)
    def chat_query(self):
        """Make a chat query (most common task)."""
        queries = [
            "I have a fever and headache",
            "Should I be worried about bleeding?",
            "What should I eat during pregnancy?",
            "How much water should I drink?",
            "I feel dizzy and nauseous"
        ]
        
        response = self.client.post(
            "/ai/chat",
            json={
                "query": random.choice(queries),
                "language": "English"
            },
            headers=self.get_headers()
        )
    
    @task(3)
    def get_digital_twin(self):
        """Retrieve digital twin data."""
        response = self.client.get(
            "/ai/twin",
            headers=self.get_headers()
        )
    
    @task(2)
    def update_digital_twin(self):
        """Update digital twin biomarkers."""
        response = self.client.put(
            "/ai/twin",
            json={
                "current_week": random.randint(20, 40),
                "systolic_bp": random.randint(110, 140),
                "diastolic_bp": random.randint(70, 90),
                "glucose_level": random.randint(80, 120),
                "hemoglobin": round(random.uniform(10, 14), 1)
            },
            headers=self.get_headers()
        )
    
    @task(2)
    def get_health_records(self):
        """Retrieve health records."""
        response = self.client.get(
            "/ai/records",
            headers=self.get_headers()
        )
    
    @task(1)
    def health_check(self):
        """Check backend health."""
        response = self.client.get("/health")


if __name__ == "__main__":
    print("Run with: locust -f backend/tests/load_test.py -u 100 -r 10 --run-time 5m")

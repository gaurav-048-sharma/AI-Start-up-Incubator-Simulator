import requests
import time
import json

base_url = "http://localhost:8001"
headers = {"Content-Type": "application/json"}
# We won't pass an authorization token, we just want to see if the server logs a 401 for a POST request.

data = {
    "title": "Proactive Defense Engine",
    "description": "Enterprises urgently need a proactive defense engine."
}

print("Sending POST /api/ideas")
try:
    r = requests.post(f"{base_url}/api/ideas", json=data, headers=headers)
    print(r.status_code, r.text)
except Exception as e:
    print(e)

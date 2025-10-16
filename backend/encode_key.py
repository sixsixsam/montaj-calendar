import json
import base64

with open("backend/serviceAccountKey.json", "r") as f:
    data = f.read()

encoded = base64.b64encode(data.encode()).decode()
print(encoded)

import json

with open("serviceAccountKey.json", "r") as f:
    data = f.read()

print(json.dumps(data))

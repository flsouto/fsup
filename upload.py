import requests
from utils import *
import os
import json

url = "https://freesound.org/apiv2/sounds/upload/"

token = json.loads(open('token.json').read())

file_path = "industrial-loop2.wav"

headers = {
    "Authorization": f"Bearer {token['access_token']}"
}

files = {
    "audiofile": open(file_path, "rb")
}

data = {
    "description": "Industrial Loop 2",
    "license" : "Attribution",
    "tags": "Industrial Loop, Drum Loop, Ambient Loop"
}

print("Posting...")
response = requests.post(url, headers=headers, files=files, data=data)

if response.status_code == 201:
    print("Audio upload successful!")
    print("Sound ID:", response.json()["id"])
else:
    print("Error uploading audio:")
    print(response.text)

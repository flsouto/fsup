import utils
from os import getenv
import sys
import requests

url = "https://freesound.org/apiv2/oauth2/access_token/"
payload = {
    "client_id": getenv("FREESOUND_ID"),
    "client_secret": getenv("FREESOUND_SECRET"),
    "code" : sys.argv[1],
    "grant_type": "authorization_code"
}

response = requests.post(url, data=payload)

open('token.json', 'w+').write(response.text)

print(response.text)

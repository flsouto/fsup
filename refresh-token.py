import utils
from os import getenv
import sys
import requests
import json

token = json.loads(open('token.json', 'r').read())

url = "https://freesound.org/apiv2/oauth2/access_token/"
payload = {
    "client_id": getenv("client_id"),
    "client_secret": getenv("client_secret"),
    "refresh_token" : token['refresh_token'],
    "grant_type": "refresh_token"
}

response = requests.post(url, data=payload)

open('token.json', 'w+').write(response.text)

print(response.text)

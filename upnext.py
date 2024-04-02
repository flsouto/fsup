import requests
from utils import *
import os
from os.path import basename
import json
from pathlib import Path
import glob
from random import shuffle
from jsondb import Object
from looplipy import Wav
from argparse import ArgumentParser

ap = ArgumentParser()
ap.add_argument('--dry-run','-d',action='store_true')
args,_ = ap.parse_known_args()


files = glob.glob(os.getenv('queue_glob'))

shuffle(files)

uploaded_loops = Object('data/uploaded_loops.json')

avail_loops = [f for f in files if basename(f) not in uploaded_loops]

if len(avail_loops) < 1:
    print("All loops have been uploaded")
    exit()

loop_f = avail_loops.pop()
uploaded_loops[basename(loop_f)] = 1

loop = Wav(loop_f).round_bpm()
title =  "%d BPM Industrial Drum Loop #%d" % (loop.bpm() , len(uploaded_loops.data.keys()) )
desc = ('This %dbpm' % loop.bpm()) + " Drum Loop is good for Ambient/Industrial/Electronic songs or as soundtrack to a sci-fi/suspense/horror indie game or short film."

url = "https://freesound.org/apiv2/sounds/upload/"
token = json.loads(open('token.json').read())
headers = {
    "Authorization": f"Bearer {token['access_token']}"
}

files = {
    "audiofile": open(loop.file, "rb")
}


data = {
    "name": title,
    "description": desc,
    "license" : "Attribution",
    "tags": "Industrial Loop, Drum Loop, Ambient Loop, Loop Packs, Loopable, Samples, Soundtrack, Underground, Dark, Weird, Alien"
}

print(data)

if args.dry_run:
    print("Avail loops: %d" % len(avail_loops))
    exit()

print("Posting...")
response = requests.post(url, headers=headers, files=files, data=data)

if response.status_code == 201:
    result = response.json()
    if result["id"]:
        print("Audio upload successful!")
        print("Sound ID:", result["id"])
        uploaded_loops.save()
    else:
        print("Could not decode ID from response: ", response)
else:
    print("Error uploading audio:")
    print(response.text)


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
from datetime import datetime

ap = ArgumentParser()
ap.add_argument('--dry-run','-d',action='store_true')
args,_ = ap.parse_known_args()

files = [f for p in os.getenv('queue_glob').split(';') for f in glob.glob(p)]
shuffle(files)

uploaded_loops = Object('data/uploaded_loops.json')

avail_loops = [f for f in files if basename(f) not in uploaded_loops]

if len(avail_loops) < 1:
    print("All loops have been uploaded")
    exit()

loop_f = avail_loops.pop()
uploaded_loops[basename(loop_f)] = 1

loop = Wav(loop_f)

if not 'trk' in loop_f:

    loop = loop.round_bpm()

    type = 'Drum'

    if 'amb' in loop_f:
        type = 'Ambient'

    if 'gli' in loop_f:
        type = 'Glitch'

    if 'tri' in loop_f:
        type = 'Tribal'

    if 'noi' in loop_f:
        type = 'Noise'

    if 'hor' in loop_f:
        type = 'Horror'

    if 'dro' in loop_f:
        type = 'Drone'

    if 'brk' in loop_f:
        type = 'Breakbeat'

    if 'har' in loop_f:
        type = 'Hardcore'

    if 'syn' in loop_f:
        type = 'Synth'

    if 'asmr' in loop_f:
        type = 'ASMR'

    if 'exc' in loop_f and not 'asmr' in loop_f:
        pack = 'Especial Loops'
    else:
        if loop.bpm() in [80,100,120]:
            pack = "%d BPM Loops" % loop.bpm()
        else:
            pack = f'{type} Loops'


    title =  "%d BPM Industrial %s Loop #%d (WAV)" % (loop.bpm() , type , len(uploaded_loops.data.keys()) )
    desc = ('This %dbpm' % loop.bpm()) + f" {type} Loop is good for composing Industrial/Electronic/Ambient songs or using as soundtrack to a sci-fi/suspense/horror indie game or short film."
    tags =  "Industrial Loop, Drum Loop, Ambient Loop, Loop Packs, Loopable, Samples, Soundtrack, Underground, Dark, Weird, Alien"
else:
    pub_trks = [k for k in uploaded_loops.data.keys() if 'trk' in k]
    if loop.len() > 60:
        title = "Demo Track #%d (Industraumatic)" % (len(pub_trks))
        pack = "Industraumatic Demos"
    else:
        title = "Short Track #%d (Industraumatic)" % (len(pub_trks))
        pack = "Industraumatic Shorts"
    desc = "Track taken from the Industraumatic Project. Please subscribe here: <a href=\"https://www.youtube.com/@industraumatic\">https://www.youtube.com/@industraumatic</a>"
    tags = "Soundtrack, Ambient, Underground, Games, Sci-fi, Horror, Industrial, Noise, Cyberpunk"

pack += ' '+datetime.today().strftime('%m/%Y')
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
    "tags": tags,
    "pack": pack
}

print(data)

if args.dry_run:
    print("Avail loops: %d" % len(avail_loops))
    exit()

print(f"Posting {loop_f}...")
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
    if 'already part of freesound' in response.text:
    	uploaded_loops.save()

os.system('python3 refresh-token.py')
os.system('git add -u; git commit -m "updates"; git push origin $(git branch --show-current)');

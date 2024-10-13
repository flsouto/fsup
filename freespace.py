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
import time
import sys

input_data = None
if not sys.stdin.isatty():
    input_data = sys.stdin.read().splitlines()

files = input_data or [f for p in os.getenv('queue_glob').split(';') for f in glob.glob(p)]

uploaded_loops = Object('data/uploaded_loops.json')
target_loops = [f for f in files if basename(f) in uploaded_loops]

total = len(target_loops)
for i,f in enumerate(target_loops):
    print(f"At {i} of {total}: {f}")
    os.remove(f)

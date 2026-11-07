"""Upload one queued sound to Soundza and push its independent upload history."""

import argparse
import fcntl
import glob
import json
import mimetypes
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile

import requests
from dotenv import load_dotenv
from looplipy import Wav

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / 'data/uploaded_soundza_loops.json'
API = 'https://api.soundza.com/v1'


def sound_title(path):
    """Use the existing loop categories and a short filename hash."""
    stem = path.stem.lower()
    match = re.search(r'([0-9a-f]{32})$', stem)
    if match is None:
        match = re.search(r'([0-9a-f]{8,})$', stem)
    if match is None:
        raise ValueError(f'No filename hash found for sound: {path.name}')
    short_hash = "0x" + match.group(1)[:8]
    if stem.startswith('trk'):
        kind = 'Demo Track' if Wav(str(path)).len() > 60 else 'Short Track'
        return f'{kind} {short_hash}'
    # Remove the hash before looking for category markers.
    prefix = stem[:match.start()]
    category = 'Drum'
    for marker, name in [('amb', 'Ambient'), ('gli', 'Glitch'),
                         ('tri', 'Tribal'), ('noi', 'Noise'), ('hor', 'Horror'),
                         ('dro', 'Drone'), ('brk', 'Breakbeat'), ('har', 'Hardcore'),
                         ('syn', 'Synth'), ('asmr', 'ASMR')]:
        if marker in prefix:
            category = name
    bpm = round(Wav(str(path)).bpm())
    return f'{bpm} BPM Industrial {category} Loop | {short_hash}'


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def sync_history():
    """Retry a previous failed commit/push before accepting another upload."""
    branch = git('symbolic-ref', '--short', 'HEAD')
    path = str(HISTORY.relative_to(ROOT))
    git('add', '--', path)
    if git('diff', '--cached', '--name-only', '--', path):
        # --only keeps unrelated staged changes out of this commit.
        git('commit', '--only', '-m', 'Update Soundza upload history', '--', path)
    git('push', 'origin', f'HEAD:refs/heads/{branch}')


def save_history(history):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=HISTORY.parent,
                                     delete=False) as out:
        temporary = Path(out.name)
        try:
            json.dump(history, out, indent=2, sort_keys=True)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, HISTORY)


def upload_request(stage, method, url, **kwargs):
    try:
        response = method(url, **kwargs)
        response.raise_for_status()
    except requests.RequestException as error:
        response = error.response
        status = response.status_code if response is not None else 'network error'
        message = f'Soundza {stage} failed ({status})'
        if response is not None:
            try:
                body = response.json()
                detail = body.get('error', {}) if isinstance(body, dict) else {}
                code = detail.get('code') if isinstance(detail, dict) else None
            except ValueError:
                code = None
            if code == 'upload_not_enabled':
                message += (': uploading is disabled for this API key. Enable uploading '
                            'and accept the contributor terms at '
                            'https://soundza.com/developers/keys')
            elif code and re.fullmatch(r'[a-z_]{1,80}', str(code)):
                message += f': {code}'
        elif stage == 'sound creation':
            message += '. Check Soundza uploads before retrying; creation may have succeeded'
        # Avoid exposing credentials or signed storage URLs from request exceptions.
        raise ValueError(message) from None
    return response


def upload(path, key, metadata):
    headers = {'Authorization': f'Bearer {key}'}
    response = upload_request('upload URL request', requests.post,
                             f'{API}/uploads', headers=headers, json={
        'file_name': path.name,
        'content_type': metadata['content_type'],
        'size_bytes': metadata['size_bytes'],
    }, timeout=(15, 60))
    presign = response.json()
    content_type = presign.get('content_type', metadata['content_type'])
    if metadata['size_bytes'] > presign.get('max_bytes', float('inf')):
        raise ValueError('Sound exceeds the upload size limit')
    with path.open('rb') as audio:
        # Storage uses the signed URL, never the Soundza API credential.
        upload_request('audio transfer', requests.put, presign['upload_url'], data=audio,
                                headers={'Content-Type': content_type},
                                timeout=(15, 600))
    response = upload_request('sound creation', requests.post,
                             f'{API}/sounds', headers=headers, json={
        **metadata, 'content_type': content_type,
        'upload_key': presign['upload_key'],
    }, timeout=(15, 60))
    result = response.json()
    if not result.get('id'):
        raise ValueError('Soundza did not return a sound ID; check your uploads before retrying')
    return result


def run(dry_run=False):
    load_dotenv(ROOT / '.env')
    queue = os.getenv('queue_glob', '')
    if not queue.strip():
        raise ValueError('Set queue_glob in .env')
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    if not isinstance(history, dict):
        raise ValueError('Soundza upload history must be a JSON object')
    if history and not dry_run:
        sync_history()
    candidates = {
        Path(filename).resolve()
        for pattern in queue.split(';') if pattern.strip()
        for filename in glob.glob(os.path.expanduser(pattern.strip()))
        if Path(filename).is_file() and Path(filename).name not in history
    }
    if not candidates:
        print('All matching sounds have been uploaded to Soundza (or queue is empty)')
        return
    path = random.choice(sorted(candidates))
    content_type = ('audio/wav' if path.suffix.lower() == '.wav'
                    else mimetypes.guess_type(path.name)[0])
    if not content_type or not content_type.startswith('audio/'):
        raise ValueError(f'Unsupported audio type: {path.name}')
    metadata = {
        'file_name': path.name, 'title': sound_title(path),
        'content_type': content_type, 'size_bytes': path.stat().st_size,
        'ai_content': 'NO_AI', 'rights_attested': True,
    }
    if not metadata['size_bytes']:
        raise ValueError(f'Audio file is empty: {path}')
    print(f'Soundza next sound: {path}')
    print(json.dumps(metadata, indent=2))
    if dry_run:
        print(f'Available sounds: {len(candidates)} (dry run; no upload or Git changes)')
        return
    key = os.getenv('soundza_key') or os.getenv('SOUNDZA_API_KEY')
    if not key:
        raise ValueError('Set soundza_key (or SOUNDZA_API_KEY) in .env')
    # Check Git configuration before making an external upload.
    git('symbolic-ref', '--short', 'HEAD')
    git('remote', 'get-url', 'origin')
    result = upload(path, key, metadata)
    history[path.name] = {'id': result['id'], 'status': result.get('status', 'pending')}
    save_history(history)
    print(f"Upload successful; sound ID: {result['id']} (pending review)")
    sync_history()
    print('Soundza history committed and pushed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d', '--dry-run', action='store_true')
    args = parser.parse_args()
    # An advisory lock also prevents two cron invocations choosing the same sound.
    with (ROOT / 'data/.soundza-upload.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run(args.dry_run)
        except BlockingIOError:
            print('Another Soundza uploader is running', file=sys.stderr)
            return 1
        except subprocess.CalledProcessError as error:
            print(f'Git failed: {error.stderr.strip()}. Saved history is retained; '
                  'the next run retries synchronization before uploading.', file=sys.stderr)
            return 1
        except requests.RequestException as error:
            # Do not print signed storage URLs or authorization headers.
            status = error.response.status_code if error.response is not None else 'network error'
            print(f'Soundza upload failed ({status}). If creation timed out, check '
                  'Soundza uploads before retrying.', file=sys.stderr)
            return 1
        except (OSError, ValueError, KeyError) as error:
            print(f'Soundza uploader: {error}', file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

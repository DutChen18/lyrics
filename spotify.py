import webbrowser
import secrets, hashlib, base64
import urllib.parse, urllib.error
import json, web
import os.path, shelve, tempfile
import time

CLIENT_ID = '46e6abb3cb0448ee88ae176a5b2d9c4b'
PORT = 8080

async def auth():
    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_.-~'
    verifier = ''.join(secrets.choice(chars) for _ in range(64))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    challenge = challenge.decode().rstrip('=')

    query = urllib.parse.urlencode({
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': f'http://localhost:{PORT}',
        'code_challenge_method': 'S256',
        'code_challenge': challenge,
        'scope': 'user-read-currently-playing',
    })

    webbrowser.open(f'https://accounts.spotify.com/authorize?{query}')
    response = await web.serve(PORT)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(response.path).query)
    if 'error' in query:
        return None

    query = urllib.parse.urlencode({
        'client_id': CLIENT_ID,
        'grant_type': 'authorization_code',
        'code': query['code'][0],
        'redirect_uri': f'http://localhost:{PORT}',
        'code_verifier': verifier,
    })

    data = await web.open('https://accounts.spotify.com/api/token', query.encode())
    return json.loads(data.decode())

async def refresh(refresh_token):
    query = urllib.parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID,
    })

    data = await web.open('https://accounts.spotify.com/api/token', query.encode())
    return json.loads(data.decode())

async def try_open(access_token, url, data):
    headers = { 'Authorization': f'Bearer {access_token}' }
    return await web.open(url, data, headers)

async def open(url, data=None):
    path = tempfile.gettempdir()
    path = os.path.join(path, 'spotify')

    with shelve.open(path) as db:
        do_refresh = False
        do_refresh = do_refresh or 'access_token' not in db
        do_refresh = do_refresh or 'expires_at' not in db
        do_refresh = do_refresh or time.time() > db['expires_at'] - 60

        if not do_refresh:
            try:
                return await try_open(db['access_token'], url, data)
            except:
                do_refresh = True

        do_auth = False
        do_auth = do_auth or 'refresh_token' not in db

        if not do_auth:
            try:
                tmp = await refresh(db['refresh_token'])
            except:
                do_auth = True

        if do_auth:
            tmp = await auth()

        db['refresh_token'] = tmp['refresh_token']
        db['access_token'] = tmp['access_token']
        db['expires_at'] = tmp['expires_in'] + time.time()

        return await try_open(db['access_token'], url, data)

async def poll():
    data = await open('https://api.spotify.com/v1/me/player/currently-playing')
    if data != b'':
        return json.loads(data.decode())
    else:
        return None
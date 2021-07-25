import asyncio, time
import src, spotify
import sys, os, shutil

TIMEOUT = 10
ANSI_TERM = 'TERM' in os.environ

last_log = ''
last_lines = []
last_index = 0

def render():
    size = shutil.get_terminal_size()
    sys.stdout.write('\033[48;2;0;0;0;38;2;255;0;0m')
    sys.stdout.write(f'\033[1;1H\033[K  {last_log}')
    for i in range(size.lines - 1):
        c = 0.999999 - abs(i * 2 - size.lines + 2) / size.lines
        c = int(c * 256)
        sys.stdout.write(f'\033[48;2;0;0;0;38;2;{c};{c};{c}m')
        sys.stdout.write(f'\033[{i + 2};1H\033[K')
        j = i + last_index - (size.lines - 2) // 2
        if j >= 0 and j < len(last_lines):
            if j == last_index:
                sys.stdout.write(f'> ')
            else:
                sys.stdout.write(f'  ')
            sys.stdout.write(last_lines[j][1][:size.columns - 2])
    sys.stdout.write('\033[1;1H')
    sys.stdout.flush()

def log(string):
    global last_log
    if ANSI_TERM:
        last_log = string
        render()
    else:
        print(f'>>> {string}')

def show(lines, index):
    global last_lines
    global last_index
    if ANSI_TERM:
        last_lines = lines
        last_index = index
        render()
    else:
        print(lines[index][1])

async def main():
    last_key = None
    last_progress = None
    index = 0

    while True:
        data = await spotify.poll()
        while data is None or data['item'] is None:
            log('NO SONG')
            await asyncio.sleep(TIMEOUT)
            data = await spotify.poll()

        poll_time = time.time()
        progress = data['progress_ms'] / 1000
        duration = data['item']['duration_ms'] / 1000
        name = data['item']['name']
        artist = data['item']['artists'][0]['name']
        key = data['item']['id']

        name = name.split(' (')[0]
        name = name.split(' -')[0]

        if key != last_key:
            log(f'NEW SONG: {artist} {name}')
            lyrics = None
            last_key = key
        elif progress == last_progress:
            log('PAUSED')
            await asyncio.sleep(TIMEOUT)
            continue

        last_progress = progress
        
        if lyrics is None:
            lyrics = await src.search(artist, name)
            if lyrics is None:
                log('NO LYRICS')
                await asyncio.sleep(min(TIMEOUT, 1 + duration - progress))
                continue
            lyrics, adjust = src.parse_adjust(lyrics, duration)
            log(f'SYNC: {adjust}')
            index = 0

        max_i = 0
        for tm, tx in lyrics:
            if tm > progress:
                break
            else:
                max_i += 1
        if index > max_i:
            log('REWINDING')
            index = max(0, max_i - 1)
        
        while True:
            prog = time.time() - poll_time + progress
            if index >= len(lyrics):
                await asyncio.sleep(min(TIMEOUT, 1 + duration - prog))
                break
            tm, tx = lyrics[index]
            if tm - prog > 0:
                delta = TIMEOUT - time.time() + poll_time
                if tm - prog > delta:
                    if delta > 0:
                        await asyncio.sleep(delta)
                    break
                await asyncio.sleep(tm - prog)
            show(lyrics, index)
            index += 1

if __name__ == '__main__':
    asyncio.run(main())
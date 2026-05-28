
import yt_dlp
import re
url = 'https://www.facebook.com/facebook/videos/10153231379946729/'
opts = {'quiet': True, 'no_warnings': True}
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=False)
    formats = info.get('formats', [])
    available = {}
    for f in formats:
        if f.get('vcodec') == 'none':
            continue
        w = f.get('width') or 0
        h = f.get('height') or 0
        if not (w and h):
            res_str = f.get('resolution') or f.get('format_id') or ''
            m = re.search(r'(\d+)x(\d+)', res_str)
            if m:
                w = w or int(m.group(1))
                h = h or int(m.group(2))
        if not h:
            fid = str(f.get('format_id', '')).lower()
            if fid == 'hd': h = 720
            elif fid == 'sd': h = 360
            elif '1080' in fid: h = 1080
            elif '720' in fid: h = 720
            elif '480' in fid: h = 480
            elif '360' in fid: h = 360
        if h:
            label_res = min(w, h) if (w and h) else h
            res_key = f'{label_res}p'
            print('Found resolution:', res_key)
            available[res_key] = f

    print('Total available formats found:', len(available))


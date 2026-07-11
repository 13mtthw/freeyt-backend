from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import yt_dlp
import os

app = FastAPI()

# Force absolute execution path matching to eliminate relative location bugs on Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Common HTTP header strategy mimicking verified mobile operating systems
SPOOFED_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Mode': 'navigate'
}

@app.get("/search")
def search_and_stream(q: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'skip_download': True,
        'http_headers': SPOOFED_HEADERS,
        'extractor_args': {
            'youtube': {
                # Drops 'web' protocol entirely, which causes 403 blocks on cloud hosts
                'player_client': ['ios', 'android'],
                'skip': ['dash', 'hls']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{q}", download=False)
            if not info:
                raise HTTPException(status_code=404, detail="No results found")
            
            if 'entries' in info and info['entries']:
                video_data = info['entries'][0]
            else:
                video_data = info

            video_id = video_data.get('id')
            if not video_id:
                raise HTTPException(status_code=404, detail="Video ID missing")

            stream_url = video_data.get('url') or f"https://youtube.com/watch?v={video_id}"

            return {
                "title": video_data.get("title") or q,
                "artist": video_data.get("uploader") or "Unknown Artist",
                "stream_url": stream_url
            }
    except Exception as e:
        print(f"Search Crash Trace: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download")
def download_song(q: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        # Native safe template configuration to protect FFmpeg extraction workflows
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'http_headers': SPOOFED_HEADERS,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android'],
                'skip': ['dash', 'hls']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{q}", download=True)
            if not info:
                raise HTTPException(status_code=404, detail="Track extraction failed")
                
            if 'entries' in info and info['entries']:
                video_data = info['entries'][0]
            else:
                video_data = info
                
            video_id = video_data.get('id')
            video_title = video_data.get('title', 'track')
            if not video_id:
                raise HTTPException(status_code=500, detail="Could not capture video ID properties")
            
            # Clean absolute matching structure
            final_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
            
            if os.path.exists(final_path):
                # Clean characters that cause mobile file systems to discard filenames
                safe_title = "".join([c for c in video_title if c.isalpha() or c.isdigit() or c in ' -_']).strip()
                return FileResponse(
                    final_path, 
                    media_type="audio/mpeg", 
                    filename=f"{safe_title}.mp3"
                )
                
            raise HTTPException(status_code=500, detail=f"File processing failed at: {final_path}")
    except Exception as e:
        print(f"Download Crash Trace: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)

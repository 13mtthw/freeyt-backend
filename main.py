from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import yt_dlp
import os

app = FastAPI()
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/search")
def search_and_stream(q: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'skip_download': True,
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

            stream_url = video_data.get('url') or f"https://youtube.com{video_id}"

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
    # FIXED: Hardcoded outtmpl to remove the confused string token layout rules
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s', # Stripped the complex extension macros
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
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
            if not video_id:
                raise HTTPException(status_code=500, detail="Could not capture video ID properties")
            
            # SAFE ASSET MATCHING: Checks for both the fixed path and your system's literal bug filename
            file_path_fixed = f"{DOWNLOAD_DIR}/{video_id}.mp3"
            file_path_literal_bug = f"{DOWNLOAD_DIR}/{video_id}.%(ext)s.mp3"
            
            final_path = None
            if os.path.exists(file_path_fixed):
                final_path = file_path_fixed
            elif os.path.exists(file_path_literal_bug):
                final_path = file_path_literal_bug
                
            if final_path:
                return FileResponse(final_path, media_type="audio/mpeg")
                
            raise HTTPException(status_code=500, detail=f"File not found. Checked: {file_path_fixed}")
    except Exception as e:
        print(f"Download Crash Trace: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005) 

import os
import shutil
import zipfile
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import imageio_ffmpeg

app = FastAPI()

# Ambil path FFmpeg otomatis dari imageio-ffmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

class DownloadRequest(BaseModel):
    urls: List[str]
    format: str = "mp3"
    quality: str = "medium"

QUALITY_MAP = {
    'low': '64',
    'medium': '128',
    'high': '320'
}

@app.post("/api/download-batch")
async def download_batch(data: DownloadRequest):
    batch_id = os.urandom(4).hex()
    output_dir = f"downloads_{batch_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    bitrate = QUALITY_MAP.get(data.quality.lower(), '128')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': FFMPEG_PATH, # Jalur FFmpeg otomatis
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': data.format,
            'preferredquality': bitrate,
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'noplaylist': True,
    }

    downloaded_files = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in data.urls:
                try:
                    ydl.download([url.strip()])
                except Exception as e:
                    print(f"Gagal download {url}: {e}")
        
        for file in os.listdir(output_dir):
            downloaded_files.append(os.path.join(output_dir, file))
            
        if not downloaded_files:
            shutil.rmtree(output_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail="Tidak ada audio yang berhasil di-download.")

        zip_path = f"output_{batch_id}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in downloaded_files:
                zipf.write(file, os.path.basename(file))
                
        shutil.rmtree(output_dir, ignore_errors=True)
        return FileResponse(zip_path, media_type='application/zip', filename="youtube_audio_batch.zip")

    except Exception as e:
        shutil.rmtree(output_dir, ignore_errors=True)
        if os.path.exists(f"output_{batch_id}.zip"):
            os.remove(f"output_{batch_id}.zip")
        raise HTTPException(status_code=500, detail=str(e))
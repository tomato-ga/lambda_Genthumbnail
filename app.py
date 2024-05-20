import os
import json
import subprocess
from urllib.parse import urlparse, ParseResult
from typing import Dict, Any
import requests
import boto3
from supabase import create_client, Client
from dotenv import load_dotenv

class VideoThumbnailGenerator:
    def __init__(self) -> None:
        load_dotenv()
        
        self.supabase_url: str = os.getenv("SUPABASE_URL")
        self.supabase_key: str = os.getenv("SUPABASE_KEY")
        self.r2_api_token: str = os.getenv("R2_API_TOKEN")
        self.r2_bucket_name: str = os.getenv("R2_BUCKET_NAME")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.r2_endpoint_url: str = f'https://{os.getenv("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com'

    def download_video(self, url: str) -> str:
        result = subprocess.run(['yt-dlp', '-o', 'video.mp4', url], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to download video: {result.stderr}")
        return 'video.mp4'

    def download_file(self, url: str) -> str:
        response = requests.get(url)
        video_path = 'video.mp4'
        with open(video_path, 'wb') as f:
            f.write(response.content)
        return video_path

    def generate_thumbnail(self, video_path: str, frame_time: int = 5) -> str:
        thumbnail_path = 'thumbnail.jpg'
        result = subprocess.run(['ffmpeg', '-i', video_path, '-ss', str(frame_time), '-vframes', '1', thumbnail_path], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to generate thumbnail: {result.stderr}")
        return thumbnail_path

    def upload_to_r2(self, file_path: str, file_name: str) -> str:
        s3 = boto3.client('s3', 
                          endpoint_url=self.r2_endpoint_url,
                          aws_access_key_id='', 
                          aws_secret_access_key='', 
                          aws_session_token=self.r2_api_token)
        bucket = self.r2_bucket_name

        with open(file_path, 'rb') as f:
            s3.upload_fileobj(f, bucket, file_name)

        file_url = f"https://{bucket}.r2.cloudflarestorage.com/{file_name}"
        return file_url

    def update_database(self, video_id: int, thumbnail_url: str) -> Dict[str, Any]:
        response = self.supabase.table('videos').update({'thumbnail_url': thumbnail_url}).eq('id', video_id).execute()
        return response.data

    def process_video(self, video_url: str) -> Dict[str, str]:
        parsed_url: ParseResult = urlparse(video_url)

        if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
            video_path = self.download_video(video_url)
        else:
            video_path = self.download_file(video_url)

        thumbnail_path = self.generate_thumbnail(video_path)
        video_id = 1  # 実際にはデータベースから取得したIDを使うべき
        thumbnail_url = self.upload_to_r2(thumbnail_path, f"thumbnails/{video_id}.jpg")
        self.update_database(video_id, thumbnail_url)

        os.remove(video_path)
        os.remove(thumbnail_path)

        return {'thumbnail_url': thumbnail_url}

def lambda_handler(event, context):
    generator = VideoThumbnailGenerator()
    body = json.loads(event['body'])
    video_url = body.get('videoUrl')
    
    if not video_url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'videoUrl is required'})
        }

    try:
        result = generator.process_video(video_url)
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

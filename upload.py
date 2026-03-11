
#!/usr/bin/env python3
"""
Main automation script:
- Downloads next unused video from Google Drive.
- Generates metadata via Gemini.
- Uploads to YouTube with schedule.
- Moves video to "uploaded" folder in Drive.
"""
import os
import sys
import tempfile
from dotenv import load_dotenv

from src.utils import setup_logging, get_scheduled_publish_time
from src.drive_client import GoogleDriveClient
from src.gemini_client import GeminiClient
from src.youtube_client import YouTubeClient

# Load environment variables
load_dotenv()

# Configuration from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SOURCE_FOLDER_ID = os.getenv("SOURCE_FOLDER_ID")
UPLOADED_FOLDER_ID = os.getenv("UPLOADED_FOLDER_ID")
YOUTUBE_SCHEDULE_TIME = os.getenv("YOUTUBE_SCHEDULE_TIME", "14:00")  # Default 14:00 UTC
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

# Validate required variables
required_vars = [GEMINI_API_KEY, SOURCE_FOLDER_ID, UPLOADED_FOLDER_ID]
if not all(required_vars):
    sys.exit("Missing required environment variables. Check .env file.")

logger = setup_logging()


def main():
    logger.info("Starting YouTube auto-upload process")

    # 1. Initialize clients
    try:
        drive = GoogleDriveClient(token_file=TOKEN_FILE, client_secret_file=CLIENT_SECRET_FILE)
        gemini = GeminiClient(GEMINI_API_KEY)
        youtube = YouTubeClient(token_file=TOKEN_FILE, client_secret_file=CLIENT_SECRET_FILE)
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        sys.exit(1)

    # 2. Find next video file in source folder
    logger.info(f"Listing video files in Drive folder: {SOURCE_FOLDER_ID}")
    videos = drive.list_video_files(SOURCE_FOLDER_ID)
    if not videos:
        logger.info("No video files found. Exiting.")
        return

    video = videos[0]  # oldest first
    file_id = video["id"]
    file_name = video["name"]
    logger.info(f"Selected video: {file_name} (ID: {file_id})")

    # 3. Download video to temporary location
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file_name)[1], delete=False) as tmp:
        local_path = tmp.name
    logger.info(f"Downloading to {local_path}")
    try:
        drive.download_file(file_id, local_path)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        os.unlink(local_path)
        sys.exit(1)

    # 4. Generate metadata with Gemini
    logger.info("Generating metadata from filename")
    try:
        metadata = gemini.generate_metadata(file_name)
        title = metadata["title"]
        description = metadata["description"]
        tags = metadata["tags"]
        logger.info(f"Generated title: {title}")
    except Exception as e:
        logger.error(f"Metadata generation failed: {e}")
        os.unlink(local_path)
        sys.exit(1)

    # 5. Upload to YouTube with schedule
    logger.info("Uploading to YouTube")
    try:
        publish_time = get_scheduled_publish_time(YOUTUBE_SCHEDULE_TIME)
        logger.info(f"Scheduled publish at: {publish_time}")
        video_id = youtube.upload_video(
            video_path=local_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status="private",   # scheduled uploads must be private/unlisted initially
            publish_at=publish_time
        )
        logger.info(f"YouTube upload successful. Video ID: {video_id}")
    except Exception as e:
        logger.error(f"YouTube upload failed: {e}")
        os.unlink(local_path)
        sys.exit(1)

    # 6. Move file to uploaded folder in Drive
    logger.info(f"Moving file {file_id} to uploaded folder {UPLOADED_FOLDER_ID}")
    try:
        drive.move_file(file_id, UPLOADED_FOLDER_ID)
    except Exception as e:
        logger.error(f"Move failed: {e}")
        # Not fatal, but log it

    # 7. Cleanup temp file
    os.unlink(local_path)
    logger.info("Process completed successfully.")


if __name__ == "__main__":
    main()
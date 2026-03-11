#!/usr/bin/env python3
"""
Main automation script:
- Downloads next unused videos from Google Drive.
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

# Two upload times (UTC)
# 8:01 AM BD = 02:01 UTC
# 7:00 PM BD = 13:00 UTC
YOUTUBE_SCHEDULE_TIMES = os.getenv("YOUTUBE_SCHEDULE_TIMES", "02:01,13:00")
SCHEDULE_TIMES = YOUTUBE_SCHEDULE_TIMES.split(",")

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

# Validate required variables
required_vars = [GEMINI_API_KEY, SOURCE_FOLDER_ID, UPLOADED_FOLDER_ID]
if not all(required_vars):
    sys.exit("Missing required environment variables. Check .env file.")

logger = setup_logging()


def main():
    logger.info("Starting YouTube auto-upload process")

    # 1️⃣ Initialize API clients
    try:
        drive = GoogleDriveClient(
            token_file=TOKEN_FILE,
            client_secret_file=CLIENT_SECRET_FILE
        )

        gemini = GeminiClient(GEMINI_API_KEY)

        youtube = YouTubeClient(
            token_file=TOKEN_FILE,
            client_secret_file=CLIENT_SECRET_FILE
        )

    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        sys.exit(1)

    # 2️⃣ Find video files in Drive
    logger.info(f"Listing video files in Drive folder: {SOURCE_FOLDER_ID}")

    videos = drive.list_video_files(SOURCE_FOLDER_ID)

    if not videos:
        logger.info("No video files found. Exiting.")
        return

    # Limit videos to number of schedule slots
    videos = videos[:len(SCHEDULE_TIMES)]

    for i, video in enumerate(videos):

        file_id = video["id"]
        file_name = video["name"]

        logger.info(f"Selected video: {file_name} (ID: {file_id})")

        # 3️⃣ Download video
        with tempfile.NamedTemporaryFile(
            suffix=os.path.splitext(file_name)[1],
            delete=False
        ) as tmp:

            local_path = tmp.name

        logger.info(f"Downloading to {local_path}")

        try:
            drive.download_file(file_id, local_path)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            os.unlink(local_path)
            continue

        # 4️⃣ Generate metadata using Gemini
        try:
            metadata = gemini.generate_metadata(file_name)

            title = metadata["title"]
            description = metadata["description"]
            tags = metadata["tags"]

            logger.info(f"Generated title: {title}")

        except Exception as e:
            logger.error(f"Metadata generation failed: {e}")
            os.unlink(local_path)
            continue

        # 5️⃣ Schedule publish time
        publish_time = get_scheduled_publish_time(SCHEDULE_TIMES[i])

        logger.info(f"Scheduled publish at: {publish_time}")

        # 6️⃣ Upload video to YouTube
        try:
            video_id = youtube.upload_video(
                video_path=local_path,
                title=title,
                description=description,
                tags=tags,
                privacy_status="private",
                publish_at=publish_time
            )

            logger.info(f"YouTube upload successful. Video ID: {video_id}")

        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            os.unlink(local_path)
            continue

        # 7️⃣ Move video to uploaded folder
        logger.info(
            f"Moving file {file_id} to uploaded folder {UPLOADED_FOLDER_ID}"
        )

        try:
            drive.move_file(file_id, UPLOADED_FOLDER_ID)

        except Exception as e:
            logger.error(f"Move failed: {e}")

        # 8️⃣ Cleanup temp file
        os.unlink(local_path)

    logger.info("Process completed successfully.")


if __name__ == "__main__":
    main()
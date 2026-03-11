
from google import genai
from typing import Dict


class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def generate_metadata(self, filename: str) -> Dict[str, str]:
        """
        Generate YouTube title, description, and hashtags based on the filename.
        Returns dict with keys: title, description, tags (comma-separated string).
        """
        # Extract base name without extension and replace underscores with spaces
        topic = filename.rsplit(".", 1)[0].replace("_", " ").strip()

        prompt = f"""
        Based on the video topic: "{topic}", generate:
        1. An engaging YouTube video title (max 100 characters)
        2. A compelling video description (2-3 sentences, include relevant details)
        3. 10 relevant hashtags (comma separated, no spaces, starting with #)

        Format your response exactly as:
        Title: <title>
        Description: <description>
        Hashtags: <hashtag1,hashtag2,...>
        """

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = response.text

        # Parse response
        lines = text.strip().split("\n")
        result = {}
        for line in lines:
            if line.startswith("Title:"):
                result["title"] = line.replace("Title:", "").strip()
            elif line.startswith("Description:"):
                result["description"] = line.replace("Description:", "").strip()
            elif line.startswith("Hashtags:"):
                hashtags = line.replace("Hashtags:", "").strip()
                # Ensure no spaces inside tags, but keep commas
                hashtags = ",".join([tag.strip() for tag in hashtags.split(",")])
                result["tags"] = hashtags

        # Fallbacks if parsing fails
        result.setdefault("title", topic)
        result.setdefault("description", f"Check out this video about {topic}.")
        result.setdefault("tags", "#video")

        return result
import google.generativeai as genai
import os

GEMINI_API = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API)

model = genai.GenerativeModel("gemini-pro")

prompt = """
Create a YouTube Shorts title,
caption and 10 hashtags for a nature timelapse video.
"""

response = model.generate_content(prompt)

print(response.text)

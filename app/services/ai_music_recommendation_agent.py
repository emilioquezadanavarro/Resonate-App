import os
import ast
from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.services.user_service import UserService

# 1. Load the GEMINI secret API key
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class MusicRecommendationAgent:

    @staticmethod
    def music_recommendation(content, mood_labels, ai_summary, age, gender, user_name, excluded_songs):
        """
            Generates music recommendations based on journal analysis, age and gender.

            Args:
                content (str): The journal text.
                mood_labels (list): Detected moods.
                ai_summary (str): The summary of the day.
                age: The age of the user
                gender: The gender of the user
                user_name: The name of the user
                excluded_songs (list): A list of song titles to AVOID (Blacklist).
        """

        print(f"🎸 Looking for music recommendations for User: {user_name} / Age: {age} / Gender: {gender}")

        try:
            # Join the moods (e.g., "Sad, Anxious")
            moods_str = ", ".join(mood_labels)

            # Build the Blacklist Warning
            blacklist_instruction = ""
            if excluded_songs:
                black_list_str = ", ".join(excluded_songs)
                blacklist_instruction = (
                    f"\nIMPORTANT CONSTRAINT: The user has recently heard these songs: [{black_list_str}]. "
                    "Do NOT recommend them again. Choose different tracks."
                )

            # Construct the User Message (The Context)
            user_message = (
                f"Journal content: \"{content}\"\n"
                f"Detected Moods: {moods_str}\n"
                f"Summary: {ai_summary}\n"
                f"Age: {age}\n"
                f"Gender: {gender}\n"
                f"{blacklist_instruction}\n\n"
                "Based on this, suggest 3 songs..."
            )

            # The Persona (System Prompt)
            system_instruction = (
                "You are an expert Music Curator. "
                "Your goal is to recommend a playlist based on the user's emotional state, age and gender. "
                "Task: Recommend exactly 3 songs that match this mood. "
                "Format: Return ONLY a raw Python list of dictionaries. "
                "Example: [{'title': 'Song Name', 'artist': 'Artist Name', 'reason': 'Why it fits'}] "                
                "Do not use Markdown formatting. Just the raw list."
            )

            # API Call
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=1 # Creative music picks
                ),
                contents=user_message
            )

            # Clean response
            raw_text = response.text.strip()

            # Remove markdown code blocks if Gemini adds them accidentally
            if raw_text.startswith("```"):
                # Finds the first newline and the last newline to strip the ```python lines
                lines = raw_text.split('\n')
                # If the first line is ```python, remove it and the last line
                if lines[0].strip().startswith("```"):
                    raw_text = "\n".join(lines[1:-1])

            # Convert String -> Python List
            recommendations = ast.literal_eval(raw_text)

            # Final Check: Is it actually a list?
            if isinstance(recommendations, list):
                return recommendations # Returns a real List!
            else:
                return []

        except Exception as e:
            print(f" Music recommendation agent error ❌ : {e}")
            return []
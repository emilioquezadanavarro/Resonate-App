import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Load the GEMINI secret API key
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class AIRecommendation:

    @staticmethod
    def music_recommendation(content, mood_labels, ai_summary):

        try:
            # Join the moods (e.g., "Sad, Anxious")
            moods_str = ", ".join(mood_labels)

            # Construct the User Message (The Context)
            user_message = (
                f"Journal Entry:\n{content}\n\n"
                f"User Moods: {moods_str}\n\n"
                f"Psychological Summary: {ai_summary}"
                )

            # The Persona (System Prompt)
            system_instruction = (
                "You are an expert Music Curator. "
                "Your goal is to recommend a playlist based on the user's emotional state, "
                "using their journal entry and psychological summary as context. "
                "Do not repeat songs and always give new recommendations. "
                "Task: Recommend exactly 3 songs that perfectly match this mood. "
                "Output Format: A simple numbered list (e.g., '1. Artist - Song'). "
                "Constraint: Do not provide URLs. Do not provide intro text. Just the list."
            )

            # API Call
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction),
                contents=user_message
            )

            return response.text

        except Exception as e:
            print(f" Music recommendation Error ❌ : {e}")
            return "No music found for this entry."
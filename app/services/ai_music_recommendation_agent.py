import os
import ast
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.services.user_service import UserService
from langfuse import get_client

# Load the GEMINI secret API key
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Langfuse
langfuse = get_client()

class MusicRecommendationAgent:

    def __init__(self, name="Shaka"):

        print(f"Initializing Music Recommendation Agent {name} ... 🤖 🎹")

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

        # Start the Main Span - Langfuse
        with langfuse.start_as_current_observation(
                as_type="span",
                name="Music Recommendation Agent",
                input={
                    "content": content,
                    "moods": mood_labels,
                    "summary": ai_summary,
                    "user_profile": {"name": user_name, "age": age, "gender": gender},
                    "excluded_songs": excluded_songs
                }
        ) as span:

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
                    "Example: [{\"title\": \"Song Name\", \"artist\": \"Artist Name\", \"reason\": \"Why it fits\"}] "
                    "CRITICAL: Use double quotes (\") for all keys and values. Escape any double quotes inside the text. "
                    "Do not use Markdown formatting. Just the raw list."
                )

                # Start the Generation (The LLM Call)
                with langfuse.start_as_current_observation(
                        as_type="generation",
                        name="Gemini Playlist Generation",
                        model="gemini-2.5-flash",  # CRITICAL: Exact model name for pricing
                        input={"system": system_instruction, "user": user_message}
                ) as generation:

                    # API Call
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=1, # Creative music picks
                        ),
                        contents=user_message
                    )

                    # Clean response
                    raw_text = response.text.strip()
                    print(f"\n RAW GEMINI OUTPUT: {raw_text}\n")

                    # Extract Google Tokens and Map to Langfuse Format
                    # We use .get() safely in case Gemini doesn't return usage data for some reason
                    prompt_tokens = 0
                    completion_tokens = 0
                    total_tokens = 0

                    if response.usage_metadata:
                        prompt_tokens = response.usage_metadata.prompt_token_count
                        completion_tokens = response.usage_metadata.candidates_token_count
                        total_tokens = response.usage_metadata.total_token_count

                    generation.update(
                        output=raw_text,
                        usage={
                            "promptTokens": prompt_tokens,
                            "completionTokens": completion_tokens,
                            "totalTokens": total_tokens
                        }
                    )


                # Remove markdown code blocks if Gemini adds them accidentally
                if raw_text.startswith("```"):
                    raw_text = raw_text.strip("`").removeprefix("json").removeprefix("python").strip()

                recommendations = []

                try:
                    recommendations = json.loads(raw_text)
                except json.decoder.JSONDecodeError as e:
                    print(f"⚠️ JSON Parsing Error: {e}")

                # Convert String -> Python List
                #recommendations = ast.literal_eval(raw_text)

                # Final Check: Is it actually a list?
                if isinstance(recommendations, list):
                    # Update the span with the final clean list
                    span.update(output=recommendations)
                    langfuse.flush()
                    return recommendations # Returns a real List!
                else:
                    span.update(level="WARNING", status_message="Output was not a list")
                    langfuse.flush()
                    return []

            except Exception as e:
                print(f" Music recommendation agent error ❌ : {e}")
                span.update(level="ERROR", metadata={"error": str(e)})
                langfuse.flush()
                return []

# Create the Singleton Instance
music_recommendation_agent = MusicRecommendationAgent()
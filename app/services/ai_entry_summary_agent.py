import os
from openai import OpenAI
from dotenv import load_dotenv

# 1. Load the secret key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class SummaryAgent:

    @staticmethod
    def analyze_sentiment(content, mood_labels):
        """
        Reads the journal entry and returns an empathetic summary.
        """
        try:
            # Join the moods (e.g., "Sad, Anxious")
            moods_str = ", ".join(mood_labels)

            # 2. The Persona (System Prompt)
            system_instruction = (
                "You are an empathetic and insightful mental health assistant. "
                "Read the user's journal entry and their selected mood tags. "
                "Write a short, warm summary (3-5 sentences) validation their feelings. "
                "Speak directly to the user ('You seem to be feeling...')."
            )

            user_message = f"User Moods: {moods_str}\n\nJournal Entry:\n{content}"

            # 3. Call OpenAI
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7     # Adds a little creativity/warmth
            )

            # 4. Return just the text summary
            return response.choices[0].message.content

        except Exception as e:
            print(f"❌ Summary Agent Error ❌: {e}")
            return "I'm having trouble connecting to my brain right now, but I hear you."
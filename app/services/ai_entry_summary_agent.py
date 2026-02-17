import os
from openai import OpenAI
from dotenv import load_dotenv
from langfuse import get_client

# 1. Load the secret key
load_dotenv()

# Initialize
langfuse = get_client()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class SummaryAgent:

    def __init__(self, name="Milo"):

        print(f"Initializing Summary Agent {name} ... 🤖 📝")

    @staticmethod
    def analyze_sentiment(content, mood_labels):
        """
        Reads the journal entry and returns an empathetic summary.
        """

        # Langfuse - Start the Span
        with langfuse.start_as_current_observation(
            as_type="span",
            name="Summary Agent",
            input={"content": content, "moods": mood_labels}
        ) as span:

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

                # Create the nested generation
                # Log the combined prompt as the input for the generation
                with langfuse.start_as_current_observation(
                        as_type="generation",
                        name="Summary Generation",
                        model="gpt-4o-mini",
                        input={"system": system_instruction, "user": user_message}
                ) as generation:

                    # 3. Call OpenAI
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0.7,     # Adds a little creativity/warmth
                        max_tokens=250
                    )

                    summary = response.choices[0].message.content

                    # Update the generation with tokens
                    generation.update(
                        output=summary,
                        usage={
                            "promptTokens": response.usage.prompt_tokens,
                            "completionTokens": response.usage.completion_tokens,
                            "totalTokens": response.usage.total_tokens
                        }
                    )

                # Update the parent span and flush
                span.update(output=summary)
                langfuse.flush()

                # 4. Return just the text summary
                return summary

            except Exception as e:
                span.update(level="ERROR", metadata={"error": str(e)})
                print(f"❌ Summary Agent Error ❌: {e}")
                langfuse.flush()
                return "I'm having trouble connecting to my brain right now, but I hear you."

# Create the Singleton Instance
summary_agent = SummaryAgent()
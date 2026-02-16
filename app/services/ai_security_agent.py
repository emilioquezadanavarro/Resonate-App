import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class SecurityAgent:
    """
        The Gatekeeper.
        Classifies text into SAFE, CRISIS, or TOXIC before it enters the system.

    """

    def __init__(self, name="Kanon"):

        print(f"Initializing Security Agent {name} ... 🤖 🛡️")

    @staticmethod
    def check_safety(user_text):
        """
        Returns:
        - "SAFE": Allow entry.
        - "CRISIS": Redirect to Help Resources (Do not save).
        - "TOXIC": Block entry with warning (Do not save).
        - "ERROR": Fail closed (Block entry).
        """

        system_prompt = """
                You are a Content Safety Classifier for a journaling app.
                Classify the text into exactly one category:

                1. CRISIS
                - User expresses active intent of self-harm, suicide, or immediate medical danger.

                2. TOXIC
                - Hate speech, racial slurs, sexism, or promoting violence against others.
                - DO NOT flag swearing, venting, or complaining about life/people as TOXIC.
                - DO NOT flag descriptions of experiencing discrimination as TOXIC.

                3. SAFE
                - Everything else (sadness, anger, joy, anxiety, neutral).

                Output ONLY the category name.
                """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                temperature=0,
                max_tokens=10
            )

            result = response.choices[0].message.content.strip().upper()
            print(f"Security Agent response: {result}")

            # Validation: Ensure the AI didn't hallucinate a new category
            if result not in ["SAFE", "CRISIS", "TOXIC"]:
                print(f"Bouncer confused: {result}")
                return "ERROR"

            return result

        except Exception as e:
            print(f"Bouncer Error: {e}")
            return "ERROR"

# Create the Singleton Instance
security_agent = SecurityAgent()
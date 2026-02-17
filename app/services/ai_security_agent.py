import os
from openai import OpenAI
from dotenv import load_dotenv
from langfuse import get_client

load_dotenv()
langfuse = get_client()

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
        - "INVALID": Block & Ask user to try again (Do not save).
        - "ERROR": Fail closed (Block entry).
        """

        print("🛡️🛡️ Kanon, the security guard is checking the entry ... 🛡️🛡️")

        # Langfuse - Start the Span
        with langfuse.start_as_current_observation(
                as_type="span",
                name="Security Agent",
                input={"content": user_text}
        ) as span:

            system_prompt = """
                    You are a Content Safety Classifier for a journaling app.
                    Classify the text into exactly one category:
    
                    1. CRISIS
                    - User expresses active intent of self-harm, suicide, or immediate medical danger.
    
                    2. TOXIC
                    - Hate speech, racial slurs, sexism, or promoting violence against others.
                    - DO NOT flag swearing, venting, or complaining about life/people as TOXIC.
                    - DO NOT flag descriptions of experiencing discrimination as TOXIC.
                    
                    3. INVALID
                    - Flag text as INVALID if it consists of random characters, keysmashing (e.g., 'asdfghjkl'), repetitive nonsense, or has no linguistic meaning.
    
                    4. SAFE
                    - Everything else (sadness, anger, joy, anxiety, neutral).
    
                    Output ONLY the category name.
                    """

            # Langfuse - Start the Generation (The "File" for the AI cost)
            with langfuse.start_as_current_observation(
                    as_type="generation",
                    name="Security Agent Category Response",
                    model="gpt-4o-mini",
                    input={"system": system_prompt, "user": user_text}
            ) as generation:

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
                    if result not in ["SAFE", "CRISIS", "TOXIC", "INVALID"]:
                        print(f"Bouncer confused: {result}")
                        return "ERROR"

                    # Update the generation with tokens
                    generation.update(
                        output=result,
                        usage={
                            "promptTokens": response.usage.prompt_tokens,
                            "completionTokens": response.usage.completion_tokens,
                            "totalTokens": response.usage.total_tokens
                            }
                        )

                    # Update the parent span and flush
                    span.update(output=result)
                    langfuse.flush()

                    return result

                except Exception as e:
                    print(f"Bouncer Error: {e}")
                    return "ERROR"

# Create the Singleton Instance
security_agent = SecurityAgent()
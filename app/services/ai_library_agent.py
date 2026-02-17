from app.services.ai_judge_agent import judge_agent

import os
import ast
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langfuse import get_client
from langchain_community.callbacks import get_openai_callback

# 1. Load keys & Initialize Langfuse
load_dotenv()
langfuse = get_client()

class LibraryAgent:
    """
    The Book Selector (The Generator).

    It works in a loop with the Judge to find the best recommendation.

    """
    def __init__(self, name="Aioros"):

        print(f"Initializing Library Agent {name} ... 🤖 📚")

        # The Brain
        # Initialize the generic OpenAI model.

        self.llm = ChatOpenAI(
            model="gpt-4o-mini", # Fast, smart enough and cheap
            temperature=0.7, # Slightly creative to find interesting books.
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # The Output Parser
        # This acts like a 'translator' that forces the AI to speak in String
        self.parser = StrOutputParser()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", f"""
            You are The Librarian, a wise and empathetic Bibliotherapist named {name}
            Your goal is to prescribe literature to help people navigate their emotions.
            
            USER PROFILE:
            - Age: {{age}}
            - Gender: {{gender}}

            INSTRUCTIONS:
            1. Recommend 2 distinct items based on the user's emotion, {{age}} and {{gender}}
            2. **Tailor your choices**: 
               - For younger users (18-25), consider modern voices or coming-of-age classics.
               - For older users, consider mature, reflective, or deep philosophical works.
            3. **CRITICAL FORMAT**: Do not write a paragraph. Return ONLY a raw Python list of dictionaries.
            4. Structure: [{{{{ "title": "Title", "author": "Author", "reason": "One sentence explanation" }}}}]            
            5. CRITICAL: Use double quotes (") for all keys and values. Escape any double quotes inside the text.
            6. Do not use Markdown formatting (no ```python). Just the raw list.
            7. Be specific. Avoid generic self-help unless it's a perfect match.
            
            CONSTRAINT:
            {{blacklist_instruction}}

            CRITICAL INSTRUCTION (THE REFLEXION LOOP):
            You have a strict Editor (The Judge) reviewing your work. 
            If you receive FEEDBACK from the Judge below, you MUST adjust your recommendations to fix the specific errors mentioned.
            - If the Judge says "Fake Book", find a real one.
            - If the Judge says "Too Generic", find a deeper, less common recommendation.
            """),

            ("human", """
            USER EMOTION: {emotion}

            PREVIOUS CRITIC FEEDBACK (If any):
            {feedback}

            Generate your best recommendations now.
            """)
        ])

        # The Assembler (The Chain)
        self.chain = self.prompt | self.llm | self.parser

    def get_recommendations(self, emotion: str, age: int, gender: str, excluded_books=[]) -> list:
        """
        The public method called by Camus.
        It runs the Reflexion Loop.

        """

        print(f"📚📚 Aioros, the library agent is looking for book recommendations 📚📚")

        # Start the Main Span (The Whole Process)
        with langfuse.start_as_current_observation(
            as_type="span",
            name="Library Agent Recommendations",
            input={
                "emotion": emotion,
                "age": age,
                "gender": gender,
                "excluded_books": excluded_books
            }
        ) as span:

            # Build the Blacklist Instruction String
            blacklist_instruction = ""
            if excluded_books:
                black_list_str = ", ".join(excluded_books)
                blacklist_instruction = (
                    f"\nIMPORTANT CONSTRAINT: The user has recently read these books: [{black_list_str}]. "
                    "Do not recommend them again. Find different literature."
                )

            # Initialize Loop Variables
            feedback = ""
            clean_draft = None
            max_retries = 3

            print(f"\n🔄 REFLEXION LOOP STARTED for emotion: '{emotion}'")

            for attempt in range(max_retries):
                print(f"   --- Attempt {attempt + 1}/{max_retries} ---")

                # Start a Generation for THIS specific attempt
                # We name it dynamically (Attempt 1, Attempt 2...)
                with langfuse.start_as_current_observation(
                        as_type="generation",
                        name=f"Book Generation (Attempt {attempt + 1})",
                        model="gpt-4o-mini",
                        input={"feedback": feedback}  # Log what feedback we gave the AI
                ) as generation:

                    # Capture tokens with the callback
                    with get_openai_callback() as callback:

                        # Generate Draft (Using the Chain)
                        # We pass 'feedback' (which is empty on the first run)
                        draft = self.chain.invoke({
                            "emotion": emotion,
                            "age": age,
                            "gender": gender,
                            "feedback": feedback,
                            "blacklist_instruction": blacklist_instruction
                        })

                    # Update Langfuse with the AI's raw text and cost
                    generation.update(
                        output=draft,
                        usage={
                            "promptTokens": callback.prompt_tokens,
                            "completionTokens": callback.completion_tokens,
                            "totalTokens": callback.total_tokens
                        }
                    )


                # Clean up markdown if the AI added it (e.g. ```python ... ```)
                clean_draft = draft.strip()
                if clean_draft.startswith("```"):
                    # Remove first and last lines (the backticks)
                    lines = clean_draft.split('\n')
                    if len(lines) > 2:
                        clean_draft = "\n".join(lines[1:-1])


                # Call the Judge
                # We send the draft to the agent
                judgment = judge_agent.evaluate(emotion, clean_draft)

                score = judgment.get('score', 0)
                critique = judgment.get('feedback', 'No feedback')

                print(f"⚖️ Saga's Score: {score}/5")
                print(f"📝 Saga's Feedback: {critique}")

                # Decide
                if score >= 4:

                    print("Draft Approved ✅!")

                    # PARSING MOMENT: Convert String -> Real Python List
                    try:
                        real_book_list = ast.literal_eval(clean_draft)
                        if isinstance(real_book_list, list):
                            # Update the main span with the final result
                            span.update(output=real_book_list)
                            langfuse.flush()
                            return real_book_list
                        else:
                            print("⚠️ AI output was not a list.")
                            # If it failed to be a list, force a retry via feedback
                            feedback = "System Error: Output was not a valid Python list."
                    except Exception as e:
                        print(f"⚠️ Parsing Error: {e}")
                        feedback = "System Error: Output syntax was invalid Python."
                else:
                    # Update feedback for the next loop iteration
                    feedback = f"Saga's Feedback: {critique}"

                # 5. Fallback
                # If we ran out of retries, return the last draft anyway (better than nothing)
            print("Max retries reached ⚠️")

            # Try to return the last attempt anyway
            # Even if the Judge didn't love it (e.g. score 3), it might still be a valid list.
            if clean_draft:
                try:
                    print("Attempting to parse the final draft as a fallback...")
                    real_book_list = ast.literal_eval(clean_draft)

                    if isinstance(real_book_list, list):

                        span.update(output=real_book_list, level="WARNING")
                        langfuse.flush()
                        print("Fallback successful. Returning imperfect list. 🤷‍♂️")
                        return real_book_list

                except Exception as e:
                    print(f"Fallback failed. syntax was broken: {e}")

            # If everything truly failed (syntax errors), then return empty.
            span.update(output=[], level="ERROR", status_message="Failed to generate valid list")
            langfuse.flush()
            return []

# Create the Singleton Instance
library_agent = LibraryAgent()


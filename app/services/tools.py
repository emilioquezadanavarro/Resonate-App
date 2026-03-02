from app.services.vector_engine import vector_engine
from langchain.tools import tool
from app.services.ai_library_agent import library_agent
from app.services.past_recommendation_service import PastRecommendationService
from app.services.user_service import UserService

@tool # LangChain Tool Object
def search_journal_memory(query_text: str, user_id: int, result_limit: int = 3) -> str:
    """
    Use this tool to search the user's past journal entries for specific context.

    Args:
        query_text: The specific keywords or concept to search for (e.g., "Japan trip", "anxiety").
        user_id: The targeted user's ID.
        result_limit: The number of entries to retrieve.
                      - DEFAULT to 3 for specific questions (e.g., "What did I eat?").
                      - INCREASE to 10 ONLY for broad summaries (e.g., "Summarize my week").
                      - INCREASE to 1000 ONLY for counting entries (e.g., "How many entries do I have?").
    """

    # FORCE STRING
    # ChromaDB metadata is usually stored as strings.
    # Even if the agent sends an Int, we convert it here to match the database.
    user_id_str = str(user_id)

    # DEBUG PRINTS
    print(f"\n--- DEBUG TOOL ---")
    print(f" Searching for: '{query_text}'")
    print(f" Target User ID: {user_id_str} (Converted to String)")
    print(f" Limit: {result_limit}")

    # Run the search using the STRING version
    results = vector_engine.search_similar(
        query_text,
        user_id_str,
        limit=result_limit
    )

    # DEBUG RESULTS
    print(f" Found {len(results) if results else 0} results.")

    if results:
        response = ""
        for doc in results:
            print(f"Doc Content: {doc.page_content}")
            response += f" - [Entry]: {doc.page_content}\n"

        print(f"--- END DEBUG ---\n")
        return response

    else:
        print(f"--- END DEBUG ---\n")
        return "No memories found"


@tool
def consult_librarian(emotion_or_topic: str, user_id: int) -> str:
    """
    Use this tool ONLY when the user asks for books, articles, or reading recommendations.

    Args:
        emotion_or_topic: The specific feeling or topic (e.g. "Anxiety", "Grief").
        user_id: The ID of the user asking for recommendations.

    """

    print(f"📚 Tool triggered: Consulting Librarian for topic: '{emotion_or_topic}'")

    try:

        user = UserService.get_user_by_id(int(user_id))

        if user:
            age = user.age
            gender = user.gender
        else:
            age = 30
            gender = "Neutral"

        print(f"   -> User Profile Found: User ID {user_id}, Name: {user.username}, Age: {age}, Gender: {gender}")

        # Get history (The Blacklist)
        excluded_books = PastRecommendationService.get_recent_recommendations(
            user_id=user_id,
            item_type="book"
        )

        # Call the library agent
        # Returns a LIST of dicts: [{'title': '...', 'author': '...'}]
        recommendations_list = library_agent.get_recommendations(
            emotion=emotion_or_topic,
            age=age,
            gender=gender,
            excluded_books=excluded_books
        )

        # Save to history (If there are results)
        if recommendations_list:
            PastRecommendationService.save_recommendations(
                user_id=user_id,
                items=recommendations_list,
                item_type="book",
                journal_id=None,  # It's a chat, not a journal entry, so we can leave it NULL or 0
            )
            print("✅ Book recommendations saved to history.")

            # Format for Camus (List -> String)
            # Camus (the chat bot) expects text back, not a list.
            response_text = "Here are the suggestions from the Librarian:\n"
            for item in recommendations_list:
                response_text += f"- {item.get('title')} by {item.get('author')}: {item.get('reason')}\n"

            return response_text

        return "The Librarian could not find any suitable books right now."

    except Exception as e:
        print(f"❌ Librarian Tool Error: {e}")
        return "I'm having trouble connecting to the library services."
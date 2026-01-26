from app.services.vector_engine import vector_engine
from langchain.tools import tool

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
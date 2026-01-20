from app.services.vector_engine import vector_engine
from langchain.tools import tool

@tool
def search_journal_memory(query_text: str, user_id: int) -> str:
    """
    Use this when the user asks about their past, their history,
    or previous journal entries.

    Args:
        query_text: Search terms to look for
        user_id: targeted user
    """

    # FORCE STRING
    # ChromaDB metadata is usually stored as strings.
    # Even if the agent sends an Int, we convert it here to match the database.
    user_id_str = str(user_id)

    # DEBUG PRINTS
    print(f"\n--- DEBUG TOOL ---")
    print(f" Searching for: '{query_text}'")
    print(f" Target User ID: {user_id_str} (Converted to String)")

    # Run the search using the STRING version
    results = vector_engine.search_similar(query_text, user_id_str, limit=10)

    # DEBUG RESULTS
    print(f" Found {len(results) if results else 0} results.")

    if results:
        response = ""
        for doc in results:
            print(f"Doc Content: {doc.page_content}")
            response += doc.page_content + "\n"

        print(f"--- END DEBUG ---\n")
        return response

    else:
        print(f"--- END DEBUG ---\n")
        return "No memories found"
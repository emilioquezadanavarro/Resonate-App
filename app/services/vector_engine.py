import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# 1. Load the secret keys from .env
load_dotenv()


class VectorEngine:
    """
    Initialize the Vector Engine using __init__ instead of @staticmethod
    for better performance.
    """

    def __init__(self, collection_name="journal_entries"):

        print("Initializing Vector Engine... 🧠")

        # Embedding (Text -> Numbers)
        self.embedding_function = OpenAIEmbeddings(
            model="text-embedding-3-small", # Cheaper model
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Vector store (Database)
        # This creates a folder "./chroma_db" in your project to save data forever
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embedding_function,
            persist_directory="./chroma_db"
        )

    def add_entry(self, entry_id, text, user_id, mood_tags):
        """
        Converts a journal entry into numbers (vectors) and saves it.
        """

        # Create Metadata (The "Labels" on the file folder)
        # We save the User ID so we can filter later for privacy.

        metadata = {
            "entry_id": entry_id,
            "user_id": user_id,
            "moods": ", ".join(mood_tags)
        }

        # Add to ChromaDB
        # - texts: The actual journal content (used for searching)
        # - metadatas: The extra info (used for filtering)
        # - ids: Unique ID for this specific memory

        self.vector_store.add_texts(
            texts=[text],
            metadatas=[metadata],
            ids=[str(entry_id)]  # Chroma requires IDs to be strings
        )
        print(f"✅ Entry #{entry_id} vectorized and saved to memory.")

    def search_similar(self, query_text, user_id, limit=10):
        """
        Finds the top 'k' entries similar to the query_text.
        """
        print(f"🔎 Searching for memories similar to: '{query_text}'...")

        results = self.vector_store.similarity_search(
            query=query_text,
            k=limit,
            filter={"user_id": user_id}  # Security: Only show MY data
        )
        return results

    def delete_entry(self, entry_id):
        try:
            # Convert the ID to a string because that's how I saved it
            entry_id_str = str(entry_id)

            # DEBUG: Check if it exists before deleting
            # We ask the DB: "Do you have this ID?"
            existing = self.vector_store.get(ids=[entry_id_str])

            if len(existing['ids']) == 0:
                print(f"⚠️ Warning: Vector ID {entry_id_str} not found in ChromaDB. Cannot delete.")
                return False

            # Perform Delete
            print(f"🗑️ Deleting vector memory for ID: {entry_id_str}")
            self.vector_store.delete(ids=[entry_id_str])

            # Force a search immediately to refresh the cache
            # (This helps clear the RAM)
            self.vector_store.similarity_search("refresh", k=1)

            return True

        except Exception as e:
            print(f"Error deleting vector: {e}")
            return False

# Create a singleton instance
# This ensures we only open the database connection ONCE when the app starts
vector_engine = VectorEngine()
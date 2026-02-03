import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.services.tools import search_journal_memory, consult_librarian
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_tavily import TavilySearch

# 1. Load the secret keys from .env
load_dotenv()

# Global storage for chat histories
store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

class MemoryAgent:
    def __init__(self, name="Camus"):

        print(f"Initializing Memory Agent {name} ... 🤖")

        # Instantiate WEB SEARCH
        # This creates the actual tool object for the agent to use
        self.web_search = TavilySearch(max_results=3)

        # The Toolbox
        # We create a list of all the special abilities this agent has.
        # Even if there is only one tool, it must be inside a list [].
        self.tools = [search_journal_memory, consult_librarian, self.web_search]

        # The Brain
        # Initialize the generic OpenAI model.

        self.llm = ChatOpenAI(
            model="gpt-4o-mini", # Fast, smart enough and cheap
            temperature=1.1, # Low creativity, high factual accuracy
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # The Personality
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             f"You are {name}, a helpful AI companion talking to User ID: {{user_id}}. \n\n"

             f"YOUR TOOLS:\n"
             f"1. search_journal_memory: Use for specific questions about the user's past.\n"
             f"2. consult_librarian: Use this SPECIALLY when the user asks for books, reading, or resources to help with their feelings.\n"
             f"3. web_search: Use this for web search, current events, factual info, specific music recommendations or everything that the user asks. \n\n"

             f"COLLABORATION RULE:\n"
             f"If the user asks for reading recommendations, DO NOT invent titles. "
             f"Instead, use the 'consult_librarian' tool. "
             f"Take the librarian's advice and present it warmly to the user.\n\n"

             f"CRITICAL INSTRUCTION FOR MEMORY:"
             f"When you search the journal, ignore irrelevant noise. "
             f"Only base your answer on entries strictly matching the topic."
             ),

            # This is where the chat history gets injected automatically
            MessagesPlaceholder(variable_name="history"),

            ("human", "{input}"),

            # This is where the AI "thoughts" about tools go (hidden from user)
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 5. The Assembler
        # We combine the Brain, the Tools, and the Prompt into a single "Agent" unit.
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)

        # 6. The Manager
        # We create the Executor that will actually run the agent in a loop.
        # verbose=True means it will print out its "thoughts" in the terminal (great for debugging!)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5 # Stop after 5 attempts
        )

        # The Memory Wrapper
        # This wraps the agent so it automatically remembers previous messages
        self.agent_with_chat_history = RunnableWithMessageHistory(
            self.agent_executor,
            get_session_history,  # Uses the helper function above
            input_messages_key="input",
            history_messages_key="history",
        )

    def chat(self, user_input: str, user_id: str):
        print(f"Agent is thinking for User {user_id}... 💭")  # Just for debugging

        # Create a specific configuration for this user
        # This tells the system: "Load the chat history for THIS specific user_id"
        config = {"configurable": {"session_id": user_id}}

        # Run the agent!
        # input: The user's text
        # config: The user's ID
        response = self.agent_with_chat_history.invoke(
            {"input": user_input,
            "user_id": user_id
             },
            config
        )

        # The response is a big object. Final answer string.
        return response["output"]

# Create the Singleton Instance
memory_agent = MemoryAgent()
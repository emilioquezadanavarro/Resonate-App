import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.services.tools import search_journal_memory
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

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

        # The Brain
        # Initialize the generic OpenAI model.

        self.llm = ChatOpenAI(
            model="gpt-4o-mini", # Fast, smart enough and cheap
            temperature=0.3, # Low creativity, high factual accuracy
            api_key=os.getenv("OPENAI_API_KEY")
        ).bind_tools(
            tools=[search_journal_memory,
                   {"type": "web_search"}]
        )

        # The Toolbox
        # We create a list of all the special abilities this agent has.
        # Even if there is only one tool, it must be inside a list [].
        self.tools = [search_journal_memory]

        # The Personality
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             f"You are {name}, a helpful AI companion talking to User ID: {{user_id}}. "
             f"TOOLS: Use 'search_journal_memory' for personal history and 'web_search_preview' for general knowledge and music recommendation.\n\n"

             f"CRITICAL INSTRUCTION FOR MEMORY:"
             f"When you search the journal, you will receive multiple potential matches. "
             f"Some may be IRRELEVANT noise. "
             f"**You must explicitly FILTER the results.** "
             f"Only base your answer on the entries that strictly match the user's specific topic. "
             f"Ignore unrelated entries about weather, music, or other topics unless they are clearly connected."
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
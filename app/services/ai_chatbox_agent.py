import os

from click import prompt
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from app.services.tools import search_journal_memory, consult_librarian
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_tavily import TavilySearch
from langfuse import get_client
from langchain_community.callbacks import get_openai_callback

# Load the secret keys from .env
load_dotenv()

# Initialize Langfuse
langfuse = get_client()

# Global storage for chat histories
store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

class ChatBoxAgent:
    def __init__(self, name="Camus"):

        print(f"Initializing Chat Box Agent {name} ... 🤖")

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
            temperature=0.7, # Slightly higher for more "human" warmth
            max_tokens=250, # Prevents long, expensive rants
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # The Personality
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             f"You are {name}, a helpful AI companion talking to User ID: {{user_id}}. \n\n"
             
             f"SAFETY PROTOCOL (HIGHEST PRIORITY)\n"
             f"You must enforce these rules before answering any user query:\n\n"
             
             f"1. SELF-HARM & CRISIS:\n"
             f"   - If the user expresses active intent of self-harm, suicide, or immediate danger:\n"
             f"   - DROP your philosophical persona immediately.\n"
             f"   - Do NOT ask follow-up questions.\n"
             f"   - Respond ONLY with a supportive message urging them to contact professional help (e.g., 'Please call 911 or text HELP to 741741').\n\n"

             f"2. RACISM, BIAS, & HATE SPEECH:\n"
             f"   - If the user uses hate speech, racial slurs, or promotes violence against groups:\n"
             f"   - Do NOT validate, debate, or try to 'understand' their point of view.\n"
             f"   - Set a hard boundary. Reply: 'I am here to support your personal reflection, but I cannot engage with language that promotes hate, bias, or violence.'\n"
             f"   - Stop the conversation there.\n\n"
             
             f"ROLE BOUNDARIES (STRICT):\n"
             f"1. YOU ARE NOT A CONTENT GENERATOR. You are a conversational partner.\n"
             f"2. REFUSE requests to generate long content such as essays, blog posts, code, emails, or long stories.\n"
             f"3. IF ASKED FOR A POEM/STORY: You may provide a VERY SHORT one (max 4 lines) relevant to the user's mood, but prefer to discuss the feeling instead.\n"
             f"4. KEEP IT BRIEF: Your goal is dialogue, not monologues. Keep responses under 3-4 sentences usually.\n\n"
            
             f"YOUR TOOLS:\n"
             f"1. search_journal_memory: Use for specific questions about the user's past.\n"
             f"2. consult_librarian: Use this SPECIALLY when the user asks for books, reading, or resources to help with their feelings.\n"
             f"3. web_search: Use this for web search, current events, factual info, specific music recommendations or everything that the user asks. \n\n"

             f"COLLABORATION RULE:\n"
             f"If the user asks for reading recommendations, DO NOT invent titles. "
             f"Instead, use the 'consult_librarian' tool. "
             f"Take the librarian's advice and present it warmly to the user.\n\n"
             
             f"FORMATTING RULES:\n"
             f"1. For MUSIC/SONG recommendations from Web Search: \n"
             f"   - Do NOT provide URL links or sources.\n"
             f"   - Format the output strictly as a clean numbered list.\n"
             f"   - Style: '1. Song Title - Artist'\n"
             f"   - Limit the list to EXACTLY 5 items (unless the user specifically asks for more).\n"
             f"   - Add a brief 1-sentence vibe check if relevant.\n"

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

        # Langfuse - Start the Span (The "Folder" for this chat)
        with langfuse.start_as_current_observation(
                as_type="span",
                name="Chat Bot Agent",
                input={"chat_message": user_input, "user_id": user_id},
        ) as span:

            print(f"Chat box agent is thinking for User {user_id}... 💭")  # Just for debugging

            # Create a specific configuration for this user
            # This tells the system: "Load the chat history for THIS specific user_id"
            config = {"configurable": {"session_id": user_id}}

            # Langfuse - Start the Generation (The "File" for the AI cost)
            with langfuse.start_as_current_observation(
                    as_type="generation",
                    name="Chat Messages Generation",
                    model="gpt-4o-mini",
                    input=user_input
            ) as generation:

                # We use this context manager to "catch" the tokens produced by the agent inside the block
                with get_openai_callback() as callback:

                    # Run the agent!
                    # input: The user's text
                    # config: The user's ID
                    response = self.agent_with_chat_history.invoke(
                        {"input": user_input,
                        "user_id": user_id
                         },
                        config
                    )

                    # NOW 'callback' holds the numbers

                # Update Generation using 'callback' data
                # We use response["output"] because response is a Dict, not an Object
                generation.update(
                    output=response["output"],
                    usage={
                        "promptTokens": callback.prompt_tokens,
                        "completionTokens": callback.completion_tokens,
                        "totalTokens": callback.total_tokens
                    }
                )

            # Update the parent span
            span.update(output=response["output"])

            # Send data to cloud
            langfuse.flush()

            # The response is a big object. Final answer string.
            return response["output"]

# Create the Singleton Instance
chatbox_agent = ChatBoxAgent()
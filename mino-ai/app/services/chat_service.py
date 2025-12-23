from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
# from flask import current_app

class ChatService:
    _instance = None
    
    def __new__(cls, api_key=None):
        if cls._instance is None:
            cls._instance = super(ChatService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, api_key=None):
        if self._initialized:
            return
            
        self.store = {}     # In-memory store for chat sessions
        self._initialized = True
        
        if api_key:
            self.initialize_with_api_key(api_key)

    def initialize_with_api_key(self, api_key):
        """Initialize the LLM with the provided API key."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=api_key,
            temperature=1.0
        )

        self.qa_prompt_template = PromptTemplate.from_template(""" \
            You are an intelligent assistant helping users understand the content of their uploaded video.

            Context: {context}

            Instructions:
            - Respond only using the given context. Do not add information that isn't present.
            - If the user asks for a new version or rephrasing of the summary, generate a new summary directly from the original context. Do not summarize previous summaries or respond in third-person.
            - Do not include introductory phrases like "Here's a new version" or "This is a summary of…". Simply return the rewritten summary in a clear, direct, and natural tone.
            - If a question cannot be answered from the context, say so politely without guessing or fabricating.
            - Keep the tone helpful, concise, and professional."""
        )

        self.with_message_history = RunnableWithMessageHistory(
            self.llm,
            self.get_session_history
        )

    def get_session_history(self, session_id) -> BaseChatMessageHistory:
        """Retrieve the chat message history for a given session ID."""
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]
    
    def initialize_context(self, file_id, file_summary):
        """Initialize the context for a specific file with its summary."""
        if not hasattr(self, 'llm'):
            raise RuntimeError("Chat service not initialized with API key")
            
        if file_id not in self.store:
            qa_prompt = self.qa_prompt_template.format(context=file_summary)
            self.with_message_history.invoke(
                [HumanMessage(content=qa_prompt)],
                config={"configurable": {"session_id": file_id}}
            )
    
    def get_response(self, file_id, query):
        """Get a response for a specific file based on the query."""
        if not hasattr(self, 'llm'):
            raise RuntimeError("Chat service not initialized with API key")
            
        # Initialize context if it doesn't exist
        if file_id not in self.store:
            from ..services.file_service import get_file_summary
            from ..models.file import File
            
            # Get file record
            file = File.get_by_id(file_id)
            if not file:
                return None
                
            # Get file summary
            file_summary = get_file_summary(file.file_path)
            if not file_summary:
                return None
                
            # Initialize context
            self.initialize_context(file_id, file_summary)
        
        response = self.with_message_history.invoke(
            [HumanMessage(content=query)],
            config={"configurable": {"session_id": file_id}}
        )
        return response.content if response else None
    
    def clear_context(self, session_id):
        """Clear the context for a specific session."""
        if session_id in self.store:
            del self.store[session_id]

def start_chat_service(api_key):
    """Initialize the chat service with the provided API key."""
    service = ChatService()
    service.initialize_with_api_key(api_key)
    return service

# Create a singleton instance
chat_service = ChatService()

if __name__ == "__main__":
    # Example usage
    chat_service = ChatService()
    chat_service.initialize_context("file123", "This is a summary of the file.")
    response = chat_service.get_response("file123", "What is the summary of the file?")
    print(response)  # Should print the response based on the initialized context
    chat_service.clear_context("file123")
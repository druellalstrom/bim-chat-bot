import os
from openai import OpenAI
from typing import List, Dict
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

class ChatSystem:
    def __init__(self, api_key: str = None):
        """Initialize chat system with OpenAI client"""
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.conversation_history: List[Dict[str, str]] = []
        self.document_store: List[str] = []
        self.mode = "chat"
        
    def add_document(self, file_path: str):
        """Add document to RAG knowledge base"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.document_store.append(content)
                print(f"✓ Added document: {file_path}")
        except Exception as e:
            print(f"✗ Error loading {file_path}: {e}")
    
    def retrieve_relevant_context(self, query: str, top_k: int = 2) -> str:
        """Simple keyword-based retrieval from documents"""
        if not self.document_store:
            return ""
        
        # Simple relevance scoring based on keyword overlap
        query_words = set(query.lower().split())
        scored_docs = []
        
        for doc in self.document_store:
            doc_words = set(doc.lower().split())
            score = len(query_words & doc_words)
            scored_docs.append((score, doc))
        
        # Get top-k most relevant documents
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        relevant = [doc for score, doc in scored_docs[:top_k] if score > 0]
        
        return "\n\n".join(relevant) if relevant else ""
    
    def chat(self, user_message: str) -> str:
        """Send message and get response with RAG context"""
        # Retrieve relevant context from documents
        context = self.retrieve_relevant_context(user_message)
        
        # Build enhanced message with RAG context
        if context:
            enhanced_message = f"Context from documents:\n{context}\n\nUser question: {user_message}"
        else:
            enhanced_message = user_message
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": enhanced_message
        })
        
        # Call OpenAI API with conversation history
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.conversation_history,
            temperature=0.7,
            max_tokens=500  # Limit tokens for efficiency
        )
        
        assistant_message = response.choices[0].message.content
        
        # Add assistant response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message

    def _tool_get_time(self) -> str:
        """Return current local time in a user-friendly format."""
        return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    def agent_chat(self, user_message: str, max_steps: int = 4) -> str:
        """Run a small tool-using agent loop before returning a final answer."""
        self.conversation_history.append({"role": "user", "content": user_message})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "Get the current local date and time.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

        system_message = {
            "role": "system",
            "content": (
                "You are an action-oriented AI agent. Use tools when helpful, "
                "then provide a concise final answer. Do not invent tool results."
            )
        }

        working_messages = [system_message] + self.conversation_history.copy()

        for _ in range(max_steps):
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=working_messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=700
            )

            msg = response.choices[0].message
            assistant_payload = {
                "role": "assistant",
                "content": msg.content or ""
            }
            if msg.tool_calls:
                assistant_payload["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
            working_messages.append(assistant_payload)

            if not msg.tool_calls:
                final_text = msg.content or "I could not produce a response."
                self.conversation_history.append({"role": "assistant", "content": final_text})
                return final_text

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if name == "get_time":
                    result = self._tool_get_time()
                else:
                    result = f"Unknown tool: {name}"

                working_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    }
                )

        fallback = "I reached the agent step limit before a final answer. Please try again with a more specific request."
        self.conversation_history.append({"role": "assistant", "content": fallback})
        return fallback
    
    def save_history(self, filename: str = "chat_history.json"):
        """Save conversation history to file"""
        with open(filename, 'w') as f:
            json.dump(self.conversation_history, f, indent=2)
        print(f"✓ History saved to {filename}")
    
    def load_history(self, filename: str = "chat_history.json"):
        """Load conversation history from file"""
        try:
            with open(filename, 'r') as f:
                self.conversation_history = json.load(f)
            print(f"✓ History loaded from {filename}")
        except FileNotFoundError:
            print(f"✗ No history file found")
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("✓ History cleared")
    
    def get_token_count(self) -> int:
        """Estimate token usage (rough approximation)"""
        total_chars = sum(len(msg["content"]) for msg in self.conversation_history)
        return total_chars // 4  # Rough estimate: 1 token ≈ 4 characters


def main():
    """Interactive chat interface"""
    print("=== AI Chat System with RAG + Agent Mode ===\n")
    
    chat = ChatSystem()
    
    print("Commands:")
    print("  /add <file>  - Add document to knowledge base")
    print("  /mode <chat|agent> - Switch between normal chat and agent mode")
    print("  /save        - Save chat history")
    print("  /load        - Load chat history")
    print("  /clear       - Clear chat history")
    print("  /tokens      - Show estimated token usage")
    print("  /quit        - Exit\n")
    print(f"Current mode: {chat.mode}\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.startswith("/"):
            cmd_parts = user_input.split(maxsplit=1)
            cmd = cmd_parts[0].lower()
            
            if cmd == "/quit":
                break
            elif cmd == "/add" and len(cmd_parts) > 1:
                chat.add_document(cmd_parts[1])
            elif cmd == "/mode" and len(cmd_parts) > 1:
                mode = cmd_parts[1].strip().lower()
                if mode in ("chat", "agent"):
                    chat.mode = mode
                    print(f"✓ Mode set to: {chat.mode}")
                else:
                    print("Mode must be 'chat' or 'agent'")
            elif cmd == "/save":
                chat.save_history()
            elif cmd == "/load":
                chat.load_history()
            elif cmd == "/clear":
                chat.clear_history()
            elif cmd == "/tokens":
                print(f"Estimated tokens used: ~{chat.get_token_count()}")
            else:
                print("Unknown command")
            continue
        
        # Regular chat message
        try:
            if chat.mode == "agent":
                response = chat.agent_chat(user_input)
            else:
                response = chat.chat(user_input)
            print(f"\nAssistant: {response}\n")
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()

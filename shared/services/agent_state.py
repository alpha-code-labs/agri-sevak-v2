"""                                                                                                                                                                                                                                                                        
  Step 4.1 — Agent State                                                                                                                                                                                                                                                     
  TypedDict defining the state that flows through the LangGraph agent graph.                                                                                                                                                                                                 
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
from typing import Annotated                                                                                                                                                                                                                                               
from typing_extensions import TypedDict                                                                                                                                                                                                                                    
from langchain_core.messages import BaseMessage                                                                                                                                                                                                                            
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
      """State that flows through every node in the agent graph."""

      # Core conversation — LangGraph manages message accumulation
      messages: Annotated[list[BaseMessage], add_messages]

      # Farmer context (set during state machine flow, before agent runs)
      district: str
      inputs: list[str]           # farmer's collected inputs (text, image refs, audio refs)
      crop_name: str              # detected crop (filled by crop_detector tool)

      # Session tracking
      session_id: str
      user_id: str                # farmer's WhatsApp phone number
      phone_number_id: str        # business phone number ID (for sending replies)

      # Agent internals
      tool_call_log: list[dict]   # log of every tool call {tool, args, result, duration_ms}
      iteration_count: int        # how many think→tool loops so far (max 10)
"""                                                                                                                                                                                                                                                                        
  Step 4.2 — LangGraph Agent Graph
  StateGraph with 7 tools: crop_detector, rag_retriever, safety_checker,
  weather_fetcher, image_analyzer, variety_advisor, general_crop_advisor.                                                                                                                                                                                                                                           
  Think → tool → observe → repeat. Max 10 iterations, 120s timeout.                                                                                                                                                                                                          
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
import asyncio                                                                   
import logging
import time
from functools import lru_cache

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from shared.services.config import settings
from shared.services.agent_state import AgentState
from shared.services.tools.crop_detector import crop_detector
from shared.services.tools.rag_retriever import rag_retriever
from shared.services.tools.safety_checker import safety_checker
from shared.services.tools.weather_fetcher import weather_fetcher
from shared.services.tools.image_analyzer import image_analyzer
from shared.services.tools.variety_advisor import variety_advisor
from shared.services.tools.general_crop_advisor import general_crop_advisor

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
TIMEOUT_SECONDS = 120

TOOLS = [crop_detector, rag_retriever, safety_checker, weather_fetcher, image_analyzer, variety_advisor, general_crop_advisor]

SYSTEM_PROMPT = """You are a Senior Agronomist at Haryana Agricultural University (HAU, Hisar).
  A farmer from {district} district in Haryana is asking for help via WhatsApp.

  RULES:
  1. LANGUAGE: Respond ENTIRELY in Hindi (Devanagari script). Transliterate chemical names into Hindi script (e.g., Imidacloprid → इमिडाक्लोप्रिड).
  2. SAFETY: NEVER recommend banned pesticides. Always run the safety_checker tool before giving chemical advice.
  3. TOOL USAGE:
     - First use crop_detector to identify the crop from the farmer's input.
     - IMPORTANT: If the farmer does NOT mention any specific crop name in an input (e.g., "patte peele ho gaye", "kuch rog lag gaya"), do NOT call crop_detector for that input. Instead, ask the farmer to specify the crop name and optionally send a photo. If some inputs have a crop name and some don't, answer the ones you can and ask for clarification on the ambiguous ones.
     - Then use rag_retriever with the detected crop name to find verified knowledge. IMPORTANT: Only use rag_retriever for crops that were detected via "classifier", "exact", or "fuzzy" source. These crops are in our knowledge base.
     - If crop_detector returns source "gemini_fallback" (crop not in our standard list) AND the query is NOT about varieties/sowing time, use general_crop_advisor instead of rag_retriever. This provides scientifically audited advice for crops outside our RAG corpus.
     - Use weather_fetcher ONLY if the farmer explicitly asks about weather (mausam, barish, temperature, etc.). Do NOT call weather_fetcher for general crop queries. {location_hint}
     - Use image_analyzer if the farmer sent a photo (blob_name will be in their input).
     - Use variety_advisor when the farmer asks about crop varieties (kisme/किस्में), recommended varieties, or sowing time (buvai/बुवाई ka samay). Pass the crop name detected by crop_detector.
     - Use safety_checker to verify your advice doesn't include banned chemicals.
  4. MULTIPLE INPUTS: The farmer may send multiple messages (text, audio, images). Address EACH input separately with its own *bold* section header in your response.
     - EVERY input (text, audio transcript, photo) MUST get its own dedicated section with a *bold* header. NEVER merge or compress inputs together.
     - Photo analysis MUST always get its own dedicated section titled "*📷 फोटो विश्लेषण:*" with the full observations and treatment advice.
     - If the farmer mentions a pest/disease by name AND sends a photo showing a DIFFERENT pest/disease, you MUST mention both: "आपने [X] बताया, लेकिन फोटो में [Y] दिख रहा है।" Then give treatment for what the photo actually shows.
     - NEVER silently ignore or briefly merge any input. Every text, audio, and image must be fully addressed.
  5. WHATSAPP FORMATTING:
     - Use *bold* for section titles (NOT # or ##).
     - Use short paragraphs, bullet points for dosages.
     - Keep each section concise but complete. Do NOT skip or compress sections to save space.
     - Start with: "किसान भाई, यह रहा आपके सवालों का उत्तर:"
  6. If RAG retriever returns no results AND you are not confident, say so clearly and advise the farmer to visit their nearest KVK.
  7. NEVER hallucinate dosages. If unsure, say "अपने नजदीकी KVK से संपर्क करें".
  """


@lru_cache(maxsize=1)
def _get_llm():
      """Create the Gemini LLM with tools bound."""
      keys = settings.gemini_keys_list
      if not keys:
          raise ValueError("No Gemini API keys configured")

      llm = ChatGoogleGenerativeAI(
          model=settings.gemini_model_quality,
          google_api_key=keys[0],
          temperature=0,
          safety_settings={
              HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
              HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
              HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
              HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
          },
      )
      return llm.bind_tools(TOOLS)


  # ── Graph Nodes ─────────────────────────────────────────────────────────

async def agent_think(state: AgentState) -> dict:
      """The 'think' node — LLM decides what to do next."""
      # Check iteration limit
      if state.get("iteration_count", 0) >= MAX_ITERATIONS:
          logger.warning("Agent hit max iterations (%d)", MAX_ITERATIONS)
          return {
              "messages": [AIMessage(content="किसान भाई, मुझे आपकी समस्या समझने में कठिनाई हो रही है। कृपया अपने नजदीकी KVK से संपर्क करें।")],
          }

      llm = _get_llm()
      response = await llm.ainvoke(state["messages"])

      return {
          "messages": [response],
          "iteration_count": state.get("iteration_count", 0) + 1,
      }


def should_continue(state: AgentState) -> str:
      """Edge function: if the last message has tool calls, go to tools. Otherwise end."""
      last_message = state["messages"][-1]

      if state.get("iteration_count", 0) >= MAX_ITERATIONS:
          return "end"

      if hasattr(last_message, "tool_calls") and last_message.tool_calls:
          return "tools"

      return "end"


  # ── Build the Graph ─────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
      """Build and compile the LangGraph agent."""
      graph = StateGraph(AgentState)

      # Nodes
      graph.add_node("think", agent_think)
      graph.add_node("tools", ToolNode(TOOLS))

      # Edges
      graph.set_entry_point("think")
      graph.add_conditional_edges("think", should_continue, {"tools": "tools", "end": END})
      graph.add_edge("tools", "think")  # After tool execution, think again

      return graph.compile()


  # Compile once at module level
agent = build_agent_graph()


  # ── Run the Agent ───────────────────────────────────────────────────────

async def run_agent(
      user_inputs: list[str],
      district: str,
      session_id: str = "",
      user_id: str = "",
      phone_number_id: str = "",
      crop_name: str = "",
      location_lat: float | None = None,
      location_lon: float | None = None,
  ) -> dict:
      """
      Run the full agent pipeline.
      Returns: {"response": str, "tool_calls": list, "duration_ms": float}
      """
      start = time.perf_counter()

      # Build location hint for system prompt
      if location_lat is not None and location_lon is not None:
          location_hint = f"The farmer shared their exact location: lat={location_lat}, lon={location_lon}. Pass these to weather_fetcher."
      else:
          location_hint = "No exact location shared — use district name for weather."

      # Build initial messages
      system_msg = SystemMessage(content=SYSTEM_PROMPT.format(district=district, location_hint=location_hint))
      human_msg = HumanMessage(content="\n".join(user_inputs))

      initial_state: AgentState = {
          "messages": [system_msg, human_msg],
          "district": district,
          "inputs": user_inputs,
          "crop_name": crop_name,
          "session_id": session_id,
          "user_id": user_id,
          "phone_number_id": phone_number_id,
          "tool_call_log": [],
          "iteration_count": 0,
      }

      # Run with timeout
      try:
          result = await asyncio.wait_for(
              agent.ainvoke(initial_state),
              timeout=TIMEOUT_SECONDS,
          )
      except asyncio.TimeoutError:
          logger.error("Agent timed out after %ds", TIMEOUT_SECONDS)
          return {
              "response": "किसान भाई, तकनीकी समस्या के कारण जवाब देने में देरी हो रही है। कृपया कुछ देर बाद दोबारा पूछें।",
              "tool_calls": [],
              "duration_ms": (time.perf_counter() - start) * 1000,
          }

      # Extract final response and tool call log
      final_message = result["messages"][-1]
      response_text = final_message.content if hasattr(final_message, "content") else str(final_message)

      # Collect all tool calls from message history
      tool_calls = []
      for msg in result["messages"]:
          if hasattr(msg, "tool_calls") and msg.tool_calls:
              for tc in msg.tool_calls:
                  tool_calls.append({
                      "tool": tc.get("name", ""),
                      "args": tc.get("args", {}),
                  })

      duration_ms = (time.perf_counter() - start) * 1000
      logger.info("Agent completed in %.0fms with %d tool calls", duration_ms, len(tool_calls))

      return {
          "response": response_text,
          "tool_calls": tool_calls,
          "duration_ms": duration_ms,
      }
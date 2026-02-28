"""                                                                                                                                                                                                                                                                        
  Step 5.2 — Worker Message Handler                                                                                                                                                                                                                                          
  Orchestrates: parse message → load/create session → run state machine →                                                                                                                                                                                                    
  if AGENT_PROCESSING: run agent → safety audit → send WhatsApp response → restart flow.                                                                                                                                                                                     
  """                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                             
import logging                                                                                                                                                                                                                                                             
import time                                                                                                                                                                                                                                                                

from redis.asyncio import Redis

from shared.services.config import settings
from shared.services.message_parser import ParsedMessage
from shared.services.redis_session import (
      Session, SessionState,
      get_session, create_session, save_session,
  )
from shared.services.state_machine import process, Action
from shared.services.graph_api import GraphAPI
from shared.services.agent import run_agent
from shared.services.safety_audit import safety_audit
from shared.services.blob_storage import BlobStorage
from shared.services.gemini_pool import GeminiPool
from agent_worker.metrics import (
    messages_processed, tool_calls, rag_results,
    safety_triggers, agent_latency,
)

logger = logging.getLogger(__name__)


async def handle_message(payload: dict, redis: Redis):
      """
      Full message handling pipeline.
      Called by the Kafka consumer for each incoming message.
      """
      # 1. Parse the raw WhatsApp message
      msg = ParsedMessage.from_webhook(payload)
      user_id = msg.from_
      phone_number_id = msg.phone_number_id
      logger.info("Handling message from=%s type=%s", user_id, msg.type)

      # 2. Init shared services
      graph = GraphAPI()

      # 3. Mark message as read on WhatsApp
      await graph.mark_read(phone_number_id, msg.id)

      # 4. Load or create session
      session = await get_session(redis, user_id)
      if session is None:
          session = await create_session(redis, user_id, ttl_s=settings.session_ttl_seconds)
          logger.info("New session created for %s", user_id)

      # 5. Run state machine — get list of actions
      actions = process(session, msg)

      # 6. Execute each action
      for action in actions:
          await _execute_action(action, session, graph, phone_number_id, user_id, redis)

      # 7. Save session after processing
      await save_session(redis, session, ttl_s=settings.session_ttl_seconds)


async def _execute_action(
      action: Action,
      session: Session,
      graph: GraphAPI,
      phone_number_id: str,
      user_id: str,
      redis: Redis,
  ):
      """Execute a single action from the state machine."""

      if action.type == "send_text":
          await graph.send_text(phone_number_id, user_id, action.text)

      elif action.type == "send_district_menu":
          await graph.send_district_menu(phone_number_id, user_id, page=action.page)

      elif action.type == "send_buttons":
          await graph.send_interactive_buttons(
              phone_number_id, user_id,
              body_text=action.text,
              buttons=action.buttons,
          )

      elif action.type == "run_agent":
          await _run_agent_pipeline(session, graph, phone_number_id, user_id, redis)

      else:
          logger.warning("Unknown action type: %s", action.type)


async def _run_agent_pipeline(
      session: Session,
      graph: GraphAPI,
      phone_number_id: str,
      user_id: str,
      redis: Redis,
  ):
      """Run the full agent pipeline: agent → safety audit → send response → restart."""
      start = time.perf_counter()

      # Send "processing" indicator
      await graph.send_text(phone_number_id, user_id, "Aapka jawaab taiyaar ho raha hai... 🔍")

      # Collect text inputs for the agent
      text_inputs = []
      image_blobs = []
      for inp in session.inputs:
          if inp["type"] == "text":
              text_inputs.append(inp["data"])
          elif inp["type"] == "image":
              # Download image from WhatsApp and upload to Azure Blob
              try:
                  image_bytes = await graph.download_media(inp["data"])
                  blob = BlobStorage()
                  blob_name = f"images/{user_id}/{session.session_id}/{inp['data']}.jpg"
                  await blob.upload(blob_name, image_bytes, content_type="image/jpeg")
                  text_inputs.append(f"[Farmer sent a photo. blob_name: {blob_name}]")
                  image_blobs.append(blob_name)
              except Exception as e:
                  logger.error("Failed to process image %s: %s", inp["data"], e)
                  text_inputs.append("[Farmer sent a photo but it could not be downloaded]")
          elif inp["type"] == "audio":
              try:
                  audio_bytes = await graph.download_media(inp["data"])
                  pool = GeminiPool()
                  transcript = await pool.generate_audio(
                      model=settings.gemini_model_fast,
                      audio_bytes=audio_bytes,
                      text_prompt="Transcribe this audio message from a farmer in India. Output ONLY the transcription in the original language (Hindi/Haryanvi/English). No commentary.",
                      mime_type="audio/ogg",
                  )
                  logger.info("Audio transcribed: %s", transcript[:100])
                  text_inputs.append(transcript)
              except Exception as e:
                  logger.error("Failed to transcribe audio %s: %s", inp["data"], e)
                  text_inputs.append("[Farmer sent a voice message but it could not be transcribed]")

      if not text_inputs:
          text_inputs = ["किसान ने कोई सवाल नहीं भेजा"]

      # Run the LangGraph agent
      try:
          agent_result = await run_agent(
              user_inputs=text_inputs,
              district=session.district or "",
              session_id=session.session_id,
              user_id=user_id,
              phone_number_id=phone_number_id,
              location_lat=session.location_lat,
              location_lon=session.location_lon,
          )
          response = agent_result["response"]

          # Extract text from response if it's a list (Gemini returns list of parts sometimes)
          if isinstance(response, list):
              response = "\n".join(
                  part.get("text", str(part)) if isinstance(part, dict) else str(part)
                  for part in response
              )

          # Skip safety audit if agent timed out (no real content to audit)
          if not agent_result.get("tool_calls"):
              logger.warning("Agent returned no tool calls (likely timeout) — skipping audit")
              audited = {}
              final_response = response
          else:
              # Run safety audit
              # Try to detect crop name from agent tool calls
              crop_name = ""
              for tc in agent_result.get("tool_calls", []):
                  if tc["tool"] == "crop_detector":
                      crop_name = tc.get("args", {}).get("farmer_input", "")
                      break

              audited = await safety_audit(
                  agent_response=response,
                  crop_name=crop_name,
                  district=session.district or "",
              )
              final_response = audited["audited_response"]

          # Log tool calls to session
          session.tool_call_log = agent_result.get("tool_calls", [])

      except Exception as e:
          logger.error("Agent pipeline failed: %s", e, exc_info=True)
          messages_processed.labels(topic="agent_pipeline", status="error").inc()
          audited = {}
          final_response = (
              "किसान भाई, तकनीकी समस्या के कारण जवाब देने में दिक्कत हो रही है। "
              "कृपया कुछ देर बाद दोबारा पूछें या अपने नजदीकी KVK से संपर्क करें।"
          )

      duration_ms = (time.perf_counter() - start) * 1000
      duration_s = duration_ms / 1000.0
      logger.info("Agent pipeline completed in %.0fms for user=%s", duration_ms, user_id)

      # Record Prometheus metrics
      agent_latency.observe(duration_s)
      messages_processed.labels(topic="agent_pipeline", status="success").inc()

      # Track tool calls
      for tc in session.tool_call_log:
          tool_calls.labels(tool_name=tc["tool"]).inc()
          # Track RAG source
          if tc["tool"] == "rag_retriever":
              source = tc.get("result", {}).get("source", "unknown") if isinstance(tc.get("result"), dict) else "unknown"
              rag_results.labels(source=source).inc()

      # Track safety triggers
      if audited.get("local_scan"):
          safety_triggers.labels(layer="local_scan").inc(len(audited["local_scan"]))
      if audited.get("post_audit_scan"):
          safety_triggers.labels(layer="gemini_auditor").inc(len(audited["post_audit_scan"]))

      # Send the final response to the farmer
      await graph.send_text(phone_number_id, user_id, final_response)

      # Post-answer follow-up — ask if farmer has more questions
      session.state = SessionState.POST_ANSWER
      session.inputs = []
      session.input_count = 0
      await save_session(redis, session, ttl_s=settings.session_ttl_seconds)

      await graph.send_interactive_buttons(
          phone_number_id, user_id,
          body_text="Kya aur koi samasya hai?",
          buttons=[
              {"type": "reply", "reply": {"id": "post_yes", "title": "Haan, aur poochein 🔄"}},
              {"type": "reply", "reply": {"id": "post_no", "title": "Nahi, dhanyavaad 🙏"}},
          ],
      )

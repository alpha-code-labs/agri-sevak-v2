from dataclasses import dataclass, field                                                                                                                                                                                                                                   
from shared.services.redis_session import Session, SessionState                                                                                                                                                                                                            
from shared.services.message_parser import ParsedMessage                                                                                                                                                                                                                   
from shared.services.graph_api import HARYANA_DISTRICTS                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                             
MAX_INPUTS = 6                                                                                                                                                                                                                                                             
                                                                                   

@dataclass
class Action:
      type: str
      text: str = ""
      page: int = 0
      buttons: list[dict] = field(default_factory=list)


def process(session: Session, msg: ParsedMessage) -> list[Action]:
      """Process a message through the state machine. Returns a list of actions to execute."""
      actions = []

      if session.state == SessionState.GREETING:
          actions.append(Action(
              type="send_text",
              text="🙏 Namaste! KCC Kisaan Mitra mein aapka swagat hai. Kripya apna jila chunein.",
          ))
          actions.append(Action(type="send_district_menu", page=0))
          session.state = SessionState.DISTRICT_SELECT

      elif session.state == SessionState.DISTRICT_SELECT:
          if msg.type == "interactive" and msg.interactive_id:
              if msg.interactive_id == "dist_prev":
                  current_page = getattr(session, '_page', 1)
                  actions.append(Action(type="send_district_menu", page=max(0, current_page - 1)))
              elif msg.interactive_id == "dist_next":
                  current_page = getattr(session, '_page', 0)
                  actions.append(Action(type="send_district_menu", page=current_page + 1))
              elif msg.interactive_id.startswith("dist_"):
                  district_key = msg.interactive_id.replace("dist_", "").replace("_", " ").title()
                  # Find matching district
                  matched = next((d for d in HARYANA_DISTRICTS if d.lower() == district_key.lower()), None)
                  if matched:
                      session.district = matched
                      session.state = SessionState.QUERY_COLLECT
                      actions.append(Action(
                          type="send_text",
                          text=f"Jila: {matched} ✅\nApni samasya batayein — text, photo ya voice bhejein.",
                      ))
                  else:
                      actions.append(Action(type="send_text", text="Kripya suchi mein se jila chunein."))
                      actions.append(Action(type="send_district_menu", page=0))
          else:
              actions.append(Action(type="send_text", text="Kripya suchi mein se jila chunein."))
              actions.append(Action(type="send_district_menu", page=0))

      elif session.state == SessionState.QUERY_COLLECT:
          _collect_input(session, msg)

          if session.input_count >= MAX_INPUTS:
              session.state = SessionState.AGENT_PROCESSING
              actions.append(Action(type="run_agent"))
          else:
              session.state = SessionState.QUERY_CONFIRM
              actions.append(Action(
                  type="send_buttons",
                  text="Aur kuch bhejein ya jawaab dein?",
                  buttons=[
                      {"type": "reply", "reply": {"id": "query_continue", "title": "Aur bhejein ➕"}},
                      {"type": "reply", "reply": {"id": "query_done", "title": "Jawaab dein ✅"}},
                  ],
              ))

      elif session.state == SessionState.QUERY_CONFIRM:
          if msg.type == "interactive" and msg.interactive_id == "query_done":
              session.state = SessionState.AGENT_PROCESSING
              actions.append(Action(type="run_agent"))
          elif msg.type == "interactive" and msg.interactive_id == "query_continue":
              session.state = SessionState.QUERY_COLLECT
              actions.append(Action(type="send_text", text="Kripya aur bhejein — text, photo ya voice."))
          else:
              # Farmer sent another input instead of pressing a button — collect it
              _collect_input(session, msg)
              if session.input_count >= MAX_INPUTS:
                  session.state = SessionState.AGENT_PROCESSING
                  actions.append(Action(type="run_agent"))
              else:
                  actions.append(Action(
                      type="send_buttons",
                      text="Aur kuch bhejein ya jawaab dein?",
                      buttons=[
                          {"type": "reply", "reply": {"id": "query_continue", "title": "Aur bhejein ➕"}},
                          {"type": "reply", "reply": {"id": "query_done", "title": "Jawaab dein ✅"}},
                      ],
                  ))

      elif session.state == SessionState.AGENT_PROCESSING:
          actions.append(Action(type="send_text", text="Aapka jawaab taiyaar ho raha hai... 🔍"))

      return actions


def _collect_input(session: Session, msg: ParsedMessage):
      """Append farmer's input to the session."""
      if msg.type == "text" and msg.text:
          session.inputs.append({"type": "text", "data": msg.text})
      elif msg.type == "image" and msg.image_id:
          session.inputs.append({"type": "image", "data": msg.image_id})
      elif msg.type == "audio" and msg.audio_id:
          session.inputs.append({"type": "audio", "data": msg.audio_id})
      session.input_count = len(session.inputs)
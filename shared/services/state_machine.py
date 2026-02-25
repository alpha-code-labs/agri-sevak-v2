import re
from dataclasses import dataclass, field
from shared.services.redis_session import Session, SessionState
from shared.services.message_parser import ParsedMessage
from shared.services.graph_api import HARYANA_DISTRICTS

MAX_INPUTS = 6

WEATHER_KEYWORDS = re.compile(
    r"mausam|weather|barish|baarish|rain|temperature|tufaan|toofan|andhi|"
    r"garmi|sardi|loo|heatwave|frost|pala|ola|hail|mौसम|बारिश|तूफान|"
    r"आंधी|गर्मी|सर्दी|लू|ओला|पाला",
    re.IGNORECASE,
)


@dataclass
class Action:
    type: str
    text: str = ""
    page: int = 0
    buttons: list[dict] = field(default_factory=list)


def _has_weather_keywords(text: str) -> bool:
    """Check if text contains weather-related keywords."""
    return bool(WEATHER_KEYWORDS.search(text))


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
            # Check if farmer mentioned weather — ask for location pin
            last_text = _get_last_text_input(session)
            if last_text and _has_weather_keywords(last_text):
                session.state = SessionState.WEATHER_PIN_REQUEST
                actions.append(Action(
                    type="send_buttons",
                    text="Sahi mausam ke liye apna location pin bhejein 📍",
                    buttons=[
                        {"type": "reply", "reply": {"id": "pin_skip", "title": "Skip karein ⏭️"}},
                    ],
                ))
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

    elif session.state == SessionState.WEATHER_PIN_REQUEST:
        if msg.type == "location" and msg.location:
            # Farmer dropped a pin — save coordinates
            session.location_lat = msg.location.get("latitude")
            session.location_lon = msg.location.get("longitude")
            session.state = SessionState.QUERY_CONFIRM
            actions.append(Action(
                type="send_buttons",
                text="Location mil gaya ✅ Aur kuch bhejein ya jawaab dein?",
                buttons=[
                    {"type": "reply", "reply": {"id": "query_continue", "title": "Aur bhejein ➕"}},
                    {"type": "reply", "reply": {"id": "query_done", "title": "Jawaab dein ✅"}},
                ],
            ))
        elif msg.type == "interactive" and msg.interactive_id == "pin_skip":
            # Farmer skipped — use district center coordinates
            session.state = SessionState.QUERY_CONFIRM
            actions.append(Action(
                type="send_buttons",
                text="Aur kuch bhejein ya jawaab dein?",
                buttons=[
                    {"type": "reply", "reply": {"id": "query_continue", "title": "Aur bhejein ➕"}},
                    {"type": "reply", "reply": {"id": "query_done", "title": "Jawaab dein ✅"}},
                ],
            ))
        else:
            # Farmer sent something else — treat as skip, collect input
            _collect_input(session, msg)
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

    elif session.state == SessionState.POST_ANSWER:
        if msg.type == "interactive" and msg.interactive_id == "post_yes":
            # Farmer wants to ask another question — keep district, clear inputs
            session.state = SessionState.QUERY_COLLECT
            session.inputs = []
            session.input_count = 0
            session.location_lat = None
            session.location_lon = None
            actions.append(Action(
                type="send_text",
                text="Apni agli samasya batayein — text, photo ya voice bhejein.",
            ))
        elif msg.type == "interactive" and msg.interactive_id == "post_no":
            # Farmer is done — goodbye and reset
            actions.append(Action(type="send_text", text="Dhanyavaad! Jai Kisan 🌾"))
            session.state = SessionState.GREETING
            session.inputs = []
            session.input_count = 0
            session.district = None
            session.location_lat = None
            session.location_lon = None
        else:
            # Farmer sent a new message instead of pressing button — treat as new query
            session.state = SessionState.QUERY_COLLECT
            session.inputs = []
            session.input_count = 0
            session.location_lat = None
            session.location_lon = None
            _collect_input(session, msg)
            session.state = SessionState.QUERY_CONFIRM
            actions.append(Action(
                type="send_buttons",
                text="Aur kuch bhejein ya jawaab dein?",
                buttons=[
                    {"type": "reply", "reply": {"id": "query_continue", "title": "Aur bhejein ➕"}},
                    {"type": "reply", "reply": {"id": "query_done", "title": "Jawaab dein ✅"}},
                ],
            ))

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


def _get_last_text_input(session: Session) -> str | None:
    """Get the last text input from the session, if any."""
    for inp in reversed(session.inputs):
        if inp["type"] == "text":
            return inp["data"]
    return None

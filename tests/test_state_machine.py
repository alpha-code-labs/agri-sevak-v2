import time
from shared.services.state_machine import process, Action
from shared.services.redis_session import Session, SessionState
from shared.services.message_parser import ParsedMessage


def make_session() -> Session:
      return Session(
          user_id="919876543210",
          session_id="919876543210_123",
          created_at=time.time(),
          updated_at=time.time(),
      )


def make_msg(**kwargs) -> ParsedMessage:
      defaults = {"id": "wamid_1", "from": "919876543210", "type": "text", "phone_number_id": "100001"}
      defaults.update(kwargs)
      return ParsedMessage.from_webhook(defaults)


def test_greeting():
      session = make_session()
      msg = make_msg()
      actions = process(session, msg)
      assert session.state == SessionState.DISTRICT_SELECT
      assert actions[0].type == "send_text"
      assert actions[1].type == "send_district_menu"
      print("Greeting OK")


def test_district_select():
      session = make_session()
      session.state = SessionState.DISTRICT_SELECT
      msg = make_msg(type="interactive", interactive={"type": "list_reply", "list_reply": {"id": "dist_karnal", "title": "Karnal"}})
      actions = process(session, msg)
      assert session.state == SessionState.QUERY_COLLECT
      assert session.district == "Karnal"
      assert "Karnal" in actions[0].text
      print("District select OK")


def test_query_collect():
      session = make_session()
      session.state = SessionState.QUERY_COLLECT
      session.district = "Karnal"
      msg = make_msg(text={"body": "gehun me kide lage hue hai"})
      actions = process(session, msg)
      assert session.state == SessionState.QUERY_CONFIRM
      assert session.input_count == 1
      assert session.inputs[0]["data"] == "gehun me kide lage hue hai"
      assert actions[0].type == "send_buttons"
      print("Query collect OK")


def test_query_done():
      session = make_session()
      session.state = SessionState.QUERY_CONFIRM
      session.district = "Karnal"
      session.inputs = [{"type": "text", "data": "gehun me kide"}]
      session.input_count = 1
      msg = make_msg(type="interactive", interactive={"type": "button_reply", "button_reply": {"id": "query_done", "title": "Jawaab dein"}})
      actions = process(session, msg)
      assert session.state == SessionState.AGENT_PROCESSING
      assert actions[0].type == "run_agent"
      print("Query done OK")


def test_max_inputs():
      session = make_session()
      session.state = SessionState.QUERY_COLLECT
      session.district = "Karnal"
      session.inputs = [{"type": "text", "data": f"input {i}"} for i in range(5)]
      session.input_count = 5
      msg = make_msg(text={"body": "sixth input"})
      actions = process(session, msg)
      assert session.state == SessionState.AGENT_PROCESSING
      assert session.input_count == 6
      assert actions[0].type == "run_agent"
      print("Max inputs OK")


if __name__ == "__main__":
      test_greeting()
      test_district_select()
      test_query_collect()
      test_query_done()
      test_max_inputs()
      print("State machine OK")
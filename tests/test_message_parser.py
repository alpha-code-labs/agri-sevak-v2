from shared.services.message_parser import ParsedMessage


def test_text():
      msg = {"id": "wamid_123", "from": "919876543210", "type": "text",
             "text": {"body": "gehun me kide"}, "phone_number_id": "10000001"}
      parsed = ParsedMessage.from_webhook(msg)
      assert parsed.from_ == "919876543210"
      assert parsed.text == "gehun me kide"
      assert parsed.type == "text"
      print("Text OK")


def test_image():
      msg = {"id": "wamid_456", "from": "919876543210", "type": "image",
             "image": {"id": "img_789"}, "phone_number_id": "10000001"}
      parsed = ParsedMessage.from_webhook(msg)
      assert parsed.image_id == "img_789"
      assert parsed.text is None
      print("Image OK")


def test_interactive():
      msg = {"id": "wamid_789", "from": "919876543210", "type": "interactive",
             "interactive": {"type": "list_reply", "list_reply": {"id": "dist_karnal", "title": "Karnal"}},
             "phone_number_id": "10000001"}
      parsed = ParsedMessage.from_webhook(msg)
      assert parsed.interactive_type == "list_reply"
      assert parsed.interactive_id == "dist_karnal"
      assert parsed.interactive_title == "Karnal"
      print("Interactive OK")


if __name__ == "__main__":
      test_text()
      test_image()
      test_interactive()
      print("Message parser OK")
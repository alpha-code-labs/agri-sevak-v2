from shared.services.tools.safety_checker import (
      get_banned_chemicals_for_crop,
      scan_text_for_banned,
      safety_checker,
  )


def test_banned_for_crop():
      banned = get_banned_chemicals_for_crop("Wheat")
      assert len(banned) > 0
      names = [b["chemical_name"] for b in banned]
      print(f"Wheat — {len(banned)} banned chemicals")
      print(f"Examples: {names[:5]}")


def test_scan_text():
      text = "Use Endosulfan 35 EC for pest control"
      found = scan_text_for_banned(text, "Wheat")
      names = [f["chemical_name"] for f in found]
      assert any("endosulfan" in n.lower() for n in names), f"Expected Endosulfan, got {names}"
      print(f"Scan found: {names}")


def test_tool_wrapper():
      result = safety_checker.invoke({"crop_name": "Wheat", "text_to_scan": ""})
      assert result["total_banned"] > 0
      print(f"Tool wrapper OK — {result['total_banned']} banned chemicals for Wheat")


def test_clean_text():
      text = "Use neem oil and trichoderma for pest control"
      found = scan_text_for_banned(text, "Wheat")
      assert len(found) == 0
      print("Clean text OK — no banned chemicals found")


if __name__ == "__main__":
      test_banned_for_crop()
      test_scan_text()
      test_tool_wrapper()
      test_clean_text()
      print("Safety checker OK")
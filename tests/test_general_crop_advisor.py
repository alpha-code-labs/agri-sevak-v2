"""Tests for general_crop_advisor tool — Gemini + scientific audit path."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_tool_known_crop():
    """Test with a known crop (dragon fruit) — should generate + audit."""
    from shared.services.tools.general_crop_advisor import general_crop_advisor

    async def _run():
        result = await general_crop_advisor.ainvoke({
            "crop_name": "Dragon Fruit",
            "query": "dragon fruit mein kya kya rog lagte hain aur unka ilaaj kya hai"
        })
        print(f"  Source: {result['source']}")
        print(f"  Audit safe: {result['audit'].get('is_safe', 'N/A')}")
        print(f"  Banned chemicals found: {len(result['audit'].get('banned_chemicals_found', []))}")
        print(f"  Caveat: {result.get('caveat', 'N/A')}")
        print(f"  Advice preview: {result['advice'][:300]}...")
        assert result["source"] == "gemini_with_scientific_audit"
        assert result["advice"], "Advice should not be empty"
        return result

    return asyncio.run(_run())


def test_tool_avocado():
    """Test with avocado — exotic crop, not in any list."""
    from shared.services.tools.general_crop_advisor import general_crop_advisor

    async def _run():
        result = await general_crop_advisor.ainvoke({
            "crop_name": "Avocado",
            "query": "avocado ki kheti kaise karein haryana mein"
        })
        print(f"  Source: {result['source']}")
        print(f"  Audit safe: {result['audit'].get('is_safe', 'N/A')}")
        print(f"  Advice preview: {result['advice'][:300]}...")
        assert result["source"] == "gemini_with_scientific_audit"
        assert result["advice"], "Advice should not be empty"
        return result

    return asyncio.run(_run())


def test_tool_compound_query():
    """Test with a compound query (multiple concerns)."""
    from shared.services.tools.general_crop_advisor import general_crop_advisor

    async def _run():
        result = await general_crop_advisor.ainvoke({
            "crop_name": "Kiwi",
            "query": "kiwi mein sinchai kab karein aur fertilizer kitna daalna hai aur kya keet lagte hain"
        })
        print(f"  Source: {result['source']}")
        print(f"  Audit safe: {result['audit'].get('is_safe', 'N/A')}")
        print(f"  Advice preview: {result['advice'][:300]}...")
        assert result["source"] == "gemini_with_scientific_audit"
        return result

    return asyncio.run(_run())


def test_response_is_hindi():
    """Verify the response is in Hindi (Devanagari script)."""
    from shared.services.tools.general_crop_advisor import general_crop_advisor

    async def _run():
        result = await general_crop_advisor.ainvoke({
            "crop_name": "Cashew Nut",
            "query": "cashew mein keet rog ka ilaaj"
        })
        advice = result["advice"]
        # Check for Devanagari characters (Unicode range 0900-097F)
        hindi_chars = sum(1 for c in advice if '\u0900' <= c <= '\u097F')
        total_alpha = sum(1 for c in advice if c.isalpha())
        hindi_ratio = hindi_chars / total_alpha if total_alpha > 0 else 0
        print(f"  Hindi character ratio: {hindi_ratio:.1%}")
        print(f"  Advice preview: {advice[:200]}...")
        assert hindi_ratio > 0.5, f"Expected mostly Hindi, got {hindi_ratio:.1%}"
        return result

    return asyncio.run(_run())


if __name__ == "__main__":
    tests = [
        ("Dragon Fruit query", test_tool_known_crop),
        ("Avocado query", test_tool_avocado),
        ("Compound query (Kiwi)", test_tool_compound_query),
        ("Hindi response check", test_response_is_hindi),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            fn()
            print(f"  PASS")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)

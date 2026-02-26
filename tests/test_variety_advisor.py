"""Tests for variety_advisor tool — JSON lookup path only (no Gemini needed)."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.services.tools.variety_advisor import (
    _lookup_varieties,
    _format_varieties,
    _get_varieties_data,
)


def test_json_loads():
    """Verify the JSON file loads and has records."""
    records = _get_varieties_data()
    assert len(records) > 0, "No records loaded from varieties JSON"
    print(f"  Loaded {len(records)} variety records")

    # Check unique crops
    crops = set(r.get("Crop", "") for r in records)
    print(f"  Unique crops: {len(crops)}")
    # Show first 10
    for c in sorted(crops)[:10]:
        count = sum(1 for r in records if r.get("Crop") == c)
        print(f"    - {c} ({count} varieties)")


def test_lookup_known_crop():
    """Test lookup for a crop that exists in JSON."""
    # Try common crops
    for crop in ["Wheat", "Rice", "Mustard", "Cotton", "Sugarcane"]:
        records = _lookup_varieties(crop)
        if records:
            print(f"  {crop}: {len(records)} varieties found")
            formatted = _format_varieties(crop, records)
            # Show first 200 chars
            print(f"    Preview: {formatted[:200]}...")
            return

    # If none of the above, try whatever is first in the data
    all_records = _get_varieties_data()
    first_crop = all_records[0].get("Crop", "")
    records = _lookup_varieties(first_crop)
    print(f"  {first_crop}: {len(records)} varieties found")
    formatted = _format_varieties(first_crop, records)
    print(f"    Preview: {formatted[:200]}...")


def test_lookup_case_insensitive():
    """Test that lookup is case-insensitive."""
    all_records = _get_varieties_data()
    first_crop = all_records[0].get("Crop", "")

    upper = _lookup_varieties(first_crop.upper())
    lower = _lookup_varieties(first_crop.lower())
    mixed = _lookup_varieties(first_crop.title())

    assert len(upper) == len(lower) == len(mixed), \
        f"Case sensitivity issue: upper={len(upper)}, lower={len(lower)}, mixed={len(mixed)}"
    print(f"  Case-insensitive lookup works for '{first_crop}': {len(upper)} records")


def test_lookup_unknown_crop():
    """Test lookup for a crop NOT in JSON."""
    records = _lookup_varieties("Dragon Fruit")
    assert len(records) == 0, "Dragon Fruit should not be in the JSON"
    print("  'Dragon Fruit' correctly returns 0 records")

    records = _lookup_varieties("Avocado")
    assert len(records) == 0, "Avocado should not be in the JSON"
    print("  'Avocado' correctly returns 0 records")


def test_tool_json_path():
    """Test the actual tool function — JSON lookup path."""
    from shared.services.tools.variety_advisor import variety_advisor

    async def _run():
        # Use a crop we know exists
        all_records = _get_varieties_data()
        first_crop = all_records[0].get("Crop", "")
        result = await variety_advisor.ainvoke({"crop_name": first_crop})
        assert result["source"] == "verified_database", f"Expected verified_database, got {result['source']}"
        assert result["count"] > 0
        print(f"  Tool returned {result['count']} varieties for '{first_crop}' from {result['source']}")
        print(f"    Data preview: {result['data'][:200]}...")
        return result

    return asyncio.run(_run())


def test_tool_unknown_crop_no_gemini():
    """Test tool with unknown crop — should hit Gemini fallback (will fail without keys, that's OK)."""
    from shared.services.tools.variety_advisor import variety_advisor

    async def _run():
        result = await variety_advisor.ainvoke({"crop_name": "Dragon Fruit"})
        # Without Gemini keys, should return not_found
        print(f"  Tool result for 'Dragon Fruit': source={result['source']}")
        print(f"    Data: {result['data'][:200]}")
        return result

    return asyncio.run(_run())


if __name__ == "__main__":
    tests = [
        ("JSON loads", test_json_loads),
        ("Lookup known crop", test_lookup_known_crop),
        ("Case-insensitive lookup", test_lookup_case_insensitive),
        ("Lookup unknown crop", test_lookup_unknown_crop),
        ("Tool JSON path", test_tool_json_path),
        ("Tool unknown crop (no Gemini)", test_tool_unknown_crop_no_gemini),
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

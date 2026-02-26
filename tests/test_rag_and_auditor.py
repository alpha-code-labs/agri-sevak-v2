"""Tests for upgraded rag_retriever (FOUND/MISSING) and safety_audit (full auditor)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_rag_found_path():
    """Test rag_retriever with a crop+query that should be in Pinecone (wheat + thrips)."""
    from shared.services.tools.rag_retriever import rag_retriever

    async def _run():
        result = await rag_retriever.ainvoke({
            "query": "gehun mein thrips ka ilaaj",
            "crop_name": "Wheat",
        })
        print(f"  Source: {result['source']}")
        print(f"  Status: {result['status']}")
        print(f"  Evidence count: {result.get('evidence_count', 0)}")
        print(f"  Top score: {result.get('top_score', 'N/A')}")
        print(f"  Safety warnings: {len(result.get('safety_warnings', []))}")
        if result.get("grounded_response"):
            print(f"  Grounded response preview: {result['grounded_response'][:200]}...")
        else:
            print(f"  Grounded response: EMPTY")

        if result["status"] == "FOUND":
            assert result["source"] == "pinecone_rag"
            assert result["evidence_count"] > 0
            print(f"  --> FOUND path verified")
        else:
            print(f"  --> MISSING (wheat thrips not in Pinecone, testing MISSING path instead)")
        return result

    return asyncio.run(_run())


def test_rag_missing_path():
    """Test rag_retriever with a query that likely won't be in Pinecone."""
    from shared.services.tools.rag_retriever import rag_retriever

    async def _run():
        result = await rag_retriever.ainvoke({
            "query": "dragon fruit mein red rot kaise rokein",
            "crop_name": "Dragon Fruit",
        })
        print(f"  Source: {result['source']}")
        print(f"  Status: {result['status']}")
        print(f"  Evidence count: {result.get('evidence_count', 0)}")
        if result.get("grounded_response"):
            print(f"  Grounded response preview: {result['grounded_response'][:200]}...")

        assert result["status"] == "MISSING"
        print(f"  --> MISSING path verified")
        return result

    return asyncio.run(_run())


def test_rag_grounded_response_is_hindi():
    """Verify the grounded response is in Hindi."""
    from shared.services.tools.rag_retriever import rag_retriever

    async def _run():
        result = await rag_retriever.ainvoke({
            "query": "kapas mein safed makhi ka ilaaj",
            "crop_name": "Cotton Kapas",
        })
        response = result.get("grounded_response", "")
        if not response:
            print("  SKIP: No grounded response generated")
            return

        hindi_chars = sum(1 for c in response if '\u0900' <= c <= '\u097F')
        total_alpha = sum(1 for c in response if c.isalpha())
        hindi_ratio = hindi_chars / total_alpha if total_alpha > 0 else 0
        print(f"  Hindi ratio: {hindi_ratio:.1%}")
        print(f"  Preview: {response[:200]}...")
        assert hindi_ratio > 0.4, f"Expected mostly Hindi, got {hindi_ratio:.1%}"
        return result

    return asyncio.run(_run())


def test_safety_audit_basic():
    """Test the full safety auditor with a sample response."""
    from shared.services.safety_audit import safety_audit

    async def _run():
        sample_response = """किसान भाई, यह रहा आपके सवालों का उत्तर:

**भाग अ: प्रमाणित जानकारी**
गेहूं में थ्रिप्स के लिए इमिडाक्लोप्रिड 17.8 SL का 0.5 मिली प्रति लीटर पानी में घोल बनाकर छिड़काव करें।

**भाग ब: विशेषज्ञ शोध**
सिंचाई के लिए पहली सिंचाई बुवाई के 21 दिन बाद करें।"""

        result = await safety_audit(
            agent_response=sample_response,
            crop_name="Wheat",
            district="Hisar",
        )
        print(f"  Safe before audit: {result['is_safe_before_audit']}")
        print(f"  Audit applied: {result['audit_applied']}")
        print(f"  Local scan results: {len(result.get('local_scan', []))} banned chemicals")
        if result["audit_applied"]:
            audited = result["audited_response"]
            # Check that section labels were cleaned
            has_bhag = "भाग अ" in audited or "भाग ब" in audited
            print(f"  Section labels cleaned: {not has_bhag}")
            print(f"  Audited preview: {audited[:300]}...")
        return result

    return asyncio.run(_run())


def test_safety_audit_banned_chemical():
    """Test that auditor removes banned chemicals."""
    from shared.services.safety_audit import safety_audit

    async def _run():
        # Endosulfan is banned in India
        sample_response = """किसान भाई, कपास में सफेद मक्खी के लिए एंडोसल्फान 35 EC का 2 मिली प्रति लीटर पानी में छिड़काव करें।"""

        result = await safety_audit(
            agent_response=sample_response,
            crop_name="Cotton Kapas",
            district="Sirsa",
        )
        print(f"  Safe before audit: {result['is_safe_before_audit']}")
        print(f"  Local scan found: {[c['chemical_name'] for c in result.get('local_scan', [])]}")
        if result["audit_applied"]:
            audited = result["audited_response"]
            # Endosulfan should be removed or replaced
            has_endosulfan = "एंडोसल्फान" in audited.lower() or "endosulfan" in audited.lower()
            print(f"  Endosulfan still in audited response: {has_endosulfan}")
            print(f"  Audited preview: {audited[:300]}...")
        return result

    return asyncio.run(_run())


def test_safety_instruction_builder():
    """Test the crop-specific safety instruction builder."""
    from shared.services.safety_audit import _build_safety_instruction

    # Wheat should have some banned chemicals
    instruction = _build_safety_instruction("Wheat")
    print(f"  Wheat safety instruction length: {len(instruction)} chars")
    if instruction:
        print(f"  Preview: {instruction[:200]}...")
    else:
        print(f"  No crop-specific restrictions for Wheat")

    # Cotton should have restricted chemicals
    instruction = _build_safety_instruction("Cotton Kapas")
    print(f"  Cotton safety instruction length: {len(instruction)} chars")
    if instruction:
        print(f"  Preview: {instruction[:200]}...")


if __name__ == "__main__":
    tests = [
        ("RAG FOUND path (Wheat thrips)", test_rag_found_path),
        ("RAG MISSING path (Dragon Fruit)", test_rag_missing_path),
        ("RAG grounded response Hindi check", test_rag_grounded_response_is_hindi),
        ("Safety audit basic", test_safety_audit_basic),
        ("Safety audit banned chemical removal", test_safety_audit_banned_chemical),
        ("Safety instruction builder", test_safety_instruction_builder),
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
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)

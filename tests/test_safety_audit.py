"""Test safety audit post-processing."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.services.safety_audit import safety_audit


async def main():
      # Test 1: Clean response (no banned chemicals)
      print("Test 1: Clean response (should pass audit)...")
      clean_response = (
          "किसान भाई, गेहूं में पीला रतुआ के लिए प्रोपिकोनाज़ोल 25% EC "
          "200 मिली प्रति एकड़ छिड़काव करें। टेबुकोनाज़ोल 25.9% EC भी प्रभावी है।"
      )
      result = await safety_audit(clean_response, crop_name="Wheat", district="Hisar")
      print(f"  Safe before audit: {result['is_safe_before_audit']}")
      print(f"  Audit applied: {result['audit_applied']}")
      print(f"  Audited response preview: {result['audited_response'][:200]}...")
      print()

      # Test 2: Response containing a banned chemical (Methyl Parathion)
      print("Test 2: Response with banned chemical (should be caught and replaced)...")
      unsafe_response = (
          "किसान भाई, गेहूं में कीड़ों के लिए मिथाइल पैराथियॉन (Methyl Parathion) "
          "का छिड़काव करें 500 मिली प्रति एकड़। यह बहुत प्रभावी है।"
      )
      result2 = await safety_audit(unsafe_response, crop_name="Wheat", district="Karnal")
      print(f"  Safe before audit: {result2['is_safe_before_audit']}")
      print(f"  Local scan found: {[c['chemical_name'] for c in result2['local_scan']]}")
      print(f"  Audit applied: {result2['audit_applied']}")
      print(f"  Audited response preview: {result2['audited_response'][:300]}...")
      print()

      print("Safety audit tests done.")


if __name__ == "__main__":
      asyncio.run(main())
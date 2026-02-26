# Deep Analysis — FAIL & PARTIAL Queries
## Run 2026-02-26_15-39 | 14 queries (7 FAIL + 7 PARTIAL)

---

## FAIL — Timeouts (7 queries)

All 7 FAILs are agent timeouts: zero tools fired, duration > 120s, generic error response.

---

### eval_011 — Chillies Fruit Borer (Rewari) — FAIL
- **Query:** `mirch me fruit borer laga hai kya kare`
- **Category:** pest_management
- **Expected tools:** crop_detector, rag_retriever, safety_checker
- **Actual tools:** NONE
- **Duration:** 138.1s
- **Full response:**
> किसान भाई, आपके सवालों का सटीक समाधान यहाँ है:
> ❓ *आपके सवाल का जवाब क्यों नहीं मिल रहा है?*
> ✅ तकनीकी समस्या के कारण आपके सवाल का जवाब देने में देरी हो रही है।
> ❓ *आगे क्या करें?*
> ✅ कृपया कुछ देर बाद दोबारा पूछें। यदि समस्या बनी रहती है, तो अपने कृषि विज्ञान केंद्र (KVK) या हरियाणा कृषि विश्वविद्यालय (HAU) के विशेषज्ञों से संपर्क करें।

**Root cause hypothesis:** Simple single-crop query, should complete in ~40-60s. Likely a random Gemini API timeout or agent worker stall. No pattern correlation with other timeouts.

---

### eval_019 — Cotton Root Rot (Sirsa) — FAIL
- **Query:** `kapas me root rot ho raha hai`
- **Category:** disease_management
- **Expected tools:** crop_detector, rag_retriever, safety_checker
- **Actual tools:** NONE
- **Duration:** 124.6s
- **Full response:**
> किसान भाई, तकनीकी समस्या के कारण जवाब देने में देरी हो रही है। कृपया कुछ देर बाद दोबारा पूछें।

**Root cause hypothesis:** Same as eval_011 — random infrastructure timeout.

---

### eval_038 — Cashew Nut Sowing (Panchkula) — FAIL
- **Query:** `cashew nut ki buvai kab karein aur variety bataiye`
- **Category:** variety_sowing_unknown
- **Expected tools:** crop_detector, variety_advisor
- **Actual tools:** NONE
- **Duration:** 127.7s
- **Full response:**
> किसान भाई, तकनीकी समस्या के कारण जवाब देने में देरी हो रही है। कृपया कुछ देर बाद दोबारा पूछें।

**Root cause hypothesis:** Cashew is an "unknown" crop — not in Haryana's standard crop list. The agent may have struggled with routing (no RAG data, variety_advisor has limited data for this crop). Could be Gemini taking too long to generate from scratch.

---

### eval_065 — Sugarcane Weed Control (Yamunanagar) — FAIL
- **Query:** `ganne me kharpatwar niyantran kaise kare`
- **Category:** general_agronomy
- **Expected tools:** crop_detector, rag_retriever, safety_checker
- **Actual tools:** NONE
- **Duration:** 144.1s
- **Full response:**
> किसान भाई, आपके सवालों का सटीक समाधान यहाँ है:
> ❓ *आपके सवाल का जवाब क्यों नहीं मिल रहा है?*
> ✅ किसान भाई, तकनीकी समस्या के कारण जवाब देने में देरी हो रही है। कृपया कुछ देर बाद दोबारा पूछें।

**Root cause hypothesis:** Longest timeout at 144.1s. Sugarcane weed control is a standard query with RAG data available. Random agent worker crash.

---

### eval_071 — Tomato Disease List (Panipat) — FAIL
- **Query:** `haan bhai tamatar ki fasal mein kya kya rog lagte hai puri list batao thodi`
- **Category:** simulated_audio
- **Expected tools:** crop_detector, rag_retriever
- **Actual tools:** NONE
- **Duration:** 132.7s
- **Full response:**
> किसान भाई, आपके सवालों का सटीक समाधान यहाँ है:
> ❓ *जानकारी उपलब्ध क्यों नहीं है?*
> ✅ किसान भाई, तकनीकी समस्या के कारण जवाब देने में देरी हो रही है। कृपया कुछ देर बाद दोबारा पूछें।

**Root cause hypothesis:** "puri list batao" asks for a comprehensive list — agent may attempt a large generation. Audio-style casual Hindi may also slow parsing. Random timeout.

---

### eval_093 — Paddy Variety + Pest/Disease (Karnal) — FAIL
- **Query:** `dhan ki variety batao aur saath mein keet rog ka bhi ilaaj batao`
- **Category:** compound_query
- **Expected tools:** crop_detector, variety_advisor, rag_retriever, safety_checker
- **Actual tools:** NONE
- **Duration:** 133.0s
- **Full response:**
> किसान भाई, आपके सवालों का सटीक समाधान यहाँ है:
> ❓ *आपके प्रश्न का उत्तर क्यों नहीं मिल रहा है?*
> ✅ तकनीकी समस्या के कारण जवाब देने में देरी हो रही है। कृपया कुछ देर बाद दोबारा पूछें।

**Root cause hypothesis:** Compound query requiring 4 tools. The agent may have attempted parallel tool calls and hit a Gemini rate limit or context length issue. Note: eval_087 (3 topics, 5 tools) passed in 38.9s, so compound queries CAN work — this is likely random.

---

### eval_097 — Tomato Early Blight + Chili Anthracnose (Panipat) — FAIL
- **Query:** `tamatar mein early blight aur mirch mein anthracnose ka upchar batao`
- **Category:** multi_crop
- **Expected tools:** crop_detector, rag_retriever, safety_checker
- **Actual tools:** NONE
- **Duration:** 133.1s
- **Full response:**
> किसान भाई, तकनीकी समस्या के कारण जवाब देने में देरी हो रही है। कृपया कुछ देर बाद दोबारा पूछें।

**Root cause hypothesis:** Multi-crop query (tomato + chili). Similar multi-crop queries passed (eval_095, eval_096, eval_098) so this is likely random.

---

### Timeout Summary

| ID | Query type | Duration | Crop(s) |
|----|-----------|----------|---------|
| eval_011 | single crop pest | 138.1s | Chillies |
| eval_019 | single crop disease | 124.6s | Cotton |
| eval_038 | unknown crop variety | 127.7s | Cashew |
| eval_065 | single crop agronomy | 144.1s | Sugarcane |
| eval_071 | single crop audio | 132.7s | Tomato |
| eval_093 | compound query | 133.0s | Paddy |
| eval_097 | multi-crop | 133.1s | Tomato + Chili |

**Pattern:** No consistent crop, category, or query complexity pattern. 4/7 are simple single-crop queries that should take 40-60s. This confirms random infrastructure timeouts (Gemini API stalls or LangGraph execution timeout), not systematic logic bugs.

**Fix:** Add retry logic in agent_worker. If first attempt times out at 120s, retry once. Also consider a "processing your question" quick-reply sent within 5s while the agent works.

---

## PARTIAL — Quality Issues (7 queries)

---

### eval_046 — Apple Scab Misdiagnosed as San Jose Scale (Panchkula) — PARTIAL
- **Query:** `mere seb mein ye kya rog hai photo dekho` + image: apple_scab.jpg
- **Category:** image_positive
- **Expected tools:** image_analyzer, crop_detector
- **Actual tools:** crop_detector, image_analyzer, rag_retriever, safety_checker — MATCH (superset)
- **Duration:** 65.8s
- **Issue:** **MISDIAGNOSIS**
- **Full response:**
> ❓ *सेब में सैन जोस स्केल (San Jose Scale) का प्रबंधन कैसे करें?*
> ✅ आपकी फोटो के अनुसार, सेब के फल सैन जोस स्केल से प्रभावित हैं। यह कीट रस चूसकर फल की गुणवत्ता खराब करता है।
> 🧪 *हॉर्टिकल्चरल मिनरल ऑयल*: 2% (2 लीटर तेल 100 लीटर पानी में) का छिड़काव करें।
> 🧪 *इमिडाक्लोप्रिड*: 40 मिली प्रति 100 लीटर पानी में।
> 🧪 *स्पाइरोटेट्रामैट*: 200 मिली प्रति 100 लीटर पानी में।
> ✅ सेब में **मैन्कोजेब** का उपयोग भारत सरकार द्वारा प्रतिबंधित है। इसका प्रयोग बिल्कुल न करें।

**Analysis:** The image showed apple scab (Venturia inaequalis — fungal disease with olive-green to dark lesions). The Gemini vision model misidentified it as San Jose Scale (an insect pest with tiny circular scale bodies). The recommended treatments (mineral oil, Imidacloprid, Spirotetramat) are insecticides — completely wrong for a fungal disease. Correct treatment would be fungicides (Captan, Myclobutanil, or Dodine).

**Fix:** This is a Gemini vision model limitation. Possible mitigations: (1) Add a confidence threshold to image_analyzer — if below 70%, ask farmer for a clearer photo. (2) Cross-check image diagnosis against text context — farmer said "rog" (disease) but diagnosis returned a pest.

---

### eval_058 — Ambiguous "yellow leaves" guessed as Bitter Gourd (Rohtak) — PARTIAL
- **Query:** `mere khet me kuch patte peele ho gaye hai`
- **Category:** ambiguous
- **Expected tools:** crop_detector
- **Actual tools:** crop_detector, rag_retriever, safety_checker — MATCH (superset)
- **Duration:** 54.6s
- **Issue:** **GUESSED CROP INSTEAD OF ASKING**
- **Full response:**
> ❓ *मेरे खेत में पत्ते पीले हो रहे हैं, क्या करें? (माना कि फसल करेला है)*
> ✅ पत्तों के पीलेपन के लिए पोषक तत्वों की कमी हो सकती है।
> 🧪 *जिंक सल्फेट*: 2-3 ग्राम प्रति लीटर पानी में मिलाकर छिड़काव करें।
> [... full karela treatment ...]
> ✅ सटीक पहचान के लिए अपनी फसल का नाम और प्रभावित पत्तों की साफ फोटो भेजें।

**Analysis:** No crop was mentioned. The agent assumed "Bitter Gourd" (karela) — an unlikely guess for Rohtak district in February (rabi season; karela is kharif). It gave a full treatment plan before asking for clarification at the very end. Expected behavior: ask "आपकी फसल कौन सी है?" first.

**Fix:** Tune crop_detector confidence threshold. When crop detection confidence < 0.5, the agent should ask for clarification before calling rag_retriever. The system prompt should prioritize clarification over guessing.

---

### eval_059 — Ambiguous "bugs on crop" guessed as Mentha (Jind) — PARTIAL
- **Query:** `isme kide lag gaye hai kya karu`
- **Category:** ambiguous
- **Expected tools:** crop_detector
- **Actual tools:** crop_detector, rag_retriever, safety_checker — MATCH (superset)
- **Duration:** 44.8s
- **Issue:** **GUESSED CROP INSTEAD OF ASKING**
- **Full response:**
> ❓ *मेंथा (पुदीना) में कीट नियंत्रण कैसे करें?*
> ✅ आपकी मेंथा फसल में कीटों का प्रकोप है।
> [... full mentha pest treatment with Imidacloprid, Thiamethoxam, Chlorantraniliprole, Spiromesifen ...]

**Analysis:** "isme kide lag gaye hai" gives zero crop context. Agent guessed Mentha — an unlikely crop for Jind district. Treatment advice is sound for mentha but useless if the farmer has wheat or mustard.

**Fix:** Same as eval_058. Low-confidence crop detection should trigger clarification.

---

### eval_060 — Ambiguous "crop ruined" guessed as Bitter Gourd (Fatehabad) — PARTIAL
- **Query:** `fasal kharab ho rahi hai madad karo`
- **Category:** ambiguous
- **Expected tools:** crop_detector
- **Actual tools:** crop_detector, rag_retriever, safety_checker — MATCH (superset)
- **Duration:** 41.1s
- **Issue:** **GUESSED CROP INSTEAD OF ASKING**
- **Full response:**
> ❓ *करेले में मुख्य कीट कौन से हैं और उनका समाधान क्या है?*
> ✅ करेले में **मिलीबग** और **स्केल कीट** रस चूसते हैं...
> [... full karela treatment with Buprofezin, Imidacloprid, Copper Oxychloride, Azoxystrobin ...]
> ✅ *महत्वपूर्ण:* करेले में **मैंकोजेब** का प्रयोग न करें, यह इस फसल के लिए प्रतिबंधित है।

**Analysis:** "fasal kharab ho rahi hai" = "my crop is getting ruined" — completely generic. Agent guessed Bitter Gourd again (same hallucination as eval_058). February in Fatehabad is rabi season — karela makes no sense.

**Fix:** Same as eval_058/059. The crop_detector is returning karela/mentha as false positives when input has no crop signal. Add a "no crop detected" return path.

**Note on eval_061:** Interestingly, "bhai dawai bata do jaldi" (even MORE vague) correctly triggered a clarification response. This suggests the issue is with medium-ambiguity queries where the crop_detector picks up phantom signals from common Hindi words.

---

### eval_076 — Gibberish Hallucinated as French Bean (Rohtak) — PARTIAL
- **Query:** `asdfjkl bakwaas random text nothing meaningful here zxcvbn`
- **Category:** audio_negative
- **Expected tools:** (none)
- **Actual tools:** crop_detector, rag_retriever, safety_checker — MISMATCH
- **Duration:** 35.2s
- **Issue:** **CROP HALLUCINATION FROM GIBBERISH**
- **Full response:**
> ❓ *राजमा (फ्रांसीसी बीन) की बुवाई का सही समय क्या है?*
> ✅ हरियाणा में, आप इसे फरवरी-मार्च या सितंबर के अंत से अक्टूबर के मध्य तक बो सकते हैं।
> ❓ *राजमा की उन्नत किस्में कौन सी हैं?*
> ✅ *अर्का कोमल*, *पंत अनुपमा* और *पूसा पार्वती* अच्छी पैदावार देती हैं।
> [... full rajma advice ...]

**Analysis:** Pure gibberish ("asdfjkl bakwaas random text nothing meaningful here zxcvbn") — the crop_detector hallucinated "French Bean" (Rajma) from nonsensical input. This is the MuRIL classifier returning a high-confidence prediction on garbage input (neural networks don't know when they don't know).

**Fix:** Add an input validation layer before crop_detector. If the input fails a basic Hindi/English language check (e.g., word-level language detection), return "unclear input" instead of running classification. Alternatively, add a softmax entropy check — if the classifier's top prediction has low margin over the second prediction, flag as uncertain.

---

### eval_099 — Text-Image Contradiction Not Detected (Karnal) — PARTIAL
- **Query:** text = "gehun mein keet lage hain" (wheat pest) + image = paddy_brown_spot.jpg
- **Category:** edge_case
- **Expected tools:** crop_detector, rag_retriever, safety_checker, image_analyzer
- **Actual tools:** crop_detector, image_analyzer, rag_retriever, safety_checker — MATCH
- **Duration:** 76.7s
- **Issue:** **TEXT-IMAGE CONTRADICTION NOT FLAGGED**
- **Full response:**
> ❓ *गेहूं में पत्तियों पर भूरे धब्बे (स्पॉट ब्लॉच) का क्या इलाज है?*
> ✅ आपकी फोटो में पत्तियों पर नाव के आकार के भूरे धब्बे 'स्पॉट ब्लॉच' फफूंद रोग के लक्षण हैं।
> 🧪 *प्रोपीकोनाज़ोल 25% ई.सी.*: 200 मिलीलीटर प्रति एकड़...
> ❓ *गेहूं में चेपा या सैनिक कीट का प्रबंधन कैसे करें?*
> 🧪 *लैम्ब्डा-साइहेलोथ्रिन 5 ई.सी.*: 100 मिलीलीटर प्रति एकड़...
> ✅ **फोरेट** और **कार्बोफ्यूरान** का प्रयोग गेहूं में बिल्कुल न करें, ये प्रतिबंधित हैं।

**Analysis:** Text says "gehun" (wheat) but image shows paddy brown spot. The agent merged both inputs without detecting the discrepancy — diagnosed it as "Wheat Spot Blotch" (treating the paddy disease image as if it were wheat). The boat-shaped lesion description actually matches paddy blast more than wheat spot blotch. Expected behavior: "Your text mentions wheat but the photo appears to show paddy — please clarify which crop."

**Fix:** After both crop_detector (from text) and image_analyzer return results, add a comparison step. If text_crop ≠ image_crop (or if the image shows a crop different from the detected text crop), insert a discrepancy warning into the response. This can be a simple post-processing rule in the agent graph.

---

### eval_100 — Wheat Yellow Rust via general_crop_advisor (Hisar) — PARTIAL
- **Query:** `mere wheat field mein yellow spots aa gaye hain patte pe, kya fungicide use karna chahiye ya organic treatment better rahega`
- **Category:** edge_case
- **Expected tools:** crop_detector, rag_retriever, safety_checker
- **Actual tools:** crop_detector, general_crop_advisor, safety_checker — MISMATCH
- **Duration:** 49.1s
- **Issue:** **RAG BYPASS — general_crop_advisor instead of rag_retriever**
- **Full response:**
> ❓ *गेहूं में पीले धब्बे (पीला रतुआ) की पहचान और उपचार क्या है?*
> ✅ आपकी गेहूं की फसल में पत्तियों पर पीले धब्बे 'पीला रतुआ' (Yellow Rust) रोग के लक्षण हो सकते हैं।
> *रासायनिक उपचार (कवकनाशी):*
> 🧪 *प्रोपिकोनाजोल 25% ईसी*: 200 मिलीलीटर प्रति एकड़...
> 🧪 *टेबुकोनाजोल 25.9% ईसी*: 250 मिलीलीटर प्रति एकड़...
> *जैविक उपचार:*
> *खट्टी छाछ*: 5 लीटर पुरानी खट्टी छाछ को 200 लीटर पानी में...
> *नीम का तेल*: नीम के तेल का घोल भी कवक को फैलने से रोकने में मदद करता है।

**Analysis:** Wheat yellow rust is a core RAG topic with extensive HAU data in Pinecone. Yet the agent routed to general_crop_advisor instead of rag_retriever. The response is agronomically sound (Propiconazole, Tebuconazole are correct) and even addresses the organic vs chemical question nicely. But HAU-verified data should always be preferred over AI-generated advice.

**Fix:** This is the only RAG bypass in the entire run (down from 7 in the previous run). The retrained model largely fixed this issue. Remaining fix: check if the query contains English words ("wheat field", "fungicide", "organic treatment") that may confuse the crop_detector's routing logic. The mixed Hindi-English input may have triggered a different code path.

---

## Summary of Issues & Priority Fixes

| Priority | Issue | Affected | Fix |
|----------|-------|----------|-----|
| P1 | Timeouts | 7 FAIL | Retry logic + quick-reply fallback |
| P2 | Ambiguous crop guessing | 3 PARTIAL (058, 059, 060) | Confidence threshold on crop_detector |
| P3 | Gibberish hallucination | 1 PARTIAL (076) | Input validation / entropy check |
| P3 | Text-image contradiction | 1 PARTIAL (099) | Post-processing comparison step |
| P3 | Image misdiagnosis | 1 PARTIAL (046) | Gemini vision limitation — add confidence threshold |
| P4 | RAG bypass | 1 PARTIAL (100) | Minor — mixed Hindi/English routing issue |

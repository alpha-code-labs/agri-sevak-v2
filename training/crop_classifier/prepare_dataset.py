import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "shared" / "data"
OUTPUT_DIR = Path(__file__).parent / "dataset"
OUTPUT_DIR.mkdir(exist_ok=True)

TEMPLATES_EN = [
      "{crop} me kide lag gye",
      "{crop} me rog aa gya hai",
      "{crop} ki fasal kharab ho rhi",
      "{crop} me patte peele ho rahe hain",
      "{crop} pe phool nahi aa rahe",
      "{crop} ki patti gir rahi hai",
      "meri {crop} me kya problem hai",
      "{crop} me fungus lag gaya",
      "{crop} ki growth ruk gayi hai",
      "{crop} me safed makhi aa gayi",
      "{crop} pe thrips lage hue hain",
      "{crop} me jad galan rog",
      "{crop} ka upchar batao",
      "{crop} me keeda laga hai",
      "{crop} ki fasal sukhne lagi",
      "{crop} me dawai kya dalein",
      "{crop} ka achha beej kaun sa hai",
      "{crop} kab boye",
      "{crop} me paani kitna dein",
      "{crop} ki variety batao",
      "{crop} me kharpatwar aa gayi",
      "best pesticide for {crop}",
      "{crop} disease treatment",
      "{crop} pest control",
      "{crop} fertilizer recommendation",
  ]

TEMPLATES_HI = [
      "{crop} में कीड़े लग गए",
      "{crop} में रोग आ गया है",
      "{crop} की फसल खराब हो रही",
      "{crop} में पत्ते पीले हो रहे हैं",
      "{crop} पर फूल नहीं आ रहे",
      "{crop} की पत्ती गिर रही है",
      "मेरी {crop} में क्या समस्या है",
      "{crop} में फफूंद लग गया",
      "{crop} की ग्रोथ रुक गई है",
      "{crop} में सफेद मक्खी आ गई",
      "{crop} पर थ्रिप्स लगे हुए हैं",
      "{crop} में जड़ गलन रोग",
      "{crop} का उपचार बताओ",
      "{crop} में कीड़ा लगा है",
      "{crop} की फसल सूखने लगी",
      "{crop} में दवाई क्या डालें",
      "{crop} का अच्छा बीज कौन सा है",
      "{crop} कब बोयें",
      "{crop} में पानी कितना दें",
      "{crop} की किस्म बताओ",
  ]


def load_crops():
      with open(DATA_DIR / "crops.json", "r") as f:
          return json.load(f)["crops"]


def load_varieties():
      with open(DATA_DIR / "varieties_and_sowing_time.json", "r") as f:
          return json.load(f)["records"]


def generate_examples(crops, varieties):
      examples_by_crop = {}

      # 1. From crops.json synonyms
      for crop in crops:
          master = crop["master_name"]
          if master not in examples_by_crop:
              examples_by_crop[master] = []

          all_names = []
          for syn in crop["synonyms"]:
              all_names.append(syn["en"])
              all_names.append(syn["hi"])
          all_names = list(set(all_names))

          for name in all_names:
              # Plain name
              examples_by_crop[master].append(name)
              examples_by_crop[master].append(f"{name} ki samasya")

              # English/Hinglish templates
              for template in TEMPLATES_EN:
                  examples_by_crop[master].append(template.format(crop=name))

              # Hindi templates for Hindi names
              if any(ord(c) > 127 for c in name):
                  for template in TEMPLATES_HI:
                      examples_by_crop[master].append(template.format(crop=name))

      # 2. From varieties data — variety name → crop
      for record in varieties:
          crop_name = record["Crop"]
          variety = record["Variety"]
          if crop_name not in examples_by_crop:
              examples_by_crop[crop_name] = []

          examples_by_crop[crop_name].append(variety)
          examples_by_crop[crop_name].append(f"{variety} ki samasya")
          examples_by_crop[crop_name].append(f"{variety} me kide lag gye")
          examples_by_crop[crop_name].append(f"{variety} me rog aa gya")
          examples_by_crop[crop_name].append(f"{variety} kab boye")
          examples_by_crop[crop_name].append(f"{variety} ki fasal")

      # 3. Balance — oversample small crops to match median count
      counts = [len(v) for v in examples_by_crop.values()]
      target = int(sorted(counts)[len(counts) // 2])  # median
      print(f"Balancing: min={min(counts)}, median={target}, max={max(counts)}")

      balanced = []
      for crop_name, texts in examples_by_crop.items():
          if len(texts) >= target:
              sampled = random.sample(texts, target)
          else:
              # Oversample by repeating
              sampled = texts.copy()
              while len(sampled) < target:
                  sampled.append(random.choice(texts))
          for text in sampled:
              balanced.append({"text": text, "label": crop_name})

      random.shuffle(balanced)
      return balanced


def main():
      crops = load_crops()
      varieties = load_varieties()
      print(f"Loaded {len(crops)} crops, {len(varieties)} variety records")

      examples = generate_examples(crops, varieties)
      print(f"Generated {len(examples)} balanced examples")

      # Build label map
      labels = sorted(set(e["label"] for e in examples))
      label_to_id = {label: i for i, label in enumerate(labels)}
      print(f"Labels: {len(labels)} unique crops")

      # Split: 85% train, 15% eval
      split_idx = int(len(examples) * 0.85)
      train = examples[:split_idx]
      eval_ = examples[split_idx:]

      # Save
      with open(OUTPUT_DIR / "train.jsonl", "w") as f:
          for ex in train:
              ex["label_id"] = label_to_id[ex["label"]]
              f.write(json.dumps(ex, ensure_ascii=False) + "\n")

      with open(OUTPUT_DIR / "eval.jsonl", "w") as f:
          for ex in eval_:
              ex["label_id"] = label_to_id[ex["label"]]
              f.write(json.dumps(ex, ensure_ascii=False) + "\n")

      with open(OUTPUT_DIR / "label_map.json", "w") as f:
          json.dump({"label_to_id": label_to_id, "id_to_label": {v: k for k, v in label_to_id.items()}}, f, indent=2, ensure_ascii=False)

      print(f"Train: {len(train)} examples")
      print(f"Eval:  {len(eval_)} examples")


if __name__ == "__main__":
      main()

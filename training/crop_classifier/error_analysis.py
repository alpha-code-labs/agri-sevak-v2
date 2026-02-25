import json
import torch                                                                                                                                                                                                    
from pathlib import Path                                                                                                                                                                                      
from collections import Counter
from transformers import AutoTokenizer, AutoModelForSequenceClassification

DATASET_DIR = Path(__file__).parent / "dataset"
MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "crop_classifier"


def main():
      tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
      model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
      model.eval()

      with open(MODEL_DIR / "label_map.json", "r") as f:
          label_data = json.load(f)
      id_to_label = {int(k): v for k, v in label_data["id_to_label"].items()}

      eval_examples = []
      with open(DATASET_DIR / "eval.jsonl", "r") as f:
          for line in f:
              eval_examples.append(json.loads(line))

      # Track failures
      failures = []
      confusion = Counter()

      for ex in eval_examples:
          inputs = tokenizer(ex["text"], truncation=True, padding="max_length",
                             max_length=64, return_tensors="pt")
          with torch.no_grad():
              logits = model(**inputs).logits[0]

          pred_id = torch.argmax(logits).item()
          pred_label = id_to_label[pred_id]
          expected = ex["label"]

          if pred_label != expected:
              failures.append({
                  "text": ex["text"],
                  "expected": expected,
                  "predicted": pred_label,
              })
              confusion[(expected, pred_label)] += 1

      # Print top 20 most common confusions
      print(f"Total failures: {len(failures)} / {len(eval_examples)}")
      print(f"\nTop 20 confusions (expected → predicted):")
      print("-" * 60)
      for (exp, pred), count in confusion.most_common(20):
          print(f"  {exp:25s} → {pred:25s} ({count}x)")

      # Print 10 sample failures
      print(f"\nSample failures:")
      print("-" * 60)
      for f in failures[:10]:
          print(f"  Input:    {f['text'][:60]}")
          print(f"  Expected: {f['expected']}")
          print(f"  Got:      {f['predicted']}")
          print()


if __name__ == "__main__":
      main()
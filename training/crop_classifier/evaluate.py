import json
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification

DATASET_DIR = Path(__file__).parent / "dataset"
MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "crop_classifier"


def main():
      # Load model
      print(f"Loading model from {MODEL_DIR}...")
      tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
      model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
      model.eval()

      # Load label map
      with open(MODEL_DIR / "label_map.json", "r") as f:
          label_data = json.load(f)
      id_to_label = {int(k): v for k, v in label_data["id_to_label"].items()}

      # Load eval data
      eval_examples = []
      with open(DATASET_DIR / "eval.jsonl", "r") as f:
          for line in f:
              eval_examples.append(json.loads(line))

      print(f"Evaluating on {len(eval_examples)} examples...")

      correct_top1 = 0
      correct_top3 = 0
      total = len(eval_examples)

      for ex in eval_examples:
          inputs = tokenizer(ex["text"], truncation=True, padding="max_length",
                             max_length=64, return_tensors="pt")

          with torch.no_grad():
              outputs = model(**inputs)
              logits = outputs.logits[0]

          top3_ids = torch.topk(logits, 3).indices.tolist()
          top1_label = id_to_label[top3_ids[0]]
          top3_labels = [id_to_label[i] for i in top3_ids]

          expected = ex["label"]

          if top1_label == expected:
              correct_top1 += 1
          if expected in top3_labels:
              correct_top3 += 1

      acc_top1 = correct_top1 / total * 100
      acc_top3 = correct_top3 / total * 100

      print(f"\n{'='*50}")
      print(f"  CROP CLASSIFIER EVALUATION")
      print(f"{'='*50}")
      print(f"  Total examples:    {total}")
      print(f"  Top-1 accuracy:    {acc_top1:.1f}%  {'PASS' if acc_top1 >= 90 else 'FAIL'} (target ≥90%)")
      print(f"  Top-3 accuracy:    {acc_top3:.1f}%  {'PASS' if acc_top3 >= 95 else 'FAIL'} (target ≥95%)")
      print(f"{'='*50}")


if __name__ == "__main__":
      main()
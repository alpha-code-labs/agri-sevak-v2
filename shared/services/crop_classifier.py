import json                                                                                                                                                                                                                                                                
import torch                                                                                                                                                                                                                                                               
from pathlib import Path                                                                                                                                                                                                                                                   
from transformers import AutoTokenizer, AutoModelForSequenceClassification                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                                             
class CropClassifier:                                                                                                                                                                                                                                                    
      def __init__(self, model_path: str):
          self.model_path = Path(model_path)
          self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
          self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_path))
          self.model.eval()

          with open(self.model_path / "label_map.json", "r") as f:
              label_data = json.load(f)
          self.id_to_label = {int(k): v for k, v in label_data["id_to_label"].items()}

      def predict(self, text: str, top_k: int = 3) -> list[dict]:
          """Returns top-k predictions with confidence scores."""
          inputs = self.tokenizer(text, truncation=True, padding="max_length",
                                  max_length=64, return_tensors="pt")
          with torch.no_grad():
              logits = self.model(**inputs).logits[0]

          probs = torch.softmax(logits, dim=0)
          top_k_values, top_k_ids = torch.topk(probs, top_k)

          return [
              {"crop": self.id_to_label[idx.item()], "confidence": round(conf.item(), 4)}
              for conf, idx in zip(top_k_values, top_k_ids)
          ]
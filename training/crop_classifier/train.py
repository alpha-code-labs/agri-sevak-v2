import json
import torch
from pathlib import Path
from torch.utils.data import Dataset
from transformers import (
      AutoTokenizer,
      AutoModelForSequenceClassification,
      Trainer,
      TrainingArguments,
  )

DATASET_DIR = Path(__file__).parent / "dataset"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "models" / "crop_classifier"


class CropDataset(Dataset):
      def __init__(self, filepath, tokenizer, max_length=64):
          self.examples = []
          with open(filepath, "r") as f:
              for line in f:
                  self.examples.append(json.loads(line))
          self.tokenizer = tokenizer
          self.max_length = max_length

      def __len__(self):
          return len(self.examples)

      def __getitem__(self, idx):
          ex = self.examples[idx]
          encoding = self.tokenizer(
              ex["text"],
              truncation=True,
              padding="max_length",
              max_length=self.max_length,
              return_tensors="pt",
          )
          return {
              "input_ids": encoding["input_ids"].squeeze(),
              "attention_mask": encoding["attention_mask"].squeeze(),
              "labels": torch.tensor(ex["label_id"], dtype=torch.long),
          }


def main():
      # Load label map
      with open(DATASET_DIR / "label_map.json", "r") as f:
          label_data = json.load(f)
      num_labels = len(label_data["label_to_id"])
      print(f"Number of labels: {num_labels}")

      # Load model and tokenizer
      model_name = "google/muril-base-cased"
      print(f"Loading {model_name}...")
      tokenizer = AutoTokenizer.from_pretrained(model_name)
      model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)

      # Load datasets
      train_dataset = CropDataset(DATASET_DIR / "train.jsonl", tokenizer)
      eval_dataset = CropDataset(DATASET_DIR / "eval.jsonl", tokenizer)
      print(f"Train: {len(train_dataset)} examples")
      print(f"Eval:  {len(eval_dataset)} examples")

      # Training arguments
      training_args = TrainingArguments(        
          output_dir=str(OUTPUT_DIR),                
          num_train_epochs=8,              
          per_device_train_batch_size=16,      
          per_device_eval_batch_size=64,    
          learning_rate=3e-5,
          warmup_steps=200,                                                                                                                                                                                       
          weight_decay=0.01,
          eval_strategy="epoch",                                                                                                                                                                                  
          save_strategy="epoch",                                                                                                                                                                                
          load_best_model_at_end=True,
          metric_for_best_model="eval_loss",
          logging_steps=50,
          report_to="none",
          fp16=False,
      )

      # Train
      trainer = Trainer(
          model=model,
          args=training_args,
          train_dataset=train_dataset,
          eval_dataset=eval_dataset,
      )

      print("Starting training...")
      trainer.train()

      # Save final model
      trainer.save_model(str(OUTPUT_DIR))
      tokenizer.save_pretrained(str(OUTPUT_DIR))

      # Save label map alongside model
      import shutil
      shutil.copy(DATASET_DIR / "label_map.json", OUTPUT_DIR / "label_map.json")

      print(f"Model saved to {OUTPUT_DIR}")


if __name__ == "__main__":
      main()

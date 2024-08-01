import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, DataCollatorForLanguageModeling
import os
import subprocess

# Schritt 1: Trainingsdaten laden
with open('training_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extrahieren der Inhalte für das Training
texts = [item['content'] for item in data]

# Schritt 2: Tokenizer und Modell initialisieren
model_name = "distilgpt2"  # Oder ein anderes Modell Ihrer Wahl
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Padding-Token setzen
tokenizer.pad_token = tokenizer.eos_token

# Tokenisieren der Trainingsdaten
tokenized_texts = tokenizer(texts, return_tensors='pt', padding=True, truncation=True, max_length=512)

# Schritt 3: Dataset erstellen
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, encodings):
        self.encodings = encodings

    def __getitem__(self, idx):
        return {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}

    def __len__(self):
        return len(self.encodings.input_ids)

dataset = CustomDataset(tokenized_texts)

# Schritt 4: Trainingsparameter festlegen
training_args = TrainingArguments(
    output_dir='./trained_model',
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_steps=10_000,
    save_total_limit=2,
    prediction_loss_only=True,
)

# Trainer initialisieren
data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
trainer = Trainer(
    model=model,
    args=training_args,
    data_collator=data_collator,
    train_dataset=dataset,
)

# Modell trainieren
trainer.train()

# Speichern des trainierten Modells
model.save_pretrained('./trained_model')
tokenizer.save_pretrained('./trained_model')

# Git LFS Befehle ausführen
if not os.path.exists(".gitattributes"):
    subprocess.run(["git", "lfs", "install"])
    subprocess.run(["git", "lfs", "track", "*.bin"])
    subprocess.run(["git", "lfs", "track", "*.h5"])

# Git Befehle zum Hinzufügen und Committen der Modell-Dateien
subprocess.run(["git", "add", ".gitattributes"])
subprocess.run(["git", "add", "trained_model/pytorch_model.bin"])
subprocess.run(["git", "commit", "-m", "Add trained model with Git LFS"])
subprocess.run(["git", "push"])

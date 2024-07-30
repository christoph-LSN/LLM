import os
import pandas as pd
from transformers import Trainer, TrainingArguments, AutoTokenizer, AutoModelForCausalLM
from datasets import Dataset, DatasetDict

# Funktion zum Laden von Daten aus einer Datei
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return text

# Laden des Webseiteninhalts
webpage_content = load_data('webpage_content.txt')

# Funktion zum Laden und Verarbeiten von CSV-Dateien
def load_csv_data(folder_path):
    data = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            df = pd.read_csv(os.path.join(folder_path, filename))
            data.append(df.to_string(index=False))
    return data

# Funktion zum Laden und Verarbeiten von Metadaten-Dateien
def load_meta_data(folder_path):
    data = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.md'):
            data.append(load_data(os.path.join(folder_path, filename)))
    return data

# Laden der CSV-Daten
csv_data = load_csv_data('indicator_CSV')

# Laden der Metadaten
meta_data = load_meta_data('indicator_meta')

# Zusammenführen aller Daten
all_data = [webpage_content] + csv_data + meta_data

# Erstellen eines Datasets
dataset = Dataset.from_dict({"text": all_data})
datasets = DatasetDict({"train": dataset})

# Tokenizer und Modell laden
model_name = 'gpt2'  # oder ein anderes Modell wie 'gpt3' oder 'gpt4', wenn du Zugang hast
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Tokenisierung der Daten
def tokenize_function(examples):
    return tokenizer(examples['text'], return_special_tokens_mask=True, padding="max_length", truncation=True, max_length=512)

tokenized_datasets = datasets.map(tokenize_function, batched=True, num_proc=4, remove_columns=['text'])

# Trainingsparameter definieren
training_args = TrainingArguments(
    output_dir='./results',
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=2,  # Reduziere die Batch-Größe, um Speicherprobleme zu vermeiden
    save_steps=10_000,
    save_total_limit=2,
)

# Trainer initialisieren
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets['train'],
)

# Modell trainieren
trainer.train()

# Modell speichern
model.save_pretrained('./trained_model')
tokenizer.save_pretrained('./trained_model')

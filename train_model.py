import os
from transformers import Trainer, TrainingArguments, AutoTokenizer, AutoModelForCausalLM
from datasets import load_dataset, Dataset

# Laden der Daten
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return text

data = load_data('webpage_content.txt')

# Datensatz erstellen
dataset = Dataset.from_dict({"text": [data]})

# Tokenizer und Modell laden
model_name = 'gpt2'  # oder ein anderes Modell wie 'gpt3' oder 'gpt4', wenn du Zugang hast
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Tokenisierung der Daten
def tokenize_function(examples):
    return tokenizer(examples['text'], return_special_tokens_mask=True, padding="max_length", truncation=True, max_length=512)

tokenized_datasets = dataset.map(tokenize_function, batched=True, num_proc=4, remove_columns=['text'])

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
    train_dataset=tokenized_datasets,
)

# Modell trainieren
trainer.train()

# Modell speichern
model.save_pretrained('./trained_model')
tokenizer.save_pretrained('./trained_model')

from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM
import os

app = Flask(__name__)

# Laden des trainierten Modells
model_name = 'LMM/trained_model'  # Dies sollte das Verzeichnis sein, in dem Ihr Modell liegt
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    inputs = tokenizer.encode(user_input, return_tensors='pt')
    outputs = model.generate(inputs, max_length=500)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return jsonify({'response': response})

# Debug-Route, um sicherzustellen, dass die Modell-Dateien vorhanden sind
@app.route('/debug', methods=['GET'])
def debug():
    files = []
    for root, dirs, file_names in os.walk(model_name):
        for file_name in file_names:
            files.append(os.path.join(root, file_name))
    return jsonify({'files': files})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


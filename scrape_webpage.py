import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import yaml
import re
import csv

# Setze die URL der Website, die gescrapet werden soll
BASE_URL = 'https://christoph-lsn.github.io/MT_Site/'
INDICATOR_LIST_URL = 'https://christoph-lsn.github.io/MT_Site/indicator_list/'
TRAINING_DATA_FILE = 'training_data.json'
YAML_URL = 'https://raw.githubusercontent.com/christoph-LSN/IM-translations/2.3.0-dev/translations/de/global_indicators.yml'
METADATA_BASE_URL = 'https://raw.githubusercontent.com/christoph-LSN/LLM/main/indicator_meta/'
CSV_BASE_URL = 'https://raw.githubusercontent.com/christoph-LSN/LLM/main/indicator_CSV/'

# Lade die YAML-Datei mit den Indikatornamen herunter und parse sie
def load_indicator_names():
    response = requests.get(YAML_URL)
    if response.status_code == 200:
        return yaml.safe_load(response.text)
    else:
        print("Fehler beim Laden der YAML-Datei.")
        return None

# Text reinigen (falls erforderlich)
def clean_text(text):
    return text.strip()

# Hauptseite scrapen und alle Links zu den Indikatorseiten sammeln
def scrape_indicator_list():
    response = requests.get(INDICATOR_LIST_URL)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        indicator_links = []

        # Regex zur Identifizierung der Links mit dem Muster '1-1-1'
        indicator_pattern = re.compile(r'\d+-\d+-\d+')

        # Alle Links auf der Seite durchsuchen
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Prüfen, ob der Link das Muster '1-1-1' enthält
            if indicator_pattern.search(href):
                full_url = urljoin(BASE_URL, href)
                indicator_links.append({
                    'name': clean_text(link.text),
                    'url': full_url
                })
        return indicator_links
    else:
        print("Fehler beim Laden der Indikator-Liste.")
        return []

# Lade die Metadaten aus der .md Datei auf GitHub
def load_metadata(indicator_id):
    metadata_url = f'{METADATA_BASE_URL}{indicator_id}.md'
    response = requests.get(metadata_url)
    if response.status_code == 200:
        metadata_text = response.text
        metadata = parse_metadata_from_markdown(metadata_text)
        return metadata
    else:
        print(f"Metadatei nicht gefunden: {metadata_url}")
        return {}

# Extrahiere die relevanten Informationen aus dem Markdown-Text
def parse_metadata_from_markdown(markdown_text):
    metadata = {}
    metadata['national_indicator_description'] = clean_field(extract_field_from_markdown(markdown_text, 'national_indicator_description'))
    metadata['computation_calculations'] = clean_field(extract_field_from_markdown(markdown_text, 'computation_calculations'))
    metadata['other_info'] = clean_field(extract_field_from_markdown(markdown_text, 'other_info'))

    tags = extract_field_from_markdown(markdown_text, 'tags')
    if tags:
        metadata['tags'] = tags.split('\n')[0].strip()
    return metadata

# Hilfsfunktion, um ein bestimmtes Feld aus dem Markdown-Text zu extrahieren
def extract_field_from_markdown(markdown_text, field_name):
    pattern = re.compile(rf'{field_name}:\s*([\s\S]+?)(\n[a-zA-Z_]+:|\Z)', re.MULTILINE)
    match = pattern.search(markdown_text)
    if match:
        return match.group(1).strip()
    return None

# Funktion zur Bereinigung von Markdown-Spezifischen Symbolen wie ">-" und "\r\n"
def clean_field(field_text):
    if field_text:
        field_text = re.sub(r'>-\s*|\r\n|\n', ' ', field_text)
        field_text = re.sub(r'\s+', ' ', field_text)
    return field_text.strip() if field_text else field_text

# Funktion zum Laden der CSV-Daten eines Indikators
def load_csv_data(indicator_id):
    csv_url = f'{CSV_BASE_URL}indicator_{indicator_id}.csv'
    response = requests.get(csv_url)
    if response.status_code == 200:
        csv_data = []
        decoded_content = response.content.decode('utf-8')
        csv_reader = csv.DictReader(decoded_content.splitlines())
        for row in csv_reader:
            csv_data.append(row)
        return csv_data
    else:
        print(f"CSV-Datei nicht gefunden: {csv_url}")
        return None

# JSON-Daten erstellen
def create_json_output(indicator_links, yaml_data):
    output_data = []
    for indicator in indicator_links:
        indicator_url = indicator['url']
        indicator_id = indicator_url.split('/')[-2]

        metadata = load_metadata(indicator_id)
        indicator_name = yaml_data.get(f'{indicator_id}-title', indicator['name'])

        csv_data = load_csv_data(indicator_id)

        entry = {
            'id': indicator_id,
            'name': indicator_name,
            'url': indicator_url,
            'definition': metadata.get('national_indicator_description'),
            'methodology': metadata.get('computation_calculations'),
            'additional_info': metadata.get('other_info'),
            'data_status': metadata.get('tags', None),
            'csv_data': csv_data
        }

        output_data.append(entry)
    return output_data

# Hauptfunktion zum Scrapen und Erstellen der JSON-Datei
def main():
    yaml_data = load_indicator_names()
    if yaml_data is None:
        return

    indicator_links = scrape_indicator_list()
    json_data = create_json_output(indicator_links, yaml_data)

    with open(TRAINING_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    print(f"JSON-Datei '{TRAINING_DATA_FILE}' erfolgreich erstellt.")

if __name__ == "__main__":
    main()

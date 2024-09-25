import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import yaml
import re

# Setze die URL der Website, die gescrapet werden soll
BASE_URL = 'https://christoph-lsn.github.io/MT_Site/'
INDICATOR_LIST_URL = 'https://christoph-lsn.github.io/MT_Site/indicator_list/'
TRAINING_DATA_FILE = 'training_data.json'
YAML_URL = 'https://raw.githubusercontent.com/christoph-LSN/IM-translations/2.3.0-dev/translations/de/global_indicators.yml'
METADATA_DIR = 'LLM/indicator_meta/'

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

# Lade die Metadaten aus dem Verzeichnis LLM/indicator_meta
def load_metadata(indicator_id):
    metadata_file = os.path.join(METADATA_DIR, f'{indicator_id}.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f"Metadatei nicht gefunden: {metadata_file}")
        return {}

# JSON-Daten erstellen
def create_json_output(indicator_links, yaml_data):
    output_data = []
    for indicator in indicator_links:
        # Extrahiere die Indikator-ID aus der URL
        indicator_url = indicator['url']
        indicator_id = indicator_url.split('/')[-2]  # Holt den '1-1-1' Teil der URL
        
        # Lade die Metadaten für diesen Indikator
        metadata = load_metadata(indicator_id)
        
        # Finde den Indikatornamen in der YAML-Datei
        indicator_name = yaml_data.get(f'{indicator_id}-title', indicator['name'])

        entry = {
            'id': indicator_id,
            'name': indicator_name,
            'url': indicator_url,
            'definition': metadata.get('national_indicator_description'),  # Definition des Indikators
            'methodology': metadata.get('computation_calculations'),       # Methodische Hinweise
            'additional_info': metadata.get('other_info'),                 # Weiterführende Hinweise
            'data_status': metadata.get('tags', [None, None])[0],          # Erster Eintrag im 'tags'-Feld für Datenstand
            'source_url_1': metadata.get('source_url_1'),                  # Quelle 1 URL
            'source_url_text_1': metadata.get('source_url_text_1'),        # Quelle 1 Text
            'source_url_2': metadata.get('source_url_2'),                  # Quelle 2 URL
            'source_url_text_2': metadata.get('source_url_text_2')         # Quelle 2 Text
        }

        output_data.append(entry)
    return output_data

# Hauptfunktion zum Scrapen und Erstellen der JSON-Datei
def main():
    # Lade die YAML-Daten
    yaml_data = load_indicator_names()
    if yaml_data is None:
        return

    # Scrape die Indikator-Liste
    indicator_links = scrape_indicator_list()

    # Erstellen der JSON-Datenstruktur
    json_data = create_json_output(indicator_links, yaml_data)

    # Speichern der Daten in einer JSON-Datei
    with open(TRAINING_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    print(f"JSON-Datei '{TRAINING_DATA_FILE}' erfolgreich erstellt.")

if __name__ == "__main__":
    main()

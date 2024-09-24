import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import json
import re

# Setze die URL der Website, die gescrapet werden soll
BASE_URL = 'https://christoph-lsn.github.io/MT_Site/'
MAX_PAGES = 90
CSV_DIR = 'indicator_CSV'
META_DIR = 'indicator_meta'
TRAINING_DATA_FILE = 'training_data.json'

def clean_text(text):
    """Bereinigt den Text von Steuerzeichen, mehrfachen Leerzeichen und HTML-Sonderzeichen."""
    # Entferne Steuerzeichen und ersetze multiple Leerzeichen durch ein einziges
    text = re.sub(r'\s+', ' ', text)
    # Entferne typische HTML-Sonderzeichen
    text = text.replace('\u00a0', ' ').replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    # Weitere HTML-Steuerzeichen entfernen (optional)
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Entfernt nicht-ASCII-Zeichen
    return text.strip()

def get_all_links(url):
    """Gibt eine Liste aller internen Links auf der Seite zurück."""
    links = set()
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(url, href)
            if urlparse(absolute_url).netloc == urlparse(BASE_URL).netloc:
                links.add(absolute_url)
    except Exception as e:
        print(f'Fehler beim Abrufen von Links von {url}: {e}')
    return links

def scrape_page(url, visited, data):
    """Scrapet den Inhalt einer Seite und fügt ihn zu visited hinzu."""
    if url in visited or len(visited) >= MAX_PAGES:
        return

    print(f'Scraping {url}')
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        webpage_text = soup.get_text(separator=" ").strip()
        cleaned_text = clean_text(webpage_text)  # Bereinigung des Texts
        
        if cleaned_text:
            data.append({
                'content': cleaned_text,
                'url': url
            })

        visited.add(url)
        links = get_all_links(url)
        for link in links:
            scrape_page(link, visited, data)
    except Exception as e:
        print(f'Fehler beim Scraping von {url}: {e}')

def append_csv_and_meta_content(csv_dir, meta_dir, data):
    """Liest alle CSV-Dateien und zugehörigen Metadatendateien im Verzeichnis und fügt deren Inhalt zur Liste hinzu."""
    for filename in os.listdir(csv_dir):
        if filename.endswith('.csv'):
            csv_filepath = os.path.join(csv_dir, filename)
            meta_filename = filename.replace('_indicator.csv', '_meta.md')
            meta_filepath = os.path.join(meta_dir, meta_filename)
            try:
                # Lesen und Hinzufügen des Inhalts der CSV-Datei
                with open(csv_filepath, 'r', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    csv_content = f'CSV-Datei: {filename}\n'
                    for row in reader:
                        csv_content += ','.join(row) + '\n'
                    data.append({
                        'content': csv_content.strip(),
                        'url': f'localfile://{csv_filepath}'
                    })

                # Lesen und Hinzufügen des Inhalts der Metadatendatei
                if os.path.exists(meta_filepath):
                    with open(meta_filepath, 'r', encoding='utf-8') as metafile:
                        meta_content = clean_text(metafile.read().strip())  # Bereinigung des Texts
                        data.append({
                            'content': meta_content,
                            'url': f'localfile://{meta_filepath}'
                        })
            except Exception as e:
                print(f'Fehler beim Lesen der Datei {filename} oder {meta_filename}: {e}')

if __name__ == "__main__":
    visited_urls = set()
    data = []
    scrape_page(BASE_URL, visited_urls, data)
    append_csv_and_meta_content(CSV_DIR, META_DIR, data)
    
    # Speichern der gesammelten Daten in einer JSON-Datei
    with open(TRAINING_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print('Scraping abgeschlossen und Trainingsdaten gespeichert.')

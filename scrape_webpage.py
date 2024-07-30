import os
import requests
from bs4 import BeautifulSoup
from urllib.parse: urljoin, urlparse
import csv

# Setze die URL der Website, die gescrapet werden soll
BASE_URL = 'https://christoph-lsn.github.io/MT_Site/'
# Setze die maximale Anzahl an zu durchsuchenden Seiten
MAX_PAGES = 90
# Setze den Pfad zur Datei, in der der Inhalt gespeichert wird
OUTPUT_FILE = 'webpage_content.txt'
# Verzeichnis, in dem die CSV-Dateien gespeichert sind
CSV_DIR = 'indicator_CSV'
# Verzeichnis, in dem die Metadatendateien gespeichert sind
META_DIR = 'indicator_meta'

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

def scrape_page(url, visited):
    """Scrapet den Inhalt einer Seite und fügt ihn zu visited hinzu."""
    if url in visited or len(visited) >= MAX_PAGES:
        return

    print(f'Scraping {url}')
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        webpage_text = soup.get_text()
        
        # Füge den gescrapten Text der Datei hinzu
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as file:
            file.write(f'URL: {url}\n')
            file.write(webpage_text)
            file.write('\n' + '-'*80 + '\n')
        
        visited.add(url)
        links = get_all_links(url)
        for link in links:
            scrape_page(link, visited)
    except Exception as e:
        print(f'Fehler beim Scraping von {url}: {e}')

def append_csv_and_meta_content(csv_dir, meta_dir, output_file):
    """Liest alle CSV-Dateien und zugehörigen Metadatendateien im Verzeichnis und fügt deren Inhalt zur Ausgabedatei hinzu."""
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
                    with open(output_file, 'a', encoding='utf-8') as file:
                        file.write(csv_content)
                        file.write('\n' + '-'*80 + '\n')
                print(f'Inhalt der Datei {filename} hinzugefügt.')

                # Lesen und Hinzufügen des Inhalts der Metadatendatei
                if os.path.exists(meta_filepath):
                    with open(meta_filepath, 'r', encoding='utf-8') as metafile:
                        meta_content = metafile.read()
                        with open(output_file, 'a', encoding='utf-8') as file:
                            file.write(f'Metadaten-Datei: {meta_filename}\n')
                            file.write(meta_content)
                            file.write('\n' + '-'*80 + '\n')
                    print(f'Inhalt der Metadatendatei {meta_filename} hinzugefügt.')
                else:
                    print(f'Metadatendatei {meta_filename} nicht gefunden.')
            except Exception as e:
                print(f'Fehler beim Lesen der Datei {filename} oder {meta_filename}: {e}')

if __name__ == "__main__":
    visited_urls = set()
    scrape_page(BASE_URL, visited_urls)
    append_csv_and_meta_content(CSV_DIR, META_DIR, OUTPUT_FILE)
    print('Scraping abgeschlossen.')

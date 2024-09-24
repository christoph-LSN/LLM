import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import re

# Setze die URL der Website, die gescrapet werden soll
BASE_URL = 'https://christoph-lsn.github.io/MT_Site/'
MAX_PAGES = 90
TRAINING_DATA_FILE = 'training_data.json'

def clean_text(text):
    """Bereinigt den Text von Steuerzeichen, mehrfachen Leerzeichen und HTML-Sonderzeichen."""
    text = re.sub(r'\s+', ' ', text)  # Entferne doppelte Leerzeichen
    text = text.replace('\u00a0', ' ').replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
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
        
        # Finde die Indikatoren-Überschriften und deren Beschreibungen
        headers = soup.find_all('h2')  # Annahme: Indikatoren haben h2 als Überschrift
        for header in headers:
            indicator_title = clean_text(header.get_text())
            # Suchen nach der nächsten Definition im Text (p-Tags für die Beschreibungen)
            paragraph = header.find_next('p')
            if paragraph:
                description = clean_text(paragraph.get_text())
                data.append({
                    'title': indicator_title,
                    'description': description,
                    'url': url
                })

        visited.add(url)
        links = get_all_links(url)
        for link in links:
            scrape_page(link, visited, data)
    except Exception as e:
        print(f'Fehler beim Scraping von {url}: {e}')

if __name__ == "__main__":
    visited_urls = set()
    data = []
    scrape_page(BASE_URL, visited_urls, data)
    
    # Speichern der gesammelten Daten in einer JSON-Datei
    with open(TRAINING_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print('Scraping abgeschlossen und Trainingsdaten gespeichert.')

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Setze die URL der Website, die gescrapet werden soll
BASE_URL = 'https://christoph-lsn.github.io/MT_Site/'

# Setze die maximale Anzahl an zu durchsuchenden Seiten
MAX_PAGES = 50

# Setze den Pfad zur Datei, in der der Inhalt gespeichert wird
OUTPUT_FILE = 'webpage_content.txt'

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

if __name__ == "__main__":
    visited_urls = set()
    scrape_page(BASE_URL, visited_urls)
    print('Scraping abgeschlossen.')

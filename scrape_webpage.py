import os
import requests
from bs4 import BeautifulSoup

def scrape_webpage(url, output_file):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extrahiere Text von der Webseite
    webpage_text = soup.get_text()

    # Speichere den Text in einer Datei
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(webpage_text)

if __name__ == "__main__":
    url = os.getenv('WEBPAGE_URL', 'https://christoph-lsn.github.io/MT_Site/')  # Setze die Standard-URL oder verwende die Umgebungsvariable
    output_file = 'webpage_content.txt'
    scrape_webpage(url, output_file)
    print(f'Inhalt von {url} wurde in {output_file} gespeichert.')

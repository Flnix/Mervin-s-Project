from flask import Flask, render_template, request, jsonify
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import logging
import time

app = Flask(__name__)

logging.basicConfig(filename='scraper.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')


def clean_text(text):
    return ' '.join(text.split()).strip()


def extract_content(soup):
    content = {
        'title': clean_text(soup.title.string) if soup.title else '',
        'metadata': {
            'description': soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else '',
            'keywords': soup.find('meta', attrs={'name': 'keywords'})['content'] if soup.find('meta', attrs={'name': 'keywords'}) else ''
        },
        'headings': {
            'h1': [clean_text(h1.text) for h1 in soup.find_all('h1')],
            'h2': [clean_text(h2.text) for h2 in soup.find_all('h2')],
            'h3': [clean_text(h3.text) for h3 in soup.find_all('h3')],
        },
        'paragraphs': [clean_text(p.text) for p in soup.find_all('p')],
    }
    return content


async def scrape_url(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            html_content = await response.text()
            soup = BeautifulSoup(html_content, 'lxml') 
            return extract_content(soup)
    except Exception as e:  
        logging.error(f"Error scraping {url}: {e}")  
        return None


async def scrape_multiple_urls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_url(session, url) for url in urls]
        return await asyncio.gather(*tasks)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    urls = request.form.getlist('urls') 
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    scraped_data = loop.run_until_complete(scrape_multiple_urls(urls))

    valid_data = [data for data in scraped_data if data is not None]
    
    if valid_data:
        timestamp = int(time.time())
        output_file = f'scraped_data_{timestamp}.json'
        with open(output_file, 'w') as outfile:
            json.dump(valid_data, outfile, indent=4)

        return render_template('results.html', data=valid_data)
    else:
        return jsonify({"message": "No valid data scraped", "data": []}), 400



if __name__ == '__main__':
    app.run(debug=True)

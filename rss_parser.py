import feedparser
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import hashlib
import logging
from playwright.sync_api import sync_playwright
import urllib.parse
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Настройки
rss_urls = [
    "http://feeds.venturebeat.com/VentureBeat",
    "https://www.producthunt.com/feed"
]
output_dir = "_posts"
assets_dir = "_assets"  # Директория для хранения ресурсов (CSS, изображения и т.д.)
start_date = datetime.strptime("2025-03-01", "%Y-%m-%d")  # Дата начала парсинга
existing_urls = set()

# Создание директорий
logging.info("Создание директории для постов и ресурсов...")
os.makedirs(output_dir, exist_ok=True)
os.makedirs(assets_dir, exist_ok=True)

# Загрузка существующих статей для проверки дубликатов
logging.info("Проверка существующих статей...")
for filename in os.listdir(output_dir):
    with open(os.path.join(output_dir, filename), 'r') as f:
        content = f.read()
        if "url:" in content:
            existing_urls.add(content.split("url:")[1].split("\n")[0].strip())

# Функция для скачивания ресурсов
def download_resource(url, base_url, asset_type, title_hash):
    try:
        # Если URL относительный, преобразуем его в абсолютный
        if not url.startswith(('http://', 'https://')):
            url = urllib.parse.urljoin(base_url, url)
        
        # Получаем имя файла из URL
        filename = re.sub(r'[^a-zA-Z0-9\.\-]', '_', urllib.parse.urlparse(url).path.split('/')[-1])
        if not filename:
            filename = f"{asset_type}_{hashlib.md5(url.encode()).hexdigest()[:8]}.{asset_type}"
        
        # Добавляем хэш заголовка, чтобы избежать конфликтов имен
        filename = f"{title_hash}_{filename}"
        filepath = os.path.join(assets_dir, filename)
        
        # Скачиваем ресурс
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            logging.info(f"Скачан ресурс: {url} -> {filepath}")
            return filename
        else:
            logging.warning(f"Не удалось скачать ресурс: {url} (статус: {response.status_code})")
            return None
    except Exception as e:
        logging.error(f"Ошибка при скачивании ресурса {url}: {e}")
        return None

# Парсинг RSS с использованием Playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for rss_url in rss_urls:
        logging.info(f"Парсинг RSS-ленты: {rss_url}")
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                logging.warning(f"Лента {rss_url} пуста или недоступна")
                continue

            for entry in feed.entries:
                try:
                    pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
                except (ValueError, AttributeError) as e:
                    logging.error(f"Ошибка парсинга даты для записи {entry.get('title', 'Unknown')}: {e}")
                    pub_date = datetime.now()
                if pub_date < start_date:
                    logging.info(f"Запись {entry.get('title', 'Unknown')} слишком старая: {pub_date}")
                    continue
                
                if entry.link in existing_urls:
                    logging.info(f"Запись {entry.get('title', 'Unknown')} уже существует: {entry.link}")
                    continue
                
                # Используем Playwright для рендеринга страницы
                logging.info(f"Загрузка страницы с помощью Playwright: {entry.link}")
                try:
                    page.goto(entry.link, wait_until="domcontentloaded")
                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Извлекаем содержимое <body>
                    body_content = soup.find('body')
                    if not body_content:
                        logging.warning(f"Не удалось найти содержимое на странице: {entry.link}")
                        continue
                    
                    # Уникальный хэш для этой статьи
                    title_hash = hashlib.md5(entry.title.encode()).hexdigest()[:8]
                    
                    # Скачиваем CSS-файлы
                    for link_tag in soup.find_all('link', rel='stylesheet'):
                        css_url = link_tag.get('href')
                        if css_url:
                            filename = download_resource(css_url, entry.link, 'css', title_hash)
                            if filename:
                                # Обновляем путь в HTML
                                link_tag['href'] = f"/{assets_dir}/{filename}"
                    
                    # Скачиваем изображения
                    for img_tag in body_content.find_all('img'):
                        img_url = img_tag.get('src')
                        if img_url:
                            filename = download_resource(img_url, entry.link, 'jpg', title_hash)
                            if filename:
                                # Обновляем путь в HTML
                                img_tag['src'] = f"/{assets_dir}/{filename}"
                    
                    # Сохраняем HTML-контент
                    html_content = str(soup)
                    
                    # Уникальное имя файла
                    filename = f"{pub_date.strftime('%Y-%m-%d')}-{title_hash}.md"
                    
                    # Сохранение HTML в Markdown-файле
                    logging.info(f"Сохранение статьи: {filename}")
                    with open(os.path.join(output_dir, filename), 'w') as f:
                        f.write(f"---\nlayout: post\ntitle: {entry.title}\nurl: {entry.link}\ndate: {pub_date}\n---\n{html_content}")
                    
                    existing_urls.add(entry.link)
                except Exception as e:
                    logging.error(f"Ошибка загрузки страницы {entry.link}: {e}")
                    continue
        except Exception as e:
            logging.error(f"Ошибка при парсинге ленты {rss_url}: {e}")
            continue

    browser.close()

logging.info("Парсинг завершен")

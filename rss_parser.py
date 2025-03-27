import feedparser
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import hashlib
import logging
from playwright.sync_api import sync_playwright

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Настройки
rss_urls = [
    "http://feeds.venturebeat.com/VentureBeat",
    "https://www.producthunt.com/feed"
]
output_dir = "_posts"
start_date = datetime.strptime("2025-03-01", "%Y-%m-%d")  # Изменили дату начала парсинга
existing_urls = set()

# Создание директории
logging.info("Создание директории для постов...")
os.makedirs(output_dir, exist_ok=True)

# Загрузка существующих статей для проверки дубликатов
logging.info("Проверка существующих статей...")
for filename in os.listdir(output_dir):
    with open(os.path.join(output_dir, filename), 'r') as f:
        content = f.read()
        if "url:" in content:
            existing_urls.add(content.split("url:")[1].split("\n")[0].strip())

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
                    
                    # Сохраняем HTML-контент напрямую
                    html_content = str(body_content)
                    
                    # Уникальное имя файла
                    title_hash = hashlib.md5(entry.title.encode()).hexdigest()[:8]
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

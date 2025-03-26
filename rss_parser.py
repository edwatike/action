import feedparser
import requests
from bs4 import BeautifulSoup
import html2text
import os
from datetime import datetime
import hashlib
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Настройки Selenium
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Настройки
rss_urls = [
    "http://feeds.venturebeat.com/VentureBeat",
    "https://www.producthunt.com/feed"
]
output_dir = "_posts"
start_date = datetime.strptime("2024-01-01", "%Y-%m-%d")
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

# Парсинг RSS
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
            
            # Используем Selenium для рендеринга страницы
            logging.info(f"Загрузка страницы с помощью Selenium: {entry.link}")
            try:
                driver.get(entry.link)
                content = driver.page_source
                soup = BeautifulSoup(content, 'html.parser')
                
                # Полное копирование контента
                content = soup.find('body')
                if not content:
                    logging.warning(f"Не удалось найти содержимое на странице: {entry.link}")
                    continue
                
                # Конвертация в Markdown
                h = html2text.HTML2Text()
                h.ignore_images = False
                markdown_content = h.handle(str(content))
                
                # Уникальное имя файла
                title_hash = hashlib.md5(entry.title.encode()).hexdigest()[:8]
                filename = f"{pub_date.strftime('%Y-%m-%d')}-{title_hash}.md"
                
                # Сохранение Markdown
                logging.info(f"Сохранение статьи: {filename}")
                with open(os.path.join(output_dir, filename), 'w') as f:
                    f.write(f"---\ntitle: {entry.title}\nurl: {entry.link}\ndate: {pub_date}\n---\n{markdown_content}")
                
                existing_urls.add(entry.link)
            except Exception as e:
                logging.error(f"Ошибка загрузки страницы {entry.link}: {e}")
                continue
    except Exception as e:
        logging.error(f"Ошибка при парсинге ленты {rss_url}: {e}")
        continue

driver.quit()
logging.info("Парсинг завершен")

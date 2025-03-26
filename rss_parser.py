import feedparser
import requests
from bs4 import BeautifulSoup
import html2text
import os
from datetime import datetime
import hashlib

# Настройки
rss_urls = [
    "http://feeds.venturebeat.com/VentureBeat",
    "https://www.producthunt.com/feed"
]
output_dir = "_posts"
start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")  # Укажи дату начала
existing_urls = set()

# Создание директории
os.makedirs(output_dir, exist_ok=True)

# Загрузка существующих статей для проверки дубликатов
for filename in os.listdir(output_dir):
    with open(os.path.join(output_dir, filename), 'r') as f:
        content = f.read()
        if "url:" in content:
            existing_urls.add(content.split("url:")[1].split("\n")[0].strip())

# Парсинг RSS
for rss_url in rss_urls:
    feed = feedparser.parse(rss_url)
    for entry in feed.entries:
        # Проверка даты публикации
        try:
            pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
        except (ValueError, AttributeError):
            pub_date = datetime.now()  # Если дата не парсится, используем текущую
        if pub_date < start_date:
            continue
        
        # Проверка дубликатов
        if entry.link in existing_urls:
            continue
        
        # Переход по ссылке
        try:
            response = requests.get(entry.link, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Полное копирование контента
            content = soup.find('body')  # Берем весь body
            if not content:
                continue
            
            # Конвертация в Markdown
            h = html2text.HTML2Text()
            h.ignore_images = False  # Включаем изображения как ссылки
            markdown_content = h.handle(str(content))
            
            # Уникальное имя файла
            title_hash = hashlib.md5(entry.title.encode()).hexdigest()[:8]
            filename = f"{pub_date.strftime('%Y-%m-%d')}-{title_hash}.md"
            
            # Сохранение Markdown
            with open(os.path.join(output_dir, filename), 'w') as f:
                f.write(f"---\ntitle: {entry.title}\nurl: {entry.link}\ndate: {pub_date}\n---\n{markdown_content}")
            
            # Добавляем URL в список существующих
            existing_urls.add(entry.link)
        except requests.RequestException:
            continue  # Пропускаем ошибки загрузки

# Пуш в GitHub (выполняется GitHub Actions)

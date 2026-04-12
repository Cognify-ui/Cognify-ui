#!/usr/bin/env python3
import json
import requests
from datetime import datetime
import hashlib
import feedparser
import re
import os
import time

NEWS_FILE = "news.json"
MAX_ARTICLES = 50

# Проверенные рабочие RSS-источники
RSS_SOURCES = [
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
    "https://venturebeat.com/category/ai/feed/",
    "https://towardsdatascience.com/feed/tagged/ai"
]

def clean_html(text):
    """Удаляет HTML теги"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_summary_from_title(title):
    """Генерирует краткое содержание из заголовка"""
    if not title:
        return "Новость из мира искусственного интеллекта"
    return f"{title}. Подробнее в источнике."

def generate_content_from_title(title, source):
    """Генерирует контент из заголовка, если он пустой"""
    if not title:
        return "Читайте подробности по ссылке."
    return f"{title}. Полная статья доступна на {source}. Следите за новостями мира AI на Cognify AI."

def fetch_rss(url):
    """Получает новости из RSS с повторными попытками"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Добавляем User-Agent, чтобы не блокировали
            feedparser.USER_AGENT = "Mozilla/5.0 (compatible; CognifyBot/1.0)"
            feed = feedparser.parse(url)
            
            # Проверяем на ошибки парсинга
            if feed.bozo:
                print(f"   ⚠️ Предупреждение парсинга: {feed.bozo_exception}")
            
            if not feed.entries:
                print(f"   ⚠️ Нет записей в {url}")
                return []
            
            articles = []
            for entry in feed.entries[:5]:
                # Генерируем ID из ссылки
                link = entry.get('link', '')
                if not link:
                    continue
                    
                article_id = hashlib.md5(link.encode()).hexdigest()[:12]
                
                title = clean_html(entry.get('title', ''))
                if not title:
                    title = "AI Новость"
                
                # Пробуем получить summary
                summary = clean_html(entry.get('summary', ''))
                if not summary:
                    summary = clean_html(entry.get('description', ''))
                
                # Пробуем получить content
                content = ""
                if entry.get('content'):
                    content = clean_html(entry['content'][0].get('value', ''))
                if not content and summary:
                    content = summary
                
                # Если всё пустое - генерируем
                if not summary:
                    summary = generate_summary_from_title(title)
                if not content:
                    content = generate_content_from_title(title, feed.feed.get('title', 'Unknown'))
                
                # Форматируем дату
                pub_date = entry.get('published', entry.get('updated', datetime.now().isoformat()))
                
                articles.append({
                    "id": article_id,
                    "title": title[:100],
                    "summary": summary[:300],
                    "content": content[:1500],
                    "link": link,
                    "published": pub_date,
                    "source": feed.feed.get('title', url.split('/')[2])
                })
            
            return articles
            
        except Exception as e:
            print(f"   ❌ Ошибка (попытка {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return []

def update_news_json(new_articles):
    """Обновляет файл новостей"""
    existing = {"last_updated": "", "articles": []}
    
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass
    
    existing_ids = {a.get('id') for a in existing.get('articles', [])}
    
    new_count = 0
    for article in new_articles:
        if article['id'] in existing_ids:
            continue
        
        formatted = {
            "id": article['id'],
            "title": article['title'],
            "summary": article['summary'],
            "content": article['content'],
            "source": article.get('source', 'AI News'),
            "source_url": article.get('link', ''),
            "published_at": article.get('published', datetime.now().isoformat()),
            "tags": generate_tags(article['title'])
        }
        
        existing['articles'].insert(0, formatted)
        new_count += 1
    
    # Ограничиваем количество и сортируем по дате
    existing['articles'] = existing['articles'][:MAX_ARTICLES]
    existing['last_updated'] = datetime.now().isoformat()
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    return new_count

def generate_tags(title):
    """Генерирует теги из заголовка"""
    title_lower = title.lower()
    tags = []
    
    keywords = {
        'groq': 'groq', 'cerebras': 'cerebras', 'gemini': 'gemini',
        'google': 'google', 'openai': 'openai', 'chatgpt': 'chatgpt',
        'gpt': 'gpt', 'claude': 'claude', 'meta': 'meta', 
        'llama': 'llama', 'mistral': 'mistral', 'ai': 'ai',
        'ml': 'ml', 'robot': 'роботы', 'нейросеть': 'нейросети'
    }
    
    for key, tag in keywords.items():
        if key in title_lower:
            tags.append(tag)
    
    return tags[:4] if tags else ['ai', 'news']

def main():
    print(f"🚀 Запуск: {datetime.now()}")
    print(f"📡 Источников: {len(RSS_SOURCES)}")
    print("-" * 40)
    
    all_articles = []
    
    for url in RSS_SOURCES:
        source_name = url.split('/')[2]
        print(f"📥 Парсинг: {source_name}...")
        articles = fetch_rss(url)
        print(f"   ✅ {len(articles)} новостей")
        all_articles.extend(articles)
        time.sleep(1)  # Пауза между запросами
    
    # Удаляем дубликаты по ссылке
    unique = []
    seen_links = set()
    for a in all_articles:
        if a['link'] not in seen_links:
            seen_links.add(a['link'])
            unique.append(a)
    
    print(f"📊 Уникальных: {len(unique)}")
    
    if unique:
        new_count = update_news_json(unique)
        print(f"✨ Добавлено новых: {new_count}")
        print(f"📄 Всего в файле: {len(json.load(open(NEWS_FILE))['articles'])}")
    else:
        print("⚠️ Не найдено новых статей")
        # Создаём пустой файл, если его нет
        if not os.path.exists(NEWS_FILE):
            with open(NEWS_FILE, 'w', encoding='utf-8') as f:
                json.dump({"last_updated": datetime.now().isoformat(), "articles": []}, f)
    
    print("✅ Готово!")

if __name__ == "__main__":
    main()

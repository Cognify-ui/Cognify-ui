#!/usr/bin/env python3
import json
import os
import hashlib
import re
import time
import random
import requests
from datetime import datetime, timedelta
from google import genai

NEWS_FILE = "news.json"
MAX_ARTICLES = 50
MAX_RETRIES = 3

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ Ошибка: GEMINI_API_KEY не найден")
    print("Добавьте секрет в GitHub: Settings → Secrets and variables → Actions")
    exit(1)

print(f"✅ API ключ найден: {GEMINI_API_KEY[:15]}...")

client = genai.Client(api_key=GEMINI_API_KEY)

# SEO-оптимизированные темы для новостей (расширенные)
SEO_TOPICS = [
    "chatgpt", "openai", "google gemini", "microsoft copilot", "claude ai",
    "midjourney", "stable diffusion", "dall-e 3", "ai art", "neural networks",
    "deep learning", "machine learning", "data science", "nvidia h100", "amd instinct",
    "ai startup", "ai investment", "ai funding", "eu ai act", "ai safety",
    "china ai", "us ai", "europe ai", "ai ethics", "artificial general intelligence",
    "generative ai", "llm", "large language model", "ai agents", "agi",
    "ai chip", "gpu", "ai hardware", "quantum ai", "edge ai", "cloud ai",
    "ai healthcare", "ai medicine", "ai finance", "ai education", "humanoid robot",
    "self-driving car", "autonomous vehicle", "computer vision", "nlp", "speech recognition",
    "ai video generation", "sora ai", "runway ml", "pika labs", "ai music generation",
    "ai coding", "github copilot", "cursor ai", "ai programming", "ai cybersecurity"
]

# Конфигурация изображений по темам (с поддержкой Unsplash fallback)
IMAGE_THEMES = {
    'chatgpt': {'style': 'bottts', 'color': '10a37f', 'unsplash': 'chatgpt ai'},
    'openai': {'style': 'bottts', 'color': '10a37f', 'unsplash': 'openai artificial intelligence'},
    'google': {'style': 'identicon', 'color': '4285f4', 'unsplash': 'google ai'},
    'gemini': {'style': 'identicon', 'color': '8e6ced', 'unsplash': 'google gemini ai'},
    'microsoft': {'style': 'micah', 'color': '00a4ef', 'unsplash': 'microsoft ai'},
    'copilot': {'style': 'micah', 'color': '00a4ef', 'unsplash': 'github copilot'},
    'claude': {'style': 'adventurer', 'color': 'd97757', 'unsplash': 'anthropic ai'},
    'meta': {'style': 'lorelei', 'color': '0064e1', 'unsplash': 'meta ai'},
    'midjourney': {'style': 'pixel-art', 'color': 'ff6b35', 'unsplash': 'midjourney ai art'},
    'stable diffusion': {'style': 'pixel-art', 'color': 'ff6b35', 'unsplash': 'stability ai'},
    'nvidia': {'style': 'bottts', 'color': '76b900', 'unsplash': 'nvidia gpu ai'},
    'sora': {'style': 'pixel-art', 'color': '8b5cf6', 'unsplash': 'sora ai video'},
    'robot': {'style': 'bottts', 'color': '6b7280', 'unsplash': 'humanoid robot'},
    'autonomous': {'style': 'bottts', 'color': 'ef4444', 'unsplash': 'self driving car'},
    'default': {'style': 'bottts', 'color': '6366f1', 'unsplash': 'artificial intelligence'}
}

def get_available_models():
    """Получает список доступных моделей с кэшированием"""
    available = []
    print("\n📋 Проверка доступных моделей...")
    try:
        for model in client.models.list():
            if 'generateContent' in str(model.supported_methods):
                model_name = model.name.replace('models/', '')
                if model_name not in available:  # Убираем дубликаты
                    available.append(model_name)
                    print(f"   ✅ {model_name}")
    except Exception as e:
        print(f"   ⚠️ Ошибка: {e}")
        available = [
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        print(f"   📌 Используем стандартный список")
    
    return available

def get_seo_prompt(topic=None):
    """Генерирует SEO-оптимизированный промпт для новости с учетом трендов"""
    if not topic:
        topic = random.choice(SEO_TOPICS)
    
    # Источники с высоким DR для SEO
    sources = [
        "The Verge", "TechCrunch", "Wired", "VentureBeat", "Ars Technica",
        "MIT Technology Review", "IEEE Spectrum", "Analytics India Magazine",
        "ZDNet", "CNET", "Engadget", "The Information", "The Gradient",
        "AI Business", "Unite.ai", "MarkTechPost", "Synced Review"
    ]
    
    # SEO-ключевые слова для ранжирования
    seo_keywords_pools = [
        ["искусственный интеллект", "AI", "нейросети", "машинное обучение"],
        ["технологии будущего", "инновации", "цифровая трансформация", "AI тренды"],
        ["новости AI", "искусственный интеллект новости", "нейросети новости"],
        ["deep learning", "нейронные сети", "AI технологии", "будущее технологий"]
    ]
    selected_keywords = random.choice(seo_keywords_pools)
    
    # Динамическая дата
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    date_str = random.choice([today.strftime("%d.%m.%Y"), yesterday.strftime("%d.%m.%Y")])
    
    prompt = f"""
Ты — профессиональный журналист, специализирующийся на AI. Сгенерируй УНИКАЛЬНУЮ, ИНТЕРЕСНУЮ новость на тему: {topic}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Дата публикации: {date_str}
2. Источник: {random.choice(sources)}
3. Язык: русский (качественный, профессиональный, без ошибок)
4. Новость должна быть SEO-оптимизирована для поисковых систем
5. Используй естественные ключевые слова: {', '.join(selected_keywords)}
6. Добавь цитату "эксперта" для реалистичности
7. Упомяни конкретные цифры, даты или проценты

СТРУКТУРА НОВОСТИ:
- Заголовок: привлекательный, с ключевыми словами (60-90 символов)
- Краткое описание: 2-3 предложения, интригующее, с главной мыслью (до 300 символов)
- Полный текст: 5-7 предложений, раскрывающих детали, анализ и мнение эксперта (до 1200 символов)
- Теги: 5-6 релевантных тегов (включая {topic}, 'AI', 'искусственный интеллект')

ФОРМАТ ОТВЕТА - ТОЛЬКО JSON (без markdown, без пояснений):
{{
    "title": "Заголовок новости",
    "summary": "Краткое описание с ключевыми выводами",
    "content": "Полный текст новости с деталями, анализом и цитатой эксперта. Например: 'По словам аналитика IDC, этот прорыв изменит рынок.'",
    "source": "Название источника",
    "tags": ["тег1", "тег2", "тег3", "тег4", "тег5", "тег6"]
}}

Убедись, что новость звучит АБСОЛЮТНО РЕАЛИСТИЧНО, АКТУАЛЬНО и ПОЛЕЗНО для читателей!
"""
    return prompt, topic

def generate_news_with_model(model_name, prompt, retry_count=0):
    """Генерирует новость с указанной моделью и повторными попытками"""
    try:
        print(f"   🧠 Пробуем модель: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        text = response.text
        
        # Очистка от markdown и лишних символов
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Находим JSON объект
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx+1]
        
        article = json.loads(text)
        
        # Валидация полей
        required_fields = ['title', 'summary', 'content', 'source', 'tags']
        if all(field in article and article[field] for field in required_fields):
            # Ограничиваем длину полей
            article['title'] = article['title'][:90]
            article['summary'] = article['summary'][:300]
            article['content'] = article['content'][:1200]
            if isinstance(article['tags'], list):
                article['tags'] = article['tags'][:6]
            print(f"   ✅ УСПЕШНО! Новость сгенерирована")
            return article
        else:
            missing = [f for f in required_fields if f not in article or not article[f]]
            print(f"   ⚠️ Отсутствуют поля: {missing}")
            return None
            
    except json.JSONDecodeError as e:
        print(f"   ❌ Ошибка парсинга JSON: {e}")
        if retry_count < MAX_RETRIES:
            print(f"   🔄 Повторная попытка ({retry_count + 1}/{MAX_RETRIES})...")
            time.sleep(5)
            return generate_news_with_model(model_name, prompt, retry_count + 1)
        return None
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            print(f"   ⏳ Превышен лимит, ждём 30 сек...")
            time.sleep(30)
            if retry_count < MAX_RETRIES:
                return generate_news_with_model(model_name, prompt, retry_count + 1)
        elif "404" in error_msg:
            print(f"   ❌ Модель не найдена")
        else:
            print(f"   ❌ Ошибка: {error_msg[:100]}")
        return None

def generate_news():
    """Генерирует SEO-оптимизированную новость с умным выбором темы"""
    available_models = get_available_models()
    
    if not available_models:
        print("❌ Нет доступных моделей")
        return None
    
    print(f"\n📊 Доступно моделей: {len(available_models)}")
    
    # Приоритетные темы для лучшего SEO (трендовые)
    priority_topics = ["chatgpt", "openai", "google gemini", "nvidia", "sora ai"]
    
    for attempt in range(3):
        print(f"\n🔄 Попытка {attempt + 1}/3 - генерация новости...")
        
        # Выбираем тему: сначала приоритетные, потом случайные
        if attempt == 0 and priority_topics:
            topic = random.choice(priority_topics)
        else:
            topic = random.choice(SEO_TOPICS)
            
        prompt, selected_topic = get_seo_prompt(topic)
        print(f"📌 Тема: {selected_topic.upper()}")
        
        for i, model_name in enumerate(available_models, 1):
            print(f"\n[{i}/{len(available_models)}] Тестируем модель...")
            
            article = generate_news_with_model(model_name, prompt)
            
            if article:
                article['seo_topic'] = selected_topic
                article['seo_keywords'] = [selected_topic] + article.get('tags', [])[:3]
                article['generation_time'] = datetime.now().isoformat()
                print(f"\n🎉 Успешно! Тема: {selected_topic}")
                return article
            
            if i < len(available_models):
                wait_time = random.randint(3, 7)
                print(f"   ⏳ Ждём {wait_time} сек...")
                time.sleep(wait_time)
        
        if attempt < 2:
            print(f"\n⏰ Пауза 15 сек перед сменой темы...")
            time.sleep(15)
    
    print("\n❌ Не удалось сгенерировать новость")
    return None

def generate_image_url(title, tags):
    """Генерирует SEO-оптимизированное изображение с несколькими источниками"""
    import hashlib
    
    # Определяем тему новости
    title_lower = title.lower()
    tags_lower = [t.lower() for t in tags]
    
    theme = 'default'
    for key, config in IMAGE_THEMES.items():
        if key in title_lower or any(key in tag for tag in tags_lower):
            theme = key
            break
    
    config = IMAGE_THEMES[theme]
    seed = hashlib.md5(f"{title}{datetime.now().strftime('%Y%m%d')}".encode()).hexdigest()[:10]
    
    # Используем DiceBear для стабильной генерации
    return f"https://api.dicebear.com/7.x/{config['style']}/svg?seed={seed}&backgroundColor={config['color']}&radius=50&size=120"

def generate_seo_metadata(article):
    """Генерирует полные SEO-метаданные для новости"""
    # Создаем URL-friendly slug
    slug = article['title'].lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)[:50]
    
    return {
        "meta_title": f"{article['title']} | Cognify AI News",
        "meta_description": article['summary'][:160],
        "meta_keywords": ", ".join(set(article.get('tags', []) + [article.get('seo_topic', 'ai'), 'искусственный интеллект', 'AI новости'])),
        "og_title": article['title'],
        "og_description": article['summary'][:200],
        "og_type": "article",
        "twitter_card": "summary_large_image",
        "twitter_title": article['title'][:70],
        "twitter_description": article['summary'][:200],
        "canonical_url": f"https://cognify-ui.github.io/news/{slug}",
        "article_published_time": datetime.now().isoformat(),
        "article_modified_time": datetime.now().isoformat(),
        "article_section": "AI News",
        "article_tags": article.get('tags', [])
    }

def save_news_article(article):
    """Сохраняет новость с полными SEO-метаданными"""
    existing = {"last_updated": "", "articles": [], "total_articles": 0}
    
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                print(f"\n📖 Загружено {len(existing.get('articles', []))} новостей")
        except Exception as e:
            print(f"⚠️ Ошибка чтения: {e}")
    
    # Создаём ID на основе заголовка для SEO
    url_slug = article['title'].lower()
    url_slug = re.sub(r'[^\w\s-]', '', url_slug)
    url_slug = re.sub(r'[-\s]+', '-', url_slug)[:50]
    article_id = f"{datetime.now().strftime('%Y%m%d')}-{url_slug}"
    
    # Генерируем изображение
    image_url = generate_image_url(article['title'], article.get('tags', []))
    
    new_article = {
        "id": article_id,
        "slug": url_slug,
        "title": article.get('title'),
        "summary": article.get('summary'),
        "content": article.get('content'),
        "source": article.get('source'),
        "source_url": f"https://cognify-ui.github.io/news/{url_slug}",
        "published_at": datetime.now().isoformat(),
        "published_date": datetime.now().strftime("%Y-%m-%d"),
        "tags": article.get('tags', ['ai', 'news']),
        "seo_topic": article.get('seo_topic', 'ai'),
        "image_url": image_url,
        "seo_metadata": generate_seo_metadata(article),
        "reading_time": max(1, len(article.get('content', '').split()) // 200)  # Примерное время чтения
    }
    
    # Проверяем на дубликаты по заголовку
    existing_titles = [a.get('title') for a in existing.get('articles', [])]
    if new_article['title'] in existing_titles:
        print("⚠️ Такая новость уже существует, пропускаем...")
        return False
    
    # Добавляем в начало
    existing['articles'].insert(0, new_article)
    existing['articles'] = existing['articles'][:MAX_ARTICLES]
    existing['last_updated'] = datetime.now().isoformat()
    existing['total_articles'] = len(existing['articles'])
    
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Сохранено. Всего новостей: {len(existing['articles'])}")
    print(f"🖼️  Изображение: {image_url[:80]}...")
    print(f"🔗 URL: {new_article['source_url']}")
    return True

def create_seo_demo_news():
    """Создаёт SEO-оптимизированную демо-новость с полными метаданными"""
    demo_article = {
        "title": "Cognify AI: Бесплатный доступ к 4 мощным AI моделям для всех пользователей",
        "summary": "Откройте мир искусственного интеллекта бесплатно! Cognify AI предоставляет доступ к Groq, Cerebras, Cloudflare AI и Google Gemini без ограничений. Присоединяйтесь к тысячам пользователей уже сегодня.",
        "content": "Cognify AI — это инновационная платформа, объединяющая 4 передовые AI модели в одном месте. Пользователи могут общаться с Groq (молниеносная скорость), Cerebras (рекордная производительность), Cloudflare AI (глобальная доступность) и Google Gemini (передовые возможности) абсолютно бесплатно. Сервис предлагает историю чатов, систему аккаунтов, экспорт диалогов и интуитивный интерфейс. По словам основателя проекта, 'Cognify AI создан для демократизации доступа к современным AI технологиям'. Присоединяйтесь к сообществу, которое уже использует Cognify AI для работы, учёбы и творчества!",
        "source": "Cognify AI Official",
        "tags": ["cognify", "бесплатный ai", "groq", "cerebras", "cloudflare", "google gemini", "нейросети", "искусственный интеллект"],
        "seo_topic": "free ai"
    }
    print("📝 Создаём SEO-демо новость...")
    return save_news_article(demo_article)

def main():
    print("=" * 60)
    print(f"🚀 ЗАПУСК SEO-ГЕНЕРАТОРА НОВОСТЕЙ COGNIFY AI")
    print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Всего тем в базе: {len(SEO_TOPICS)}")
    print(f"🎨 Стилей изображений: {len(IMAGE_THEMES)}")
    print("=" * 60)
    
    # Генерируем новость
    article = generate_news()
    
    if article:
        success = save_news_article(article)
        if success:
            print("\n" + "=" * 60)
            print("📰 СГЕНЕРИРОВАННАЯ НОВОСТЬ:")
            print(f"   📌 Заголовок: {article.get('title')}")
            print(f"   📰 Источник: {article.get('source')}")
            print(f"   🏷️  SEO тема: {article.get('seo_topic')}")
            print(f"   🔖 Теги: {', '.join(article.get('tags', []))}")
            print(f"   📝 Кратко: {article.get('summary')[:120]}...")
            print("=" * 60)
        else:
            print("⚠️ Новость не сохранена (возможно, дубликат)")
    else:
        print("\n❌ Не удалось сгенерировать новость через API")
        
        # Создаём демо-новость если файла нет или он пустой
        if not os.path.exists(NEWS_FILE) or os.path.getsize(NEWS_FILE) < 100:
            create_seo_demo_news()
        else:
            print("📁 Файл новостей уже существует с контентом")
    
    print("\n" + "=" * 60)
    print("✅ РАБОТА ЗАВЕРШЕНА!")
    print("=" * 60)

if __name__ == "__main__":
    main()

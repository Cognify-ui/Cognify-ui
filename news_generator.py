#!/usr/bin/env python3
import json
import os
import hashlib
import re
import time
import random
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

# Фиксированный список моделей для генерации
FIXED_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
]

# SEO-оптимизированные темы для новостей
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

# Конфигурация изображений по темам
IMAGE_THEMES = {
    'chatgpt': {'style': 'bottts', 'color': '10a37f'},
    'openai': {'style': 'bottts', 'color': '10a37f'},
    'google': {'style': 'identicon', 'color': '4285f4'},
    'gemini': {'style': 'identicon', 'color': '8e6ced'},
    'microsoft': {'style': 'micah', 'color': '00a4ef'},
    'copilot': {'style': 'micah', 'color': '00a4ef'},
    'claude': {'style': 'adventurer', 'color': 'd97757'},
    'meta': {'style': 'lorelei', 'color': '0064e1'},
    'midjourney': {'style': 'pixel-art', 'color': 'ff6b35'},
    'stable diffusion': {'style': 'pixel-art', 'color': 'ff6b35'},
    'nvidia': {'style': 'bottts', 'color': '76b900'},
    'robot': {'style': 'bottts', 'color': '6b7280'},
    'autonomous': {'style': 'bottts', 'color': 'ef4444'},
    'default': {'style': 'bottts', 'color': '6366f1'}
}

def get_available_models():
    """Возвращает фиксированный список моделей для генерации"""
    print("\n📋 Загружаем список моделей для генерации...")
    
    # Проверяем доступность моделей через API
    available_models = []
    api_models = []
    
    try:
        # Пытаемся получить список моделей из API
        for model in client.models.list():
            if 'generateContent' in str(model.supported_methods):
                model_name = model.name.replace('models/', '')
                api_models.append(model_name)
        
        print(f"   📡 Найдено моделей в API: {len(api_models)}")
        
        # Проверяем каждую модель из фиксированного списка
        for model in FIXED_MODELS:
            if model in api_models:
                available_models.append(model)
                print(f"   ✅ {model} - доступна")
            else:
                print(f"   ⚠️ {model} - не найдена в API, пропускаем")
        
        # Если ни одна модель не доступна, используем первые 3 из API
        if not available_models and api_models:
            available_models = api_models[:3]
            print(f"   📌 Используем первые 3 доступные модели: {available_models}")
            
    except Exception as e:
        print(f"   ⚠️ Ошибка проверки API: {e}")
        # Используем фиксированный список как есть
        available_models = FIXED_MODELS.copy()
        print(f"   📌 Используем фиксированный список из {len(available_models)} моделей")
    
    print(f"\n📊 Итоговый список для генерации ({len(available_models)} моделей):")
    for i, model in enumerate(available_models, 1):
        print(f"   {i}. {model}")
    
    return available_models

def get_seo_prompt(topic=None):
    """Генерирует SEO-оптимизированный промпт для новости"""
    if not topic:
        topic = random.choice(SEO_TOPICS)
    
    sources = [
        "The Verge", "TechCrunch", "Wired", "VentureBeat", "Ars Technica",
        "MIT Technology Review", "IEEE Spectrum", "Analytics India Magazine",
        "ZDNet", "CNET", "Engadget", "The Information"
    ]
    
    seo_keywords = [
        "искусственный интеллект", "AI", "нейросети", "машинное обучение",
        "технологии будущего", "инновации", "цифровая трансформация"
    ]
    
    prompt = f"""
Ты — профессиональный журналист, специализирующийся на AI. Сгенерируй УНИКАЛЬНУЮ, ИНТЕРЕСНУЮ новость на тему: {topic}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Дата публикации: сегодня или вчера
2. Источник: {random.choice(sources)}
3. Язык: русский (качественный, профессиональный)
4. Новость должна быть SEO-оптимизирована для поисковых систем
5. Используй естественные ключевые слова: {', '.join(random.sample(seo_keywords, 3))}

СТРУКТУРА НОВОСТИ:
- Заголовок: привлекательный, с ключевыми словами (до 90 символов)
- Краткое описание: 2-3 предложения, интригующее (до 300 символов)
- Полный текст: 4-6 предложений, раскрывающих детали (до 1200 символов)
- Теги: 4-5 релевантных тега (включая {topic} и 'AI')

ФОРМАТ ОТВЕТА - ТОЛЬКО JSON:
{{
    "title": "Заголовок новости",
    "summary": "Краткое описание",
    "content": "Полный текст новости с деталями",
    "source": "Название источника",
    "tags": ["тег1", "тег2", "тег3", "тег4", "тег5"]
}}

Убедись, что новость звучит АБСОЛЮТНО РЕАЛИСТИЧНО и АКТУАЛЬНО!
"""
    return prompt, topic

def generate_news_with_model(model_name, prompt, retry_count=0):
    """Генерирует новость с указанной моделью"""
    try:
        print(f"   🧠 Пробуем модель: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        
        text = response.text
        # Очистка от markdown
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Находим JSON
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx+1]
        
        article = json.loads(text)
        
        # Валидация
        required_fields = ['title', 'summary', 'content', 'source', 'tags']
        if all(field in article for field in required_fields):
            print(f"   ✅ УСПЕШНО! Новость сгенерирована моделью {model_name}")
            return article
        else:
            print(f"   ⚠️ Не все поля заполнены")
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
            print(f"   ❌ Модель {model_name} не найдена")
        else:
            print(f"   ❌ Ошибка: {error_msg[:100]}")
        return None

def generate_news():
    """Генерирует новость, перебирая все модели из списка"""
    available_models = get_available_models()
    
    if not available_models:
        print("❌ Нет доступных моделей")
        return None
    
    print(f"\n🔄 Начинаем перебор {len(available_models)} моделей...")
    print("=" * 60)
    
    # Пробуем разные темы для лучшего SEO
    for attempt in range(3):
        print(f"\n🎯 Попытка {attempt + 1}/3 - выбор темы...")
        
        # Выбираем тему
        topic = random.choice(SEO_TOPICS)
        prompt, selected_topic = get_seo_prompt(topic)
        print(f"📌 Тема: {selected_topic.upper()}")
        
        # Перебираем все модели
        for i, model_name in enumerate(available_models, 1):
            print(f"\n[{i}/{len(available_models)}] Тестируем модель {model_name}...")
            
            article = generate_news_with_model(model_name, prompt)
            
            if article:
                article['seo_topic'] = selected_topic
                article['used_model'] = model_name
                article['generation_time'] = datetime.now().isoformat()
                print(f"\n🎉 Успех! Новость сгенерирована моделью {model_name}")
                print(f"📰 Тема: {selected_topic}")
                return article
            
            # Задержка между моделями
            if i < len(available_models):
                wait_time = random.randint(3, 7)
                print(f"   ⏳ Ждём {wait_time} сек перед следующей моделью...")
                time.sleep(wait_time)
        
        if attempt < 2:
            print(f"\n⏰ Пауза 20 сек перед сменой темы...")
            time.sleep(20)
    
    print("\n❌ Не удалось сгенерировать новость ни одной моделью")
    return None

def generate_image_url(title, tags):
    """Генерирует изображение под тему новости"""
    import hashlib
    
    title_lower = title.lower()
    tags_lower = [t.lower() for t in tags]
    
    theme = 'default'
    for key, config in IMAGE_THEMES.items():
        if key in title_lower or any(key in tag for tag in tags_lower):
            theme = key
            break
    
    config = IMAGE_THEMES[theme]
    seed = hashlib.md5(f"{title}{datetime.now().strftime('%Y%m%d')}".encode()).hexdigest()[:10]
    
    return f"https://api.dicebear.com/7.x/{config['style']}/svg?seed={seed}&backgroundColor={config['color']}&radius=50"

def generate_seo_metadata(article):
    """Генерирует SEO-метаданные"""
    return {
        "meta_title": f"{article['title']} | Cognify AI News",
        "meta_description": article['summary'][:160],
        "meta_keywords": ", ".join(article.get('tags', []) + [article.get('seo_topic', 'ai')]),
        "og_title": article['title'],
        "og_description": article['summary'][:200],
        "twitter_card": "summary_large_image"
    }

def save_news_article(article):
    """Сохраняет новость"""
    existing = {"last_updated": "", "articles": []}
    
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                print(f"\n📖 Загружено {len(existing.get('articles', []))} новостей")
        except Exception as e:
            print(f"⚠️ Ошибка чтения: {e}")
    
    # Создаём ID
    article_id = hashlib.md5(f"{article['title']}{datetime.now()}".encode()).hexdigest()[:12]
    
    # Генерируем изображение
    image_url = generate_image_url(article['title'], article.get('tags', []))
    
    new_article = {
        "id": article_id,
        "title": article.get('title'),
        "summary": article.get('summary'),
        "content": article.get('content'),
        "source": article.get('source'),
        "source_url": f"https://cognify-ui.github.io/news/{article_id}",
        "published_at": datetime.now().isoformat(),
        "tags": article.get('tags', ['ai', 'news']),
        "seo_topic": article.get('seo_topic', 'ai'),
        "used_model": article.get('used_model', 'unknown'),
        "image_url": image_url,
        "seo_metadata": generate_seo_metadata(article)
    }
    
    # Проверка на дубликат
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
    print(f"🤖 Модель: {article.get('used_model', 'unknown')}")
    return True

def create_seo_demo_news():
    """Создаёт демо-новость"""
    demo_article = {
        "title": "Cognify AI: Бесплатный доступ к 4 мощным AI моделям",
        "summary": "Откройте мир искусственного интеллекта бесплатно! Cognify AI предоставляет доступ к Groq, Cerebras, Cloudflare AI и Google Gemini без ограничений.",
        "content": "Cognify AI — это инновационная платформа, объединяющая 4 передовые AI модели. Пользователи могут общаться с Groq, Cerebras, Cloudflare AI и Google Gemini абсолютно бесплатно. Сервис предлагает историю чатов, систему аккаунтов и интуитивный интерфейс.",
        "source": "Cognify AI",
        "tags": ["cognify", "бесплатный ai", "groq", "cerebras", "gemini"],
        "seo_topic": "free ai",
        "used_model": "demo"
    }
    print("📝 Создаём демо-новость...")
    return save_news_article(demo_article)

def main():
    print("=" * 60)
    print(f"🚀 ЗАПУСК ГЕНЕРАТОРА НОВОСТЕЙ")
    print(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Моделей в очереди: {len(FIXED_MODELS)}")
    print(f"🎨 SEO тем: {len(SEO_TOPICS)}")
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
            print(f"   🤖 Модель: {article.get('used_model')}")
            print(f"   🔖 Теги: {', '.join(article.get('tags', []))}")
            print("=" * 60)
        else:
            print("⚠️ Новость не сохранена (дубликат)")
    else:
        print("\n❌ Не удалось сгенерировать новость")
        
        if not os.path.exists(NEWS_FILE) or os.path.getsize(NEWS_FILE) < 100:
            create_seo_demo_news()
    
    print("\n" + "=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)

if __name__ == "__main__":
    main()

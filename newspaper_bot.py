import os
import requests
import time
import json
import feedparser
from time import mktime
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from google import genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MY_CHAT_ID = os.environ["MY_CHAT_ID"]

# ID вашего Google Документа для черновика
DOC_ID = "13tQCDrY7eW1q0kUggi-1wVXpm8Phh8HxuKwu6GREsd8"

CHANNELS = [
    "zzakatov", "darya_dinosaur_fm", "improv_nv", "dudyukajulia", "improvizekb", 
    "imtakproshche", "sidishkaaa", "svetkakrevetkaaa", "klimchudickyea", "trenazh", 
    "maly6kina", "improvplus", "proseccoshow", "iclairs_improv", "kmp_impro", "paraimprovfraz",
    "shamina_sharit", "improvinsight", "golce06", "improvstudioru", "ImprovBuro", "isk_gus",
    "ImprovLifeblog", "teriviki", "Geksliy", "NastyaNeiro2", "tochkabest", "improvauthors",
    "o_pereverzeva", "improv_paly4", "improvru", "sabrageimprov", "moscowimprovclub", 
    "improvmoscow", "romkaShn", "improv_light", "ada_legna", "improstore", "improculture",
    "improvrostovsidorova", "byvshieshow", "olyaisolyais", "gdscrpt", "moresprava", 
    "ammasters", "lgv_prod", "notscripted", "zigatu1", "drozhizhizhi", "improschoolspb", 
    "manezhclub", "playingtomyself", "domisly", "BRIF_improv", "v40th", "boondockscamp", 
    "improfi_school", "playbackrostov", "improv56", "nikitamenshoff", "Ni_odnogo_D", 
    "a_pligin", "improlab_kzn", "breaking_it", "dreamuchaya_pyatnica", "etoetiteam", 
    "improvlady", "tayaiilyaimprov", "oitheatre", "theatre_13", "sandboxlv", "ostrovimpro",
    "chaoticimprov", "improvteams", "sireneviy_toomuch", "alexmikerov", "zvezdyvlyzhah", 
    "Hoodnews", "improcomunity", "damy_improv", "izbrannye_impro", "akeytou", "carpetstorage",
    "nazhivuyu", "podplie", "showimpro", "impro_Vasa", "poilo_improvband", "improvboris", 
    "improtips", "sevenmetres", "brezglivaya_lubov", "obnyalaimpro", "burnyashnyash", 
    "kicakotli", "netolkoimpro", "Alkaimprov", "azartimprov", "alkomixer", "zhivye_impr", 
    "improvarctic", "impride_spb", "jam_students", "danetnavernoe_improv", "smehotochka", 
    "neujeliatut", "igristyyyee", "improcomfangroup", "rightnow_show", "elina_pro_improv", 
    "razrivnie_Mos_kow", "fouretazhka", "tugezaimprov", "pckcimprov", "neseryosnie", "ligaimprova"
]

RSS_FEEDS = [
    "https://connectedcomedy.com/feed/",
    "https://improveverywhere.com/feed/",
    "https://willhines.substack.com/feed",
    "https://alloutcomedytheater.com/annas-improv-blog?format=rss",
    "https://jimmycarrane.com/feed",
    "https://nationalcomedy.com/feed",
    "https://shinythingscomedy.com/improv-blog?format=rss",
    "https://feeds.libsyn.com/112269/rss",
    "https://ucbcomedy.com/feed",
    "https://improvmoscow.ru/feed"
]

def update_google_doc(html_content):
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        print("Ошибка: Секрет GOOGLE_CREDENTIALS не задан.")
        return
    
    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=credentials)
    
    # Сохраняем HTML во временный файл для загрузки
    file_path = "draft.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # Указываем mimetype text/html, чтобы Google Drive сам перевел разметку в формат Google Docs
    media = MediaFileUpload(file_path, mimetype='text/html')
    
    try:
        service.files().update(fileId=DOC_ID, media_body=media).execute()
        print("Черновик в Google Док успешно обновлен!")
    except Exception as e:
        print(f"Ошибка при обновлении Google Дока: {e}")

def fetch_reddit_posts():
    print("Сбор топовых тредов с r/improv...")
    reddit_url = "https://www.reddit.com/r/improv/top.json?limit=5&t=week"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }
    reddit_texts = []
    
    try:
        response = requests.get(reddit_url, headers=headers)
        if response.status_code == 200:
            posts = response.json().get('data', {}).get('children', [])
            for post in posts:
                data = post.get('data', {})
                title = data.get('title', '')
                text = data.get('selftext', '')
                if title:
                    short_text = text[:1500] + "..." if len(text) > 1500 else text
                    reddit_texts.append(f"[Reddit]: Заголовок: {title}\nТекст: {short_text}")
            print(f"Найдено тредов на Reddit: {len(reddit_texts)}")
        else:
            print(f"Ошибка Reddit: код ответа {response.status_code}")
    except Exception as e:
        print(f"Ошибка при сборе Reddit: {e}")
        
    return "\n\n---\n\n".join(reddit_texts)

def fetch_rss_posts():
    print("Сбор свежих статей из RSS-блогов...")
    collected_texts = []
    now_utc = datetime.now(timezone.utc)
    yesterday = now_utc - timedelta(hours=24)

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            count = 0
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed), timezone.utc)
                    if dt >= yesterday:
                        title = entry.title if hasattr(entry, 'title') else 'Без заголовка'
                        summary = entry.summary if hasattr(entry, 'summary') else ''
                        soup = BeautifulSoup(summary, 'html.parser')
                        text = soup.get_text(separator=' ', strip=True)[:1000]
                        collected_texts.append(f"[RSS Блог]: Заголовок: {title}\nТекст: {text}...")
                        count += 1
            print(f"[{feed_url}] Найдено свежих статей: {count}")
        except Exception as e:
            print(f"[{feed_url}] Ошибка парсинга: {e}")
            
    return "\n\n---\n\n".join(collected_texts)

def fetch_channel_posts():
    collected_texts = []
    now_utc = datetime.now(timezone.utc)
    yesterday = now_utc - timedelta(hours=24)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    channels_iterable = CHANNELS.items() if isinstance(CHANNELS, dict) else [("Общие новости", CHANNELS)]
    
    for city, channel_list in channels_iterable:
        for channel in channel_list:
            try:
                url = f"https://t.me/s/{channel}"
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    messages = soup.find_all('div', class_='tgme_widget_message')
                    
                    if not messages:
                        print(f"[{channel}] Телеграм заблокировал доступ.")
                    else:
                        count = 0
                        for msg in messages:
                            time_tag = msg.select_one('.tgme_widget_message_date time') or msg.find('time')
                            if time_tag and time_tag.has_attr('datetime'):
                                post_date = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                                
                                if post_date >= yesterday:
                                    text_div = msg.find('div', class_='tgme_widget_message_text')
                                    text = text_div.get_text(separator=' ', strip=True) if text_div else ""
                                    
                                    img_url = ""
                                    photo_wrap = msg.find('a', class_='tgme_widget_message_photo_wrap')
                                    if photo_wrap and 'style' in photo_wrap.attrs:
                                        style_text = photo_wrap['style']
                                        if "background-image:url('" in style_text:
                                            img_url = style_text.split("background-image:url('")[1].split("')")[0]
                                    
                                    if len(text) > 30 or img_url:
                                        post_content = text
                                        if img_url:
                                            post_content += f"\n[Фото: {img_url}]"
                                            
                                        collected_texts.append(f"[Город: {city} | Канал: {channel}]: {post_content}")
                                        count += 1
                        print(f"[{channel}] Свежих постов за 24ч: {count}")
            except Exception as e:
                print(f"[{channel}] Ошибка скрипта: {e}")
            
            time.sleep(2)
            
    print(f"Всего собрано текстов из Telegram: {len(collected_texts)}")
    return "\n\n---\n\n".join(collected_texts)

def generate_draft_html(tg_news, reddit_news, rss_news):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Ты — ИИ-редактор. Твоя задача — собрать и структурировать сырой материал для утренней газеты об импровизации.
    Этот текст будет загружен в Google Docs для финальной человеческой редактуры.
    
    Новости из Telegram:
    {tg_news}
    
    Тренды с Reddit:
    {reddit_news}
    
    Статьи из блогов (RSS):
    {rss_news}
    
    Требования к форматированию:
    Используй простую HTML-разметку (h1, h2, h3, p, ul, li). Не используй теги <style>, <head>, <body> — только чистый контент.
    Если в тексте есть пометка [Фото: URL_ССЫЛКА], обязательно вставь картинку с помощью <img src="URL_ССЫЛКА" width="300">.
    
    Рубрики:
    1. Главные события (Анонсы курсов, шоу, фестивали). Группируй по городам.
    2. Биржа джемов (Открытые микрофоны).
    3. Уголок теоретика. Переведи на русский и адаптируй тренды с Reddit и статьи из RSS-блогов.
    4. Дневники сцены. Личные впечатления комиков, эмоции и инсайты.
    5. Шутки дня и разгоны. Неформальные диалоги, панчи, сплетни.
    6. Новости комьюнити и Разное. Все остальные посты и микро-анонсы.
    
    Стиль:
    Сохраняй максимум фактуры и исходных цитат. Не удаляй контент, если он не является откровенным спамом.
    Верни только готовый HTML-код.
    """
    
    chat = client.chats.create(model="gemini-3.6-flash")
    
    for attempt in range(15):
        try:
            response = chat.send_message(prompt)
            return response.text.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            if "503" in str(e) and attempt < 14:
                print(f"Сервер перегружен. Ожидание 60 сек (попытка {attempt + 1} из 15)...")
                time.sleep(60)
            else:
                raise e

def send_notification_to_telegram():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    text = f"📰 Утренний черновик собран и загружен в Google Docs!\n\nМожно приступать к редактуре:\nhttps://docs.google.com/document/d/{DOC_ID}/edit"
    requests.post(url, data={"chat_id": MY_CHAT_ID, "text": text})

def main():
    tg_news = fetch_channel_posts()
    reddit_news = fetch_reddit_posts()
    rss_news = fetch_rss_posts()
    
    if tg_news.strip() != "---" or reddit_news.strip() != "---" or rss_news.strip() != "---":
        print("Генерация черновика через Gemini...")
        draft_html = generate_draft_html(tg_news, reddit_news, rss_news)
        print("Загрузка черновика в Google Docs...")
        update_google_doc(draft_html)
        print("Отправка уведомления в Telegram...")
        send_notification_to_telegram()
    else:
        print("Внимание: За последние 24 часа не найдено ни одного подходящего поста в источниках.")

if __name__ == "__main__":
    main()

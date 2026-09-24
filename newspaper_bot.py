import os
import requests
import time
import json
import feedparser
import random
import calendar
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from google import genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from weasyprint import HTML
LOCAL_TZ = timezone(timedelta(hours=5))

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MY_CHAT_ID = os.environ["MY_CHAT_ID"]

DOC_ID = "13tQCDrY7eW1q0kUggi-1wVXpm8Phh8HxuKwu6GREsd8"
PDF_FOLDER_ID = "1enu9CNlCXxGMojV6lbtjobHWWrhg8q_c"

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

def get_drive_service():
    """Помощник для авторизации в Google Drive"""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        return None
    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials)
    
def check_if_built_today():
    """Проверяет дату последнего изменения PDF-файла на Google Диске."""
    service = get_drive_service()
    if not service:
        return False
        
    query = f"'{PDF_FOLDER_ID}' in parents and name = 'newspaper.pdf' and trashed = false"
    try:
        response = service.files().list(q=query, spaces='drive', fields='files(id, modifiedTime)').execute()
        files = response.get('files', [])
        
        if files:
            modified_time_str = files[0].get('modifiedTime')
            if modified_time_str:
                modified_date = datetime.fromisoformat(modified_time_str.replace('Z', '+00:00')).date()
                today = datetime.now(timezone.utc).date()
                if modified_date == today:
                    return True
    except Exception as e:
        print(f"Ошибка при проверке даты файла: {e}", flush=True)
        
    return False

def update_google_doc(html_content):
    service = get_drive_service()
    if not service:
        return
        
    file_path = "draft.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    media = MediaFileUpload(file_path, mimetype='text/html')
    try:
        service.files().update(fileId=DOC_ID, media_body=media).execute()
        print("Черновик в Google Док успешно обновлен!", flush=True)
    except Exception as e:
        print(f"Ошибка при обновлении Google Дока: {e}", flush=True)

def upload_pdf_to_drive(pdf_path):
    service = get_drive_service()
    if not service:
        return
        
    query = f"'{PDF_FOLDER_ID}' in parents and name = 'newspaper.pdf' and trashed = false"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = response.get('files', [])
    media = MediaFileUpload(pdf_path, mimetype='application/pdf')
    try:
        if files:
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {'name': 'newspaper.pdf', 'parents': [PDF_FOLDER_ID]}
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            service.permissions().create(fileId=file.get('id'), body={'role': 'reader', 'type': 'anyone'}).execute()
        print("PDF успешно загружен на Google Диск!", flush=True)
    except Exception as e:
        print(f"Ошибка при загрузке PDF на Google Диск: {e}", flush=True)

def send_pdf_to_telegram(pdf_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    caption = f"📰 Утренняя газета готова!\n\nРедактировать черновик:\nhttps://docs.google.com/document/d/{DOC_ID}/edit"
    with open(pdf_path, "rb") as doc:
        requests.post(url, data={"chat_id": MY_CHAT_ID, "caption": caption}, files={"document": doc}, timeout=60)

def fetch_reddit_posts():
    reddit_url = "https://www.reddit.com/r/improv/top.json?limit=5&t=week"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ImprovNewspaperBot/1.0"}
    reddit_texts = []
    try:
        response = requests.get(reddit_url, headers=headers, timeout=30)
        if response.status_code == 200:
            for post in response.json().get('data', {}).get('children', []):
                title, text = post.get('data', {}).get('title', ''), post.get('data', {}).get('selftext', '')
                if title:
                    reddit_texts.append(f"[Reddit]: {title}\n{text[:1000]}...")
    except: pass
    return "\n\n".join(reddit_texts)

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

def generate_section_html(raw_news, section_title, layout_html):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    Ты — ИИ-редактор. Твоя задача — собрать ОДНУ рубрику для газеты об импровизации.
    
    Все новости за день:
    {raw_news}
    
    Твоя задача:
    1. Найди в новостях информацию, которая подходит для рубрики "{section_title}".
    2. КРИТИЧНОЕ УСЛОВИЕ: Если подходящих новостей для этой рубрики НЕТ, верни только одно слово: NO_CONTENT.
    3. Если новости есть, сверстай их строго по HTML-шаблону ниже.
    
    ШАБЛОН ВЕРСТКИ:
    <div style="margin-bottom: 40px;">
        <h2 style="font-family: 'Times New Roman', Georgia, serif; font-size: 26px; text-transform: uppercase; border-bottom: 1px solid #000; padding-bottom: 5px; margin-bottom: 20px;">{section_title}</h2>
        {layout_html}
    </div>
    
    ПРАВИЛА ОФОРМЛЕНИЯ:
    - НЕ МЕНЯЙ теги таблиц.
    - ЗАПРЕЩЕНО использовать списки <ul> и <li>. Используй <p> для абзацев.
    - Если у новости ЕСТЬ фото, удали блок <div ...>[Место для графитного скетча...]</div> и вставь фото. Если фото НЕТ — удали текст [ВСТАВЬ_ФОТО_СЮДА_ИЛИ_ОСТАВЬ_DIV_НИЖЕ], но сам серый <div> обязательно оставь.
    - Замени все плейсхолдеры [ТЕКСТ_СЮДА] на реальные развернутые новости.
    
    Верни ТОЛЬКО готовый HTML-код. Без маркдауна.
    """
    
    for attempt in range(10):
        try:
            # Создаем чистый чат с нуля на КАЖДУЮ попытку. 
            # Это обнуляет память и спасает лимиты при переотправке.
            chat = client.chats.create(model="gemini-3.6-flash")
            response = chat.send_message(prompt)
            
            return response.text.replace("```html", "").replace("```", "").strip()
        except Exception as e:
            if "429" in str(e) or "503" in str(e):
                print(f"      [!] API перегружен. Ждем 65 секунд (Попытка {attempt+1}/10)...", flush=True)
                time.sleep(65)
            else:
                raise e
                
    return "NO_CONTENT"
    

def build_full_newspaper(tg_news, reddit_news, rss_news):
    raw_news = f"Телеграм:\n{tg_news}\n\nReddit:\n{reddit_news}\n\nБлоги:\n{rss_news}"
    
    MAX_CHARS = 40000 
    if len(raw_news) > MAX_CHARS:
        raw_news = raw_news[:MAX_CHARS] + "\n\n[ОСТАЛЬНЫЕ НОВОСТИ ОБРЕЗАНЫ ДЛЯ ЭКОНОМИИ ЛИМИТОВ API]"
        print(f"[!] Слишком много новостей. Текст обрезан до {MAX_CHARS} символов.", flush=True)
    
    layout_classic_title = """
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border: none; background-color: #ffffff;">
        <tr>
            <td colspan="3" style="border: none; padding-bottom: 20px; vertical-align: top;">
                [ВСТАВИТЬ_ГЛАВНОЕ_ФОТО_ЕСЛИ_ЕСТЬ]
                <h3 style="font-size: 24px; margin: 20px 0 10px 0; font-weight: normal; font-family: 'Times New Roman', Georgia, serif;">[ГЛАВНЫЙ_ЗАГОЛОВОК_НОВОСТИ]</h3>
                <p style="font-size: 16px; line-height: 1.6;">[РАЗВЕРНУТЫЙ_ТЕКСТ_ГЛАВНОЙ_НОВОСТИ]</p>
            </td>
        </tr>
        <tr>
            <td width="33%" style="border: none; vertical-align: top; padding-right: 15px;">
                <p style="font-size: 14px; line-height: 1.5;">[ДОП_НОВОСТЬ_1]</p>
            </td>
            <td width="33%" style="border: none; vertical-align: top; padding: 0 15px; border-left: 1px solid #ddd; border-right: 1px solid #ddd;">
                <p style="font-size: 14px; line-height: 1.5;">[ДОП_НОВОСТЬ_2]</p>
            </td>
            <td width="34%" style="border: none; vertical-align: top; padding-left: 15px;">
                <p style="font-size: 14px; line-height: 1.5;">[ДОП_НОВОСТЬ_3]</p>
            </td>
        </tr>
    </table>
    """
    
    
    layout_rhythmic_digest = """
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border: none; background-color: #ffffff;">
        <tr>
            <td width="33%" style="vertical-align: top; padding-right: 15px; border-right: 1px solid #ccc; border-bottom: 1px solid #ccc; padding-bottom: 15px; border-top: none; border-left: none;">
                [ФОТО_1_ЕСЛИ_ЕСТЬ]
                <p style="font-size: 14px; margin-top: 10px;">[КОРОТКАЯ_НОВОСТЬ_ИЛИ_АНОНС_1]</p>
            </td>
            <td width="33%" style="vertical-align: top; padding: 0 15px; border-right: 1px solid #ccc; border-bottom: 1px solid #ccc; padding-bottom: 15px; border-top: none; border-left: none;">
                <p style="font-size: 14px;">[КОРОТКАЯ_НОВОСТЬ_ИЛИ_АНОНС_2]</p>
            </td>
            <td width="34%" style="vertical-align: top; padding-left: 15px; border-bottom: 1px solid #ccc; padding-bottom: 15px; border-top: none; border-right: none; border-left: none;">
                [ФОТО_3_ЕСЛИ_ЕСТЬ]
                <p style="font-size: 14px; margin-top: 10px;">[КОРОТКАЯ_НОВОСТЬ_ИЛИ_АНОНС_3]</p>
            </td>
        </tr>
        <tr>
            <td width="33%" style="vertical-align: top; padding-right: 15px; padding-top: 15px; border-right: 1px solid #ccc; border-top: none; border-bottom: none; border-left: none;">
                <p style="font-size: 14px;">[КОРОТКАЯ_НОВОСТЬ_ИЛИ_АНОНС_4]</p>
            </td>
            <td width="67%" colspan="2" style="vertical-align: top; padding-left: 15px; padding-top: 15px; border: none;">
                <h3 style="font-size: 20px; margin-top: 0; font-weight: normal; font-family: 'Times New Roman', Georgia, serif;">[АКЦЕНТНЫЙ_ЗАГОЛОВОК_ВЫДЕЛЯЮЩЕЙСЯ_НОВОСТИ]</h3>
                <p style="font-size: 15px; line-height: 1.5;">[ТЕКСТ_ВЫДЕЛЯЮЩЕЙСЯ_НОВОСТИ]</p>
            </td>
        </tr>
    </table>
    """
    
    layout_visual_dominant = """
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border: none; background-color: #ffffff;">
        <tr>
            <td width="40%" style="vertical-align: top; padding-right: 20px; border: none;">
                <h3 style="font-size: 22px; margin-top: 0; font-style: italic; font-family: 'Times New Roman', Georgia, serif;">[ВВОДНЫЙ_ТЕЗИС_ИЛИ_КРУПНАЯ_МЫСЛЬ]</h3>
                <p style="font-size: 15px; line-height: 1.6;">[ТЕКСТ_АНАЛИТИКИ_ЧАСТЬ_1]</p>
                <p style="font-size: 15px; line-height: 1.6;">[ТЕКСТ_АНАЛИТИКИ_ЧАСТЬ_2]</p>
            </td>
            <td width="60%" style="vertical-align: top; border: none;">
                [ВСТАВЬ_ФОТО_СЮДА_ИЛИ_ОСТАВЬ_DIV_НИЖЕ]
                <div style="background-color: #f9f9f9; width: 100%; height: 250px; display: flex; align-items: center; justify-content: center; font-style: italic; color: #888; border: 1px dashed #ccc;">[Место для графитного скетча / Иллюстрации сцены]</div>
                <p style="font-size: 14px; line-height: 1.6; margin-top: 15px; padding-left: 15px; border-left: 2px solid #333;">[ОСНОВНОЙ_ВЫВОД_ИЛИ_КОНЦОВКА_СТАТЬИ]</p>
            </td>
        </tr>
    </table>
    """

    layout_asymmetric_portrait = """
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border: none; background-color: #ffffff;">
        <tr>
            <td width="65%" style="vertical-align: top; padding-right: 25px; border: none;">
                <p style="font-size: 16px; line-height: 1.7; margin-top: 0;">[ДЛИННАЯ_ИСТОРИЯ_ИЛИ_ИСПОВЕДЬ_АБЗАЦ_1]</p>
                <p style="font-size: 16px; line-height: 1.7;">[ДЛИННАЯ_ИСТОРИЯ_ИЛИ_ИСПОВЕДЬ_АБЗАЦ_2]</p>
            </td>
            <td width="35%" style="vertical-align: top; border: none;">
                <div style="background-color: #f9f9f9; width: 100%; height: 180px; display: flex; align-items: center; justify-content: center; font-style: italic; color: #888; border: 1px dashed #ccc;">[Портрет / Фото сцены]</div>
                <p style="font-size: 13px; font-style: italic; margin-top: 10px; text-align: right; color: #555;">[ПОДПИСЬ_К_ФОТО_ИЛИ_ЦИТАТА]</p>
                <div style="margin-top: 20px; padding: 15px; background-color: #f4f4f4; font-family: 'Times New Roman', Georgia, serif;">
                    <p style="font-size: 15px; margin: 0; font-weight: bold;">[ВРЕЗКА_ИЛИ_ДОПОЛНИТЕЛЬНАЯ_МЫСЛЬ]</p>
                </div>
            </td>
        </tr>
    </table>
    """

    layout_contrast = """
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border: none; background-color: #ffffff;">
        <tr>
            <td width="40%" style="vertical-align: top; background-color: #1a1a1a; color: #ffffff; padding: 25px; border: none;">
                <h3 style="color: #ffffff; font-size: 24px; margin-top: 0; font-style: italic; font-family: 'Times New Roman', Georgia, serif;">[ГЛАВНАЯ_ЦИТАТА_ШУТКА_ИЛИ_МЕМ]</h3>
                <p style="font-size: 15px; line-height: 1.6; color: #eeeeee;">[ПОЯСНЕНИЕ_ИЛИ_РАЗГОН_ШУТКИ]</p>
            </td>
            <td width="60%" style="vertical-align: top; padding-left: 25px; border: none;">
                [ФОТО_ЕСЛИ_ЕСТЬ]
                <h3 style="font-size: 20px; margin-top: 15px; font-weight: normal; font-family: 'Times New Roman', Georgia, serif;">[ДРУГАЯ_ШУТКА_ИЛИ_ЗАГОЛОВОК]</h3>
                <p style="font-size: 15px; line-height: 1.6;">[ТЕКСТ_ВТОРОЙ_ШУТКИ_ИЛИ_СПЛЕТНИ]</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 15px 0;">
                <p style="font-size: 14px; color: #444;">[КОРОТКИЙ_ПАНЧЛАЙН_ИЛИ_ФАКТ]</p>
            </td>
        </tr>
    </table>
    """

    issue_plan = [
        {"title": "Радар импровизатора", "layout": layout_classic_title},
        {"title": "Кузница кадров", "layout": layout_rhythmic_digest},
        {"title": "Анализ и механики", "layout": layout_visual_dominant},
        {"title": "Исповедь из-за кулис", "layout": layout_asymmetric_portrait},
        {"title": "Цех абсурда", "layout": layout_contrast},
        {"title": "Что по сплетням?", "layout": layout_rhythmic_digest}
    ]
    
    final_html_parts = []
    
    for section in issue_plan:
        print(f"Генерация рубрики: {section['title']}...", flush=True)
        try:
            section_html = generate_section_html(raw_news, section['title'], section['layout'])
            if section_html and "NO_CONTENT" not in section_html:
                final_html_parts.append(section_html)
                print(f"-> Успешно сгенерировано.", flush=True)
            else:
                print(f"-> Пропуск. Нет информации.", flush=True)
                
        except Exception as e:
            print(f"-> ОШИБКА генерации. Пропускаем. Причина: {e}", flush=True)
            continue
            
        time.sleep(10)
    
    if not final_html_parts:
        return None
        
    combined_content = "\n".join(final_html_parts)
    
    final_document = f"""
    <div style="font-family: 'Times New Roman', Georgia, serif; color: #111; background-color: #ffffff;">
        <div style="text-align: center; margin-bottom: 50px; border-bottom: 3px solid #111; padding-bottom: 20px;">
            <h1 style="font-family: 'Times New Roman', Georgia, serif; font-size: 52px; margin: 0; text-transform: uppercase; letter-spacing: 3px; font-weight: normal;">Газета</h1>
            <p style="font-size: 14px; margin: 10px 0 0 0; font-style: italic; text-transform: uppercase; letter-spacing: 1px; font-family: 'Times New Roman', Georgia, serif;">Утренний выпуск • Выжимка самого важного</p>
        </div>
        {combined_content}
    </div>
    """
    return final_document

def main():
    if check_if_built_today():
        print("Газета уже была успешно собрана сегодня. Завершаю работу.", flush=True)
        return
    print("Парсинг источников...", flush=True)
    tg_news = fetch_channel_posts()
    reddit_news = fetch_reddit_posts()
    rss_news = fetch_rss_posts()
    
    if tg_news.strip() or reddit_news.strip() or rss_news.strip():
        print("Запуск модульного конвейера Gemini...", flush=True)
        draft_html = build_full_newspaper(tg_news, reddit_news, rss_news)
        
        if draft_html:
            print("Создание PDF-версии...", flush=True)
            pdf_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{ size: A4; margin: 15mm; }}
                    body {{ background-color: #ffffff; line-height: 1.5; }}
                    img {{ max-width: 100%; height: auto; }}
                    table {{ page-break-inside: avoid; }}
                </style>
            </head>
            <body>
                {draft_html}
            </body>
            </html>
            """
            pdf_path = "newspaper.pdf"
            HTML(string=pdf_html).write_pdf(pdf_path)
            
            print("Загрузка черновика в Google Docs...", flush=True)
            update_google_doc(draft_html)
            
            print("Загрузка PDF на Google Диск...", flush=True)
            upload_pdf_to_drive(pdf_path)
            
            print("Отправка PDF в Telegram...", flush=True)
            send_pdf_to_telegram(pdf_path)
            print("Успешно завершено!", flush=True)
        else:
            print("Газета не собрана: во всех рубриках сработал NO_CONTENT.", flush=True)
    else:
        print("Внимание: За последние 24 часа не найдено ни одного нового поста.", flush=True)

if __name__ == "__main__":
    main()

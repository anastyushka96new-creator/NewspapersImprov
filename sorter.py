import os
import time
import requests
from bs4 import BeautifulSoup
from google import genai
import csv

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MY_CHAT_ID = os.environ["MY_CHAT_ID"]

# Сюда вставьте ваш гигантский список всех каналов подряд
RAW_CHANNELS = [
    "improv_channel_1", 
    "another_improviser_channel",
    # ... сотни ваших каналов ...
]

def analyze_channel_city(channel_name, client):
    try:
        url = f"https://t.me/s/{channel_name}"
        response = requests.get(url)
        if response.status_code != 200:
            return "Ошибка доступа"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Собираем описание канала и пару последних постов для контекста
        description = soup.find('div', class_='tgme_channel_info_description')
        desc_text = description.get_text(separator=' ', strip=True) if description else ""
        
        posts = soup.find_all('div', class_='tgme_widget_message_text', limit=3)
        posts_text = " ".join([p.get_text(separator=' ', strip=True) for p in posts])
        
        context = f"Описание канала: {desc_text}\nПоследние посты: {posts_text}"
        
        prompt = f"""
        Проанализируй текст из канала импровизаторов. 
        Твоя задача: определить, к какому городу относится этот канал.
        Верни ТОЛЬКО название города на русском языке (например: Москва, Санкт-Петербург, Казань).
        Если город определить абсолютно невозможно, верни строго фразу "Общие новости".
        Текст: {context}
        """
        
        chat = client.chats.create(model="gemini-3.6-flash")
        response = chat.send_message(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Ошибка с {channel_name}: {e}")
        return "Ошибка"

def main():
    client = genai.Client(api_key=GEMINI_API_KEY)
    results = []
    
    print("Начинаю анализ каналов...")
    for i, channel in enumerate(RAW_CHANNELS):
        print(f"Анализ {channel} ({i+1}/{len(RAW_CHANNELS)})...")
        city = analyze_channel_city(channel, client)
        results.append({"Канал": channel, "Город": city})
        time.sleep(2) # Небольшая пауза, чтобы не спамить запросами
        
    # Сохраняем в CSV
    csv_filename = "channels_sorted.csv"
    with open(csv_filename, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Канал", "Город"])
        writer.writeheader()
        writer.writerows(results)
        
    # Отправляем готовую таблицу в Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(csv_filename, "rb") as doc:
        requests.post(url, data={"chat_id": MY_CHAT_ID, "caption": "🗂 Ваша таблица с городами готова!"}, files={"document": doc})

if __name__ == "__main__":
    main()

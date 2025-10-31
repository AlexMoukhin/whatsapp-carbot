from fastapi import FastAPI, Request
import requests, os, json

app = FastAPI()

# 🔐 Токен, который ты указал в Meta (Verify Token)
VERIFY_TOKEN = "carbot123"


# ✅ Проверка webhook при подключении (GET)
@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return {"error": "Invalid token"}


# 🟢 Проверка доступности сервера
@app.get("/")
def root():
    return {"status": "ok"}


# 💬 Основной обработчик сообщений WhatsApp → GPT → WhatsApp
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    print("📩 Входящее сообщение:", json.dumps(data, indent=2, ensure_ascii=False))

    # Безопасный парсинг входящих сообщений
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        text = message.get("text", {}).get("body", "")
        phone = message["from"]

        # ⚙️ Форматируем телефон под требования WhatsApp Sandbox
        # Удаляем все нецифровые символы
        phone = ''.join(filter(str.isdigit, phone))

        # Если хочешь зафиксировать номер вручную (для Sandbox), раскомментируй:
        # phone = "79258608489"

        print(f"👤 От пользователя {phone}: {text}")
    except Exception as e:
        print("⚠️ Ошибка разбора входящих данных:", e)
        return {"status": "ignored"}

    # 🧠 GPT ответ
    headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "Ты консультант автосалона. Отвечай чётко и дружелюбно, пиши коротко и по существу."
            },
            {"role": "user", "content": text}
        ]
    }

    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    print("🧠 Ответ от OpenAI:", r.text)  # логируем полный ответ API
    print("📞 номер на который отправляется номер из входящего JSON:", message["from"])
    print("📋 Все входящие данные:", json.dumps(data, indent=2, ensure_ascii=False))

    if r.status_code != 200:
        print("⚠️ Ошибка OpenAI:", r.text)
        return {"status": "openai_error"}

    data = r.json()
    if "choices" not in data:
        print("⚠️ Нет поля choices в ответе:", data)
        return {"status": "openai_format_error"}

    reply = data["choices"][0]["message"]["content"]
    print("🤖 Ответ GPT:", reply)

    # 📤 Отправляем ответ пользователю в WhatsApp
    wa_url = f"https://graph.facebook.com/v20.0/{os.getenv('PHONE_ID')}/messages"
    wa_headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
        "Content-Type": "application/json"
    }
    wa_payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": reply}
    }

    resp = requests.post(wa_url, headers=wa_headers, json=wa_payload)
    print("📤 Ответ WhatsApp API:", resp.text)

    return {"status": "ok"}

from fastapi import FastAPI, Request
import requests, os

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
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        text = message.get("text", {}).get("body", "")
        phone = message["from"]
    except Exception as e:
        print("⚠️ Ошибка разбора входящих данных:", e)
        return {"status": "ignored"}

    # 🧠 GPT ответ
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Ты консультант автосалона. Отвечай чётко и дружелюбно."},
                {"role": "user", "content": text}
            ]
        },
    )
    reply = r.json()["choices"][0]["message"]["content"]

    # 📤 Ответ пользователю в WhatsApp
    requests.post(
        f"https://graph.facebook.com/v20.0/{os.getenv('PHONE_ID')}/messages",
        headers={
            "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
            "Content-Type": "application/json"
        },
        json={
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": reply}
        }
    )

    return {"status": "ok"}

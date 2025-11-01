from fastapi import FastAPI, Request
import requests, os, traceback

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

@app.get("/")
def root():
    return {"status": "ok"}

# 💬 Вебхук от Telegram
@app.post("/webhook")
async def telegram_webhook(req: Request):
    try:
        data = await req.json()
        print("📩 Incoming Telegram:", data)

        # Проверяем наличие сообщения
        if "message" not in data:
            print("⚠️ Нет поля 'message' в запросе")
            return {"status": "ignored"}

        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        if not user_text:
            print("⚠️ Пустое сообщение — ничего не отправляем в GPT")
            return {"status": "ignored"}

        print(f"👤 Пользователь {chat_id} написал: {user_text}")

        # 🧠 Запрос к OpenAI
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "Ты консультант автосалона. Отвечай коротко и по делу."},
                        {"role": "user", "content": user_text}
                    ]
                },
                timeout=20
            )

            if not r.ok:
                print(f"❌ Ошибка OpenAI: {r.status_code} {r.text}")
                reply = f"⚠️ Ошибка GPT ({r.status_code}): {r.text[:300]}"
            else:
                gpt_data = r.json()
                reply = gpt_data["choices"][0]["message"]["content"]
                print(f"🤖 GPT ответ: {reply}")

        except Exception as e:
            print("🔥 Исключение при запросе к OpenAI:", traceback.format_exc())
            reply = "⚠️ Ошибка при обращении к GPT API."

        # 📤 Ответ пользователю в Telegram
        try:
            t_resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply},
                timeout=10
            )

            if not t_resp.ok:
                print(f"❌ Ошибка Telegram API: {t_resp.status_code} {t_resp.text}")

        except Exception as e:
            print("🔥 Исключение при отправке сообщения в Telegram:", traceback.format_exc())

        return {"status": "ok"}

    except Exception as e:
        print("🚨 Общая ошибка вебхука:", traceback.format_exc())
        return {"status": "error", "details": str(e)}

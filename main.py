from fastapi import FastAPI, Request
import requests, os

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    message = data["entry"][0]["changes"][0]["value"]["messages"][0]
    text = message.get("text", {}).get("body", "")
    phone = message["from"]

    # GPT ответ
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Ты консультант автосалона."},
                {"role": "user", "content": text}
            ]
        },
    )
    reply = r.json()["choices"][0]["message"]["content"]

    # Ответ через WhatsApp API
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

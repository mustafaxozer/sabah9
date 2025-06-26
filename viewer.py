import os
import json
import asyncio
import random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetMessagesViewsRequest

# Türkiye saat dilimi
TURKIYE_ZAMANI = timezone(timedelta(hours=3))

# Config dosyasını oku
with open("config.json", "r") as f:
    config = json.load(f)

api_id = config["api_id"]
api_hash = config["api_hash"]
channels = config["channels"]
delay_min, delay_max = config["delay_range_seconds"]

ACCOUNTS_DIR = "accounts"

async def start_account_sessions():
    clients = []
    for session_file in os.listdir(ACCOUNTS_DIR):
        if not session_file.endswith(".session"):
            continue
        name = session_file.replace(".session", "")
        client = TelegramClient(os.path.join(ACCOUNTS_DIR, name), api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            print(f"[!] {name} giriş yapılmamış.")
            continue

        clients.append(client)
    return clients

async def realistic_view(client, channel_username, msg_id):
    try:
        await client(JoinChannelRequest(channel_username))
        await asyncio.sleep(random.randint(2, 5))

        await asyncio.sleep(random.randint(delay_min, delay_max))
        await client.send_read_acknowledge(channel_username, max_id=msg_id)

        channel_entity = await client.get_entity(channel_username)

        try:
            views = await client(GetMessagesViewsRequest(
                peer=channel_entity,
                id=[msg_id],
                increment=True
            ))
            print(f"[✓] {client.session.filename} mesajı görüntüledi: {views}")
        except Exception as e:
            print(f"[!] {client.session.filename} görüntüleme hatası: {e}")

    except Exception as e:
        print(f"[X] {client.session.filename} hata: {e}")

async def delayed_view(client, username, msg_id, delay):
    await asyncio.sleep(delay)
    await realistic_view(client, username, msg_id)

async def main():
    clients = await start_account_sessions()
    if not clients:
        print("Aktif hesap yok.")
        return

    for client in clients:
        @client.on(events.NewMessage(chats=channels))
        async def handler(event):
            channel = await event.get_chat()
            username = channel.username or channel.id
            msg_id = event.id

            if event.message.views is None:
                print(f"[⏭️] View bilgisi yok, mesaj atlandı: {username} / ID: {msg_id}")
                return

            print(f"[📢] Yeni görüntülenebilir mesaj: {username} / ID: {msg_id}")

            total_clients = clients[:]
            random.shuffle(total_clients)

            skip_count = random.randint(int(len(clients) * 0.05), int(len(clients) * 0.1))
            active_clients = total_clients[skip_count:]

            now = datetime.now(TURKIYE_ZAMANI)
            
            # Bir sonraki sabah 09:00-11:00 arasındaki zamanı hesapla
            target_day = now.date()
            if now.time() >= datetime.strptime("11:00", "%H:%M").time():
                target_day += timedelta(days=1)

            morning_start = datetime.combine(target_day, datetime.strptime("09:00", "%H:%M").time(), TURKIYE_ZAMANI)
            morning_end = datetime.combine(target_day, datetime.strptime("11:00", "%H:%M").time(), TURKIYE_ZAMANI)

            def random_time(start, end):
                return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

            # Tüm hesapları sabah saatlerinde görüntüleme yap
            for c in active_clients:
                view_time = random_time(morning_start, morning_end)
                delay = (view_time - now).total_seconds()
                delay = max(5, delay)  # En az 5 saniye bekle
                asyncio.create_task(delayed_view(c, username, msg_id, delay))

            print(f"[⏰] Görüntüleme zamanı: {morning_start.strftime('%d.%m.%Y %H:%M')} - {morning_end.strftime('%H:%M')}")

    print("[✅] Bot çalışıyor, yeni gönderiler dinleniyor...")
    print("[ℹ️] Tüm görüntülemeler sadece sabah 09:00-11:00 arasında yapılacak.")
    await asyncio.gather(*[client.run_until_disconnected() for client in clients])

if __name__ == "__main__":
    asyncio.run(main())

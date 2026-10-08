from telethon import TelegramClient
import socks
import asyncio
import os

# Read from the environment so the credentials never land in the repository.
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
channel = "playlist1zz"  # یوزرنیم یا لینک کانال
download_path = "music"  # مسیر ذخیره فایل‌ها
AUDIO_LIMIT = 20  # حداکثر تعداد موزیک جدید که می‌خواهی دانلود شود

os.makedirs(download_path, exist_ok=True)

# فایل برای ذخیره لیست فایل‌های دانلود شده
downloaded_list_file = os.path.join(download_path, "downloaded.txt")

# خواندن فایل‌هایی که قبلاً دانلود شده‌اند
if os.path.exists(downloaded_list_file):
    with open(downloaded_list_file, "r") as f:
        downloaded_files = set(f.read().splitlines())
else:
    downloaded_files = set()


def progress_callback(received: int, total: int):
    """Print download progress (percentage and size)."""
    if total and total > 0:
        pct = 100 * received / total
        rec_mb = received / (1024 * 1024)
        tot_mb = total / (1024 * 1024)
        print(f"\r  {pct:.1f}% ({rec_mb:.2f} / {tot_mb:.2f} MB)", end="", flush=True)
    else:
        rec_mb = received / (1024 * 1024)
        print(f"\r  {rec_mb:.2f} MB", end="", flush=True)


async def main():
    async with TelegramClient(
        "session",
        api_id,
        api_hash,
        proxy=(socks.SOCKS5, "127.0.0.1", 10808),
    ) as client:
        downloaded_count = 0

        # روی همه پیام‌ها loop می‌زنیم تا زمانی که به AUDIO_LIMIT موزیک جدید برسیم
        async for message in client.iter_messages(channel):
            if downloaded_count >= AUDIO_LIMIT:
                break

            # فقط پیام‌هایی که حاوی فایل صوتی هستند را در نظر بگیر
            media = None

            if message.audio:
                media = message.audio
            elif (
                message.document
                and getattr(message.document, "mime_type", None)
                and message.document.mime_type.startswith("audio/")
            ):
                media = message.document

            # اگر مدیا صوتی نبود (مثلاً عکس/ویدیو/فایل معمولی) پرش کن
            if not media:
                continue

            file_name = getattr(media, "file_name", None) or getattr(
                media, "name", None
            )
            if not file_name:
                file_name = f"{message.id}.ogg"

            if file_name in downloaded_files:
                print("Already downloaded:", file_name)
                continue

            print("Downloading:", file_name)
            await client.download_media(
                message, download_path, progress_callback=progress_callback
            )
            print()  # newline after progress
            downloaded_files.add(file_name)
            downloaded_count += 1

    # ذخیره لیست فایل‌های دانلود شده
    with open(downloaded_list_file, "w") as f:
        for f_name in downloaded_files:
            f.write(f_name + "\n")

    print(
        f"Done! Downloaded {len(downloaded_files)} total files,"
        f" {downloaded_count} new audio files this run."
    )


if __name__ == "__main__":
    asyncio.run(main())

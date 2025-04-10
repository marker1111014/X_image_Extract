import logging
import re
import time
import sys
import os
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 從環境變數取得 TOKEN（部署在 Railway 時要設定）
TOKEN = os.getenv("TOKEN")

def convert_to_nitter_url(twitter_url):
    match = re.match(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', twitter_url)
    if match:
        username, tweet_id = match.groups()
        return f"https://nitter.net/{username}/status/{tweet_id}"
    return twitter_url

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    service = Service(executable_path='/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("歡迎使用 X 圖片下載機器人！\n請直接發送 X 貼文連結，我會幫你提取其中的圖片。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    if not re.match(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+', message_text):
        return

    driver = None
    try:
        driver = setup_driver()
        driver.get(message_text)
        time.sleep(10)

        if "Sign in" in driver.page_source or "登入" in driver.page_source:
            nitter_url = convert_to_nitter_url(message_text)
            driver.get(nitter_url)
            time.sleep(10)

        try:
            WebDriverWait(driver, 20).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception as e:
            logging.error(f"頁面載入等待錯誤: {str(e)}")

        images = []
        try:
            media_urls = driver.execute_script("""
                const mediaElements = [];
                const images = document.querySelectorAll('img');
                images.forEach(img => {
                    if (img.src && !img.src.includes('profile_images') &&
                        !img.src.includes('logo') && !img.src.includes('avatar') &&
                        (img.src.includes('media') || img.src.includes('pbs.twimg.com'))) {
                        mediaElements.push({ type: 'image', url: img.src });
                    }
                });
                return mediaElements;
            """)
            for media in media_urls:
                url = media['url']
                if url not in images:
                    images.append(url)
        except Exception as e:
            logging.error(f"JavaScript 錯誤: {str(e)}")

        if not images:
            await update.message.reply_text("找不到圖片。")
            return

        if len(images) == 1:
            await update.message.reply_photo(images[0])
        else:
            media_group = [InputMediaPhoto(media=img) for img in images]
            await update.message.reply_media_group(media=media_group)

    except Exception as e:
        logging.error(f"處理訊息時發生錯誤: {str(e)}")
    finally:
        if driver:
            driver.quit()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

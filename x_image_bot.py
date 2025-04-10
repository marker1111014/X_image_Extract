import logging
import re
import time
import os
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.environ.get("TOKEN")  # 從 Railway 環境變數讀取

def convert_to_nitter_url(twitter_url):
    match = re.match(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', twitter_url)
    if match:
        username, tweet_id = match.groups()
        return f"https://nitter.net/{username}/status/{tweet_id}"
    return twitter_url

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    # 使用 Docker 容器內的默認路徑
    service = Service(executable_path='/usr/bin/chromedriver')
    chrome_options.binary_location = '/usr/bin/google-chrome'  # Chrome 路徑

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("歡迎使用 X 圖片下載機器人！請發送推文連結。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    if not re.match(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+', message_text):
        return

    try:
        driver = setup_driver()
        driver.get(message_text)
        time.sleep(10)

        if "Sign in" in driver.page_source or "登入" in driver.page_source:
            nitter_url = convert_to_nitter_url(message_text)
            driver.get(nitter_url)
            time.sleep(10)

        images = []
        media_elements = driver.execute_script("""
            const media = [];
            document.querySelectorAll('img').forEach(img => {
                const url = img.src || img.getAttribute('srcset')?.split(' ')[0];
                if (url && url.includes('pbs.twimg.com') && !url.includes('thumb')) {
                    media.push(url.replace('&name=small', ''));
                }
            });
            return media;
        """)
        images = list(set(media_elements))

        if not images:
            await update.message.reply_text("⚠️ 未找到圖片")
            return

        batch_size = 10
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            media_group = [InputMediaPhoto(url) for url in batch]
            try:
                await update.message.reply_media_group(media=media_group)
            except Exception as e:
                logging.error(f"群組發送失敗: {str(e)}")
                for url in batch:
                    try:
                        await update.message.reply_photo(url)
                    except:
                        continue

    except Exception as e:
        logging.error(f"錯誤: {str(e)}")
        await update.message.reply_text("❌ 處理請求時發生錯誤")
    finally:
        if driver:
            driver.quit()

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()

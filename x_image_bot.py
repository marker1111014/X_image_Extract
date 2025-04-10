import logging
import re
import time
import sys
import os
import requests
import zipfile
import io
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Telegram Bot Token
TOKEN = "7679988713:AAHIiKRJnrmLfmokRSO2rZo1eY4JZd0mHHg"

def get_chrome_version():
    """獲取 Chrome 瀏覽器版本"""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Google\Chrome\BLBeacon')
        version, _ = winreg.QueryValueEx(key, 'version')
        return version
    except Exception as e:
        logging.error(f"Error getting Chrome version: {str(e)}")
        return None

def download_chromedriver():
    """下載對應版本的 ChromeDriver"""
    try:
        # 獲取 Chrome 版本
        chrome_version = get_chrome_version()
        if not chrome_version:
            raise Exception("無法獲取 Chrome 版本")
            
        # 獲取主版本號
        major_version = chrome_version.split('.')[0]
        
        # 創建 drivers 目錄
        current_dir = os.path.dirname(os.path.abspath(__file__))
        drivers_dir = os.path.join(current_dir, 'drivers')
        os.makedirs(drivers_dir, exist_ok=True)
        
        # 下載 ChromeDriver
        url = f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{chrome_version}/win64/chromedriver-win64.zip"
        logging.info(f"正在下載 ChromeDriver {chrome_version}...")
        
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"下載失敗，HTTP 狀態碼: {response.status_code}")
            
        # 解壓縮
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            zip_file.extractall(drivers_dir)
            
        # 移動文件到正確位置
        chromedriver_path = os.path.join(drivers_dir, 'chromedriver-win64', 'chromedriver.exe')
        target_path = os.path.join(drivers_dir, 'chromedriver.exe')
        
        if os.path.exists(target_path):
            os.remove(target_path)
            
        os.rename(chromedriver_path, target_path)
        
        # 清理臨時文件
        os.rmdir(os.path.join(drivers_dir, 'chromedriver-win64'))
        
        logging.info("ChromeDriver 下載完成")
        return target_path
        
    except Exception as e:
        logging.error(f"下載 ChromeDriver 時發生錯誤: {str(e)}")
        raise

def convert_to_nitter_url(twitter_url):
    """將 Twitter URL 轉換為 Nitter URL"""
    # 提取用戶名和推文 ID
    match = re.match(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', twitter_url)
    if match:
        username, tweet_id = match.groups()
        # 使用 nitter.net 作為 Nitter 實例
        return f"https://nitter.net/{username}/status/{tweet_id}"
    return twitter_url

def setup_driver():
    """設置 Selenium WebDriver"""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')  # 使用新的 headless 模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.85 Safari/537.36')
        chrome_options.add_argument('--remote-debugging-port=9222')
        
        # 使用本地的 ChromeDriver
        current_dir = os.path.dirname(os.path.abspath(__file__))
        driver_path = os.path.join(current_dir, 'drivers', 'chromedriver.exe')
        
        # 如果 ChromeDriver 不存在，則下載
        if not os.path.exists(driver_path):
            driver_path = download_chromedriver()
            
        service = Service(executable_path=driver_path)
        
        # 嘗試多次連接
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                driver = webdriver.Chrome(service=service, options=chrome_options)
                # 測試連接
                driver.get("about:blank")
                return driver
            except Exception as e:
                if attempt < max_attempts - 1:
                    logging.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(2)  # 等待 2 秒後重試
                else:
                    raise
                    
    except Exception as e:
        logging.error(f"Error setting up driver: {str(e)}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """當用戶發送 /start 命令時的回應"""
    await update.message.reply_text(
        "歡迎使用 X 圖片下載機器人！\n"
        "請直接發送 X 貼文連結，我會幫你提取其中的圖片。"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理用戶發送的消息"""
    message_text = update.message.text
    
    # 檢查是否為 X 貼文連結
    if not re.match(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+', message_text):
        return

    try:
        # 設置 WebDriver
        driver = None
        try:
            driver = setup_driver()
            
            # 先嘗試原始連結
            driver.get(message_text)
            # 增加等待時間
            time.sleep(10)
            
            # 檢查是否需要登入
            if "Sign in" in driver.page_source or "登入" in driver.page_source:
                logging.info("Tweet requires login, trying Nitter")
                # 轉換為 Nitter URL
                nitter_url = convert_to_nitter_url(message_text)
                driver.get(nitter_url)
                time.sleep(10)
            
            # 等待頁面完全加載
            try:
                WebDriverWait(driver, 20).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except Exception as e:
                logging.error(f"Error waiting for page load: {str(e)}")
            
            # 初始化媒體列表
            images = []
            videos = []
            gifs = []
            
            # 使用 JavaScript 獲取所有媒體內容
            try:
                media_urls = driver.execute_script("""
                    // 獲取所有媒體元素
                    const mediaElements = [];
                    
                    // 獲取所有圖片元素
                    const images = document.querySelectorAll('img');
                    images.forEach(img => {
                        if (img.src && 
                            !img.src.includes('profile_images') && 
                            !img.src.includes('logo') &&
                            !img.src.includes('avatar') &&
                            (img.src.includes('media') || img.src.includes('pbs.twimg.com'))) {
                            mediaElements.push({
                                type: 'image',
                                url: img.src
                            });
                        }
                    });
                    
                    // 獲取所有媒體容器
                    const containers = document.querySelectorAll('div[data-testid="tweetPhoto"], div.tweet-body');
                    containers.forEach(container => {
                        const media = container.querySelector('img');
                        if (media) {
                            const url = media.src || media.getAttribute('srcset')?.split(',')[0].split(' ')[0];
                            if (url && 
                                !url.includes('logo') &&
                                !url.includes('avatar') &&
                                (url.includes('media') || url.includes('pbs.twimg.com'))) {
                                mediaElements.push({
                                    type: 'image',
                                    url: url
                                });
                            }
                        }
                    });
                    
                    return mediaElements;
                """)
                
                if media_urls:
                    logging.info(f"Found media URLs via JavaScript: {media_urls}")
                    for media in media_urls:
                        url = media['url']
                        if url:
                            # 過濾掉縮略圖和其他非圖片內容
                            if not ('thumb' in url.lower() or 'small' in url.lower() or 'logo' in url.lower() or 'avatar' in url.lower()):
                                if media['type'] == 'image':
                                    if url not in images:
                                        images.append(url)
                                        logging.info(f"Found image URL: {url}")
            except Exception as e:
                logging.error(f"Error executing JavaScript for media URLs: {str(e)}")
            
            # 如果沒有找到圖片，嘗試從頁面源碼中提取
            if not images:
                try:
                    page_source = driver.page_source
                    # 尋找圖片 URL 模式
                    image_patterns = [
                        r'https?://[^"\']+\.(?:jpg|jpeg|png|gif)[^"\']*',
                        r'https?://[^"\']+media[^"\']*',
                        r'https?://[^"\']+pbs\.twimg\.com[^"\']*'
                    ]
                    
                    for pattern in image_patterns:
                        matches = re.findall(pattern, page_source)
                        for match in matches:
                            if match and not ('thumb' in match.lower() or 'small' in match.lower() or 'profile_images' in match.lower() or 'logo' in match.lower() or 'avatar' in match.lower()):
                                if match not in images:
                                    images.append(match)
                                    logging.info(f"Found image URL from page source: {match}")
                except Exception as e:
                    logging.error(f"Error extracting image from page source: {str(e)}")
            
            logging.info(f"Total images found: {len(images)}")
            
            if not images:
                await update.message.reply_text("無法找到圖片內容。")
                return

            # 發送圖片
            if images:
                # 如果只有一張圖片，直接發送
                if len(images) == 1:
                    try:
                        await update.message.reply_photo(images[0])
                    except Exception as e:
                        logging.error(f"Error sending single photo: {str(e)}")
                        await update.message.reply_text("發送圖片時發生錯誤。")
                else:
                    # 使用媒體群組發送多張圖片，分批次發送
                    batch_size = 10  # 每批最多 10 張圖片
                    for start in range(0, len(images), batch_size):
                        media_group = []
                        end = min(start + batch_size, len(images))
                        for i in range(start, end):
                            img_url = images[i]
                            if i == start:
                                # 第一張圖片作為群組的主要圖片
                                media_group.append(InputMediaPhoto(media=img_url, caption=f"來自 {message_text} 的圖片"))
                            else:
                                media_group.append(InputMediaPhoto(media=img_url))
                        
                        try:
                            # 發送媒體群組
                            await update.message.reply_media_group(media=media_group)
                        except Exception as e:
                            logging.error(f"Error sending media group: {str(e)}")
                            # 如果群組發送失敗，嘗試單獨發送每張圖片
                            for img_url in images[start:end]:
                                try:
                                    await update.message.reply_photo(img_url)
                                except Exception as e:
                                    logging.error(f"Error sending individual photo: {str(e)}")
                                    continue

        except Exception as e:
            logging.error(f"Error in handle_message: {str(e)}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    except Exception as e:
        logging.error(f"Error: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理錯誤"""
    logging.error(f"Update {update} caused error {context.error}")

def main():
    """啟動機器人"""
    try:
        # 創建應用程式
        application = Application.builder().token(TOKEN).build()

        # 添加處理器
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # 添加錯誤處理器
        application.add_error_handler(error_handler)

        # 啟動機器人
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
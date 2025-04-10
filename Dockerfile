# 使用官方 Python 鏡像
FROM python:3.10-slim

# 安裝系統依賴和 Chrome
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    unzip \
    libnss3 \
    libxcb1 \
    libxdamage1 \
    libgbm1 \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# 下載並安裝 Chrome（獲取完整版本號）
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -yf && \
    rm google-chrome-stable_current_amd64.deb

# 獲取 Chrome 完整版本號（例如 117.0.5938.92）
RUN CHROME_FULL_VERSION=$(google-chrome --version | awk '{print $3}') && \
    echo "Chrome 完整版本號: $CHROME_FULL_VERSION" && \
    CHROME_MAJOR_VERSION=$(echo $CHROME_FULL_VERSION | cut -d'.' -f1) && \
    echo "Chrome 主版本號: $CHROME_MAJOR_VERSION" && \
    # 下載對應的 ChromeDriver
    wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_FULL_VERSION/linux64/chromedriver-linux64.zip" && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm -rf chromedriver-linux64.zip chromedriver-linux64

# 設置工作目錄
WORKDIR /app

# 複製代碼和安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 啟動命令
CMD ["python", "x_image_bot.py"]
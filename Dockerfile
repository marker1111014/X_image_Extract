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
    libdrm2 \
    xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# 下載並安裝 Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -yf && \
    rm google-chrome-stable_current_amd64.deb

# 下載並安裝 ChromeDriver（替換版本號）
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1) && \
    wget -q https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}.0.0.0/linux64/chromedriver-linux64.zip && \
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
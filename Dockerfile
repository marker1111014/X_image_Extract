# 使用官方 Python 鏡像
FROM python:3.10-slim

# 安裝系統核心依賴
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    gnupg \
    unzip \
    libnss3 \
    libxcb1 \
    libxdamage1 \
    libgbm1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libvulkan1 \
    libcurl4 \
    fonts-liberation \
    xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# 通過 Google 官方源安裝 Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /etc/apt/sources.list.d/google-chrome.list

# 獲取 Chrome 完整版本號
RUN CHROME_FULL_VERSION=$(google-chrome --version | awk '{print $3}') && \
    echo "Chrome 完整版本號: $CHROME_FULL_VERSION" && \
    # 下載對應 ChromeDriver
    wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_FULL_VERSION/linux64/chromedriver-linux64.zip" && \
    unzip chromedriver-linux64.zip && \
    mv chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/chromedriver && \
    rm -rf chromedriver-linux64*

# 設置工作目錄
WORKDIR /app

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 啟動命令
CMD ["python", "x_image_bot.py"]
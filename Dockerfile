# 使用 Python 3.11 並選擇 slim-buster 版本
FROM python:3.11-slim-buster

# 設定工作目錄
WORKDIR /app

# 複製當前目錄的所有文件到容器內部
COPY . /app

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 指定啟動命令
CMD ["python", "x_image_bot.py"]

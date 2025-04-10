# 選擇較新的 Python 基礎鏡像（例如 python:3.11-slim）
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 複製當前目錄的所有文件到容器內部
COPY . /app

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 指定啟動命令
CMD ["python", "x_image_bot.py"]

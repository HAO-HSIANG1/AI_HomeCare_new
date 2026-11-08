# HomeCare AI：單一映像，docker-compose 用它跑兩個服務（careflow：Streamlit 8501；checkin：打卡網頁 8600）。
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TZ=Asia/Taipei
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# 排班工作紀錄與打卡資料（sqlite）放在 /app/output_results，請用 volume 保存
VOLUME ["/app/output_results"]
EXPOSE 8501 8600
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]

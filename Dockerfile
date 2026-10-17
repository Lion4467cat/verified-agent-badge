FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
COPY IMPACT.md CALIBRATION.md SCALE.md ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.app:app --host 0.0.0.0 --port ${PORT}"]

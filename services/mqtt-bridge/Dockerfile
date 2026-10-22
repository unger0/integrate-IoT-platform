FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir 'paho-mqtt>=2,<3' 'httpx>=0.27,<1'
COPY main.py .
CMD ["python", "main.py"]

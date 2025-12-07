FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    paho-mqtt==1.6.1 \
    kafka-python==2.0.2 \
    python-dotenv==1.0.0

COPY mqtt_to_kafka.py /app/
COPY requirements.txt /app/
COPY mqtt-bridge.conf /mosquitto/config/mosquitto.conf

EXPOSE 1883 9001
CMD ["python", "mqtt_to_kafka.py"]
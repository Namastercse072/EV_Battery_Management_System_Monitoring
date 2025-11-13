FROM python:3.10-slim
RUN apt-get update -qq && apt-get install -y --no-install-recommends mosquitto-clients && apt-get clean
RUN pip install paho-mqtt numpy
COPY edge/app/sensor_simulate.py /app/sensor_simulate.py
WORKDIR /app
CMD ["python", "sensor_simulate.py"]
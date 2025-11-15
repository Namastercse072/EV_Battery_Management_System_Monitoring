FROM python:3.10-slim

WORKDIR /app

# install system deps and clean up apt lists
RUN apt-get update -qq \
 && apt-get install -y --no-install-recommends mosquitto-clients \
 && rm -rf /var/lib/apt/lists/*

# install Python deps in one layer
RUN pip install --no-cache-dir paho-mqtt numpy zstandard pybloom-live scikit-learn joblib requests

# copy the sensor script (must be inside build context)
COPY edge/app/sensor_simulate.py /app/sensor_simulate.py
COPY edge/models/Machine_learning.py /app/models/Machine_learning.py
CMD ["python", "sensor_simulate.py"]
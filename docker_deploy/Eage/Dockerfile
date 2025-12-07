FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    paho-mqtt==1.6.1 \
    numpy==1.24.3 \
    scikit-learn==1.3.0 \
    python-dotenv==1.0.0 \
    zstandard==0.21.0 \
    pybloom_live==4.0.0 \
    psutil==5.9.5 \
    Flask==2.3.3

# Create models directory with write permissions
RUN mkdir -p /app/models && chmod 777 /app/models
# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

COPY edge/app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as non-root but ensure directory is writable
RUN chown -R nobody:nogroup /app/models
# Copy sensor simulator script
COPY edge/app/sensor_simulate.py .
# Run with unbuffered output for real-time logs
CMD ["python", "-u", "sensor_simulate.py"]
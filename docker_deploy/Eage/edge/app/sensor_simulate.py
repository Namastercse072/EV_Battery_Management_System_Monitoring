import zstandard as zstd
import numpy as np
import time, json, random, socket, paho.mqtt.client as mqtt
from pybloom_live import BloomFilter

client = mqtt.Client()
client.connect("mqtt-broker", 1883)
client.loop_start()  # run background thread to handle MQTT
bloom = BloomFilter(capacity=1000, error_rate=0.001)

def send_if_new(sample):
    sig = f"{round(sample['voltage'],2)}-{round(sample['temperature'],1)}"
    if sig not in bloom:
        bloom.add(sig)
        compressed = compress_data(sample)
        client.publish("ev/compressed", compressed)

def compress_data(data: dict):
    raw = json.dumps(data).encode('utf-8')
    cctx = zstd.ZstdCompressor(level=3)
    return cctx.compress(raw)

while True:
    # try:
    #     # client.connect("mqtt-broker", 1883)
    #     break
    # except socket.gaierror:
    #     print("⚠️ Broker not found, retrying...")
    #     time.sleep(5)
    print("✅ Connected to MQTT broker")    
    msg = {
        "voltage": round(np.random.uniform(3.0, 4.2), 2),
        "temperature": round(np.random.uniform(20, 45), 1),
        "current": round(np.random.uniform(0, 100), 1),
        "soh": round(np.random.uniform(50, 100), 1),
        "remaining_capacity": round(np.random.uniform(10, 100), 1),
        "soc": round(np.random.uniform(20, 100), 1),
        "timestamp": time.time()
    }
    '''Compress and send data'''
    if(False):
        compressed = compress_data(msg)
        client.publish("ev/sensor", json.dumps(compressed.decode('latin1')))
    else:
        client.publish("ev/sensor", json.dumps(msg))
    '''Send only if new (using bloom filter)''' 
    send_if_new(msg)
    time.sleep(2)

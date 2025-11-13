import time, json, random, socket
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("mqtt-broker", 1883)

while True:
    # try:
    #     client.connect("mqtt-broker", 1883)
    #     break
    # except socket.gaierror:
    #     print("⚠️ Broker not found, retrying...")
    #     time.sleep(5)
    msg = {
        "voltage": round(random.uniform(3.0, 4.2), 2),
        "temperature": round(random.uniform(20, 45), 1),
        "current": round(random.uniform(0, 100), 1),
        "soh": round(random.uniform(50, 100), 1),
        "remaining_capacity": round(random.uniform(10, 100), 1),
        "soc": round(random.uniform(20, 100), 1),
        "timestamp": time.time()
    }
    client.publish("ev/sensor", json.dumps(msg))
    time.sleep(2)

from sklearn.ensemble import IsolationForest
import joblib, os, requests, time, json
import paho.mqtt.client as mqtt
import numpy as np

# load trained model
MODEL_URL = "https://example.com/models/isoforest.pkl"
MODEL_PATH = "/app/models/isoforest.pkl"
os.makedirs("/app/models", exist_ok=True)

if not os.path.exists(MODEL_PATH):
    print("📥 Downloading IsolationForest model...")
    r = requests.get(MODEL_URL)
    if r.status_code == 200:
        with open(MODEL_PATH, "wb") as f:
            f.write(r.content)
        print("✅ Model downloaded successfully.")
    else:
        print(f"⚠️ Model fetch failed: {r.status_code}")

if not os.path.exists(MODEL_PATH):
    print("⚠️ No model found — training a new one")
    dummy_data = np.random.rand(100, 3)
    model = IsolationForest(contamination=0.05).fit(dummy_data)
    print("✅ Model trained and saved")
    joblib.dump(model, MODEL_PATH)
else:
    print("✅ Loading existing model")
    model = joblib.load(MODEL_PATH)
client = mqtt.Client()
client.connect("mqtt-broker", 1883)

def detect_fault(data):
    X = [[data['voltage'], data['temperature'], data['soc']]]
    pred = model.predict(X)
    if pred[0] == -1:
        print("⚠️ Fault detected:", data)
        client.publish("ev/fault", json.dumps(data))
    else:
        print("✅ Normal:", data)

def on_message(client, userdata, msg):
    """Callback when a message is received."""
    try:
        payload = json.loads(msg.payload.decode())
        print(f"📨 Received from {msg.topic}: {payload}")
        detect_fault(payload)
    except json.JSONDecodeError:
        print(f"⚠️ Failed to parse JSON from {msg.topic}")

client.on_message = on_message
client.subscribe("ev/sensor")  # subscribe to sensor data
print("🔗 Connected to MQTT broker. Listening on ev/metrics...")
client.loop_forever()  # blocks and listens for incoming messages
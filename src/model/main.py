import cv2
import mediapipe as mp
import serial
import time
import os
import numpy as np
import tensorflow as tf
from collections import deque
import speech_recognition as sr
import threading

# ওয়ার্নিং বন্ধ করার জন্য
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# ================= 1. সেটআপ সেকশন =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ei-project-shajidur-project-1-classifier-tensorflow-lite-float32-model.3.lite")

# তোর 4টা ক্লাসের আসল নাম এখানে দিবি (Edge Impulse-এ যেভাবে ছিল)
CLASSES = ["Hehe", "Hello_1", "Hello_2", "Hello_3"] 

# পোর্ট সেটআপ (তোর অনুযায়ী পোর্ট নাম্বারগুলো চেঞ্জ করে নিবি)
SERIAL_PORT_IN = 'COM8'   # যেটাতে সেন্সর লাগানো ESP32-S3 আছে
SERIAL_PORT_OUT = 'COM9'  # যেটাতে রেজাল্ট পাঠাবি (দ্বিতীয় ESP32)
BAUD_RATE = 115200

# সেন্সর ইনপুট কানেকশন
try:
    ser_in = serial.Serial(SERIAL_PORT_IN, BAUD_RATE, timeout=1)
    print(f"[SUCCESS] Connected to Input ESP32 on {SERIAL_PORT_IN}")
except Exception as e:
    print(f"[ERROR] Cannot connect to {SERIAL_PORT_IN}. Check cable!")
    ser_in = None

# আউটপুট কানেকশন
try:
    ser_out = serial.Serial(SERIAL_PORT_OUT, BAUD_RATE, timeout=1)
    print(f"[SUCCESS] Connected to Output ESP32 on {SERIAL_PORT_OUT}")
except Exception as e:
    print(f"⚠️ Warning: Output ESP32 on {SERIAL_PORT_OUT} not connected. Skipping output send.")
    ser_out = None

# ================= 1.5 স্পিচ টু টেক্সট (বাংলা) সেকশন =================
print("মাইক্রোফোন সেটআপ হচ্ছে... 🎤")
recognizer = sr.Recognizer()

def listen_and_convert():
    with sr.Microphone() as source:
        # চারপাশের নয়েজ ফিল্টার করা
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("🎤 [MIC READY] আপনি এখন কথা বলতে পারেন...")
        
        while True:
            try:
                # কথা শোনার জন্য অপেক্ষা করবে
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                # গুগলের এপিআই দিয়ে কথাকে বাংলা টেক্সট করা
                text = recognizer.recognize_google(audio, language="bn-BD")
                print(f"\n[🗣️ VOICE INPUT]: {text}\n")
                
            except sr.UnknownValueError:
                pass
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                # ইন্টারনেট না থাকলে বা অন্য এরর হলে
                pass

# ব্যাকগ্রাউন্ডে কথা শোনার ইঞ্জিন চালু করা (যাতে ক্যামেরা না আটকায়)
voice_thread = threading.Thread(target=listen_and_convert)
voice_thread.daemon = True
voice_thread.start()

# ================= 2. এআই ব্রেইন লোড =================
print("AI Brain লোড হচ্ছে... 🧠")
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
print("✅ AI Model Loaded Successfully! 🚀")

# ================= 3. ভিশন এবং ডেটা বাফার =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
# ক্যামেরা উইন্ডো সাইজ ঠিক করা
cv2.namedWindow("Smart Glove Vision AI", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Smart Glove Vision AI", 800, 450)

# মডেলের জন্য 1060 ফিচারের বাফার (20 ফ্রেম * 53 ফিচার = 1060)
data_buffer = deque(maxlen=20)
last_sensor_data = [0.0] * 11
current_prediction = "Waiting..."
confidence = 0.0

print("\n" + "="*50)
print("🚀 AI INFERENCE & VOICE SYSTEM RUNNING 🚀")
print("Press 'q' to quit.")
print("="*50 + "\n")

# ================= 4. মেইন রিয়েল-টাইম লুপ =================
while True:
    ret, frame = cap.read()
    if not ret: 
        break

    frame = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    # মিডিয়াপাইপ থেকে 42 ফিচার (21 x, y)
    hand_data = [0.0] * 42 
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        idx = 0
        for lm in hand_landmarks.landmark:
            hand_data[idx], hand_data[idx+1] = round(lm.x, 4), round(lm.y, 4)
            idx += 2

    # ESP32 (COM8) থেকে 11 সেন্সর ডেটা রিড
    if ser_in and ser_in.in_waiting > 0:
        try:
            line = ser_in.readline().decode('utf-8').strip()
            if line:
                parts = line.split(' | ')
                if len(parts) == 3:
                    flex_str = parts[0].split(':')[1].split(',')
                    accel_str = parts[1].split(':')[1].split(',')
                    gyro_str = parts[2].split(':')[1].split(',')
                    
                    # স্ট্রিং থেকে ফ্লোটে রূপান্তর
                    raw_sensor = flex_str + accel_str + gyro_str
                    last_sensor_data = [float(val) for val in raw_sensor]
        except:
            pass 

    # 53 ফিচারের একটা সিগন্যাল ফ্রেম (11 sensor + 42 hand)
    combined_features = last_sensor_data + hand_data
    data_buffer.append(combined_features)

    # ================= 5. এআই প্রেডিকশন =================
    if len(data_buffer) == 20:
        # বাফারের 20x53 ডেটাকে ফ্ল্যাট করে [1, 1060] শেইপ বানানো
        input_array = np.array(data_buffer, dtype=np.float32).flatten().reshape(1, 1060)
        
        # মডেলে ডেটা দেওয়া
        interpreter.set_tensor(input_details[0]['index'], input_array)
        interpreter.invoke()
        
        # আউটপুট নেওয়া
        output_data = interpreter.get_tensor(output_details[0]['index'])[0]
        max_idx = np.argmax(output_data)
        confidence = output_data[max_idx]

        # যদি 70% এর বেশি সিওর হয়, তাহলে আউটপুট দেখাবে
        if confidence > 0.70:
            current_prediction = CLASSES[max_idx]
            
            # রেজাল্ট দ্বিতীয় ESP32-তে পাঠানো
            if ser_out:
                msg = f"{current_prediction}\n"
                ser_out.write(msg.encode('utf-8'))
        else:
            current_prediction = "Unknown"

    # ================= 6. অন-স্ক্রিন ডিসপ্লে (HUD) =================
    cv2.rectangle(frame, (10, 10), (450, 100), (0, 0, 0), -1)
    
    cv2.putText(frame, f"Sign: {current_prediction}", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    cv2.putText(frame, f"Confidence: {confidence*100:.1f}%", (20, 85), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("Smart Glove Vision AI", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ক্লিনআপ
cap.release()
cv2.destroyAllWindows()
if ser_in: ser_in.close()
if ser_out: ser_out.close()
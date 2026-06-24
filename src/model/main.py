import cv2
import mediapipe as mp
import serial
import os
import numpy as np
import tensorflow as tf
from collections import deque
import speech_recognition as sr
import threading
import vlc  # 🎵 VLC লাইব্রেরি .aac বাজানোর জন্য

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# ================= 1. সেটআপ সেকশন =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ei-project-shajidur-project-1-classifier-tensorflow-lite-float32-model.3.lite")

# 🎵 তোর কাস্টম .aac অডিও ফাইলের লোকেশন
AUDIO_FILE = os.path.join(BASE_DIR, "ab.aac") 

CLASSES = ["Hehe", "Hello_1", "Hello_2", "Hello_3"] 

# ⚠️ তোর ল্যাপটপের সঠিক COM পোর্টগুলো এখানে বসাবি ⚠️
SERIAL_PORT_IN = 'COM13'   # সেন্সর গ্লাভস এর বোর্ড
SERIAL_PORT_OUT = 'COM8'   # ডিসপ্লের বোর্ড
BAUD_RATE = 115200

# পোর্ট কানেকশন
try:
    ser_in = serial.Serial(SERIAL_PORT_IN, BAUD_RATE, timeout=1)
except:
    ser_in = None
    print(f"⚠️ Warning: Input ESP32 on {SERIAL_PORT_IN} not connected.")

try:
    ser_out = serial.Serial(SERIAL_PORT_OUT, BAUD_RATE, timeout=1)
except:
    ser_out = None
    print(f"⚠️ Warning: Output ESP32 on {SERIAL_PORT_OUT} not connected.")

# ================= 1.5 স্পিচ রিকগনিশন =================
recognizer = sr.Recognizer()

def listen_and_convert():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("🎤 [MIC READY] You can speak now...")
        
        while True:
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = recognizer.recognize_google(audio, language="en-US")
                print(f"\n[🗣️ VOICE INPUT]: {text}\n")
                
                if ser_out:
                    msg = f"VOICE:{text}\n"
                    ser_out.write(msg.encode('utf-8'))
                    
            except sr.UnknownValueError:
                pass
            except sr.WaitTimeoutError:
                pass
            except Exception:
                pass

voice_thread = threading.Thread(target=listen_and_convert)
voice_thread.daemon = True
voice_thread.start()

# ================= 2. এআই ব্রেইন লোড =================
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# ================= 3. ভিশন এবং ডেটা বাফার =================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cv2.namedWindow("Smart Glove Vision AI", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Smart Glove Vision AI", 800, 450)

data_buffer = deque(maxlen=20)
last_sensor_data = [0.0] * 11
current_prediction = "Waiting..."
confidence = 0.0
last_spoken_sign = ""  

# ================= 4. মেইন রিয়েল-টাইম লুপ =================
while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)
    
    hand_data = [0.0] * 42 
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        idx = 0
        for lm in hand_landmarks.landmark:
            hand_data[idx], hand_data[idx+1] = round(lm.x, 4), round(lm.y, 4)
            idx += 2

    # সিরিয়াল সেন্সর ডেটা রিড
    if ser_in and ser_in.in_waiting > 0:
        try:
            line = ser_in.readline().decode('utf-8').strip()
            if line:
                parts = line.split(' | ')
                if len(parts) == 3:
                    flex_str = parts[0].split(':')[1].split(',')
                    accel_str = parts[1].split(':')[1].split(',')
                    gyro_str = parts[2].split(':')[1].split(',')
                    raw_sensor = flex_str + accel_str + gyro_str
                    last_sensor_data = [float(val) for val in raw_sensor]
        except:
            pass 

    combined_features = last_sensor_data + hand_data
    data_buffer.append(combined_features)

    # ================= 5. এআই প্রেডিকশন =================
    if len(data_buffer) == 20:
        input_array = np.array(data_buffer, dtype=np.float32).flatten().reshape(1, 1060)
        interpreter.set_tensor(input_details[0]['index'], input_array)
        interpreter.invoke()
        
        output_data = interpreter.get_tensor(output_details[0]['index'])[0]
        max_idx = np.argmax(output_data)
        confidence = output_data[max_idx]

        if confidence > 0.70:
            current_prediction = CLASSES[max_idx]
            
            # ডিসপ্লের ESP32-তে সাইন পাঠানো
            if ser_out:
                msg = f"SIGN:{current_prediction}\n"
                ser_out.write(msg.encode('utf-8'))
                
            # 🎵 তোর কাস্টম .aac অডিও প্লে করা (VLC দিয়ে)
            if current_prediction == "Hello_3" and last_spoken_sign != "Hello_3":
                print(f"\n🔊 [SPEAKER]: Playing {AUDIO_FILE}...\n")
                try:
                    player = vlc.MediaPlayer(AUDIO_FILE)
                    player.play()
                except Exception as e:
                    print(f"⚠️ Audio Error: {e} (Check if VLC is installed!)")
                last_spoken_sign = "Hello_3"
                
            elif current_prediction != "Hello_3":
                last_spoken_sign = current_prediction
                
        else:
            current_prediction = "Waiting..."

    # ================= 6. অন-স্ক্রিন ডিসপ্লে (HUD) =================
    cv2.rectangle(frame, (10, 10), (450, 100), (0, 0, 0), -1)
    cv2.putText(frame, f"Sign: {current_prediction}", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    cv2.putText(frame, f"Confidence: {confidence*100:.1f}%", (20, 85), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("Smart Glove Vision AI", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
if ser_in: ser_in.close()
if ser_out: ser_out.close()
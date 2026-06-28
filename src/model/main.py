import cv2
import mediapipe as mp
import random
import urllib.request
import os
import threading
import speech_recognition as sr
import serial
import pygame

# ================= 1. ESP32 সিরিয়াল কানেকশন =================
SERIAL_PORT = 'COM3' 
BAUD_RATE = 115200
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"[SUCCESS] Connected to ESP32 Display on {SERIAL_PORT}")
except:
    ser = None
    print(f"[WARNING] ESP32 not found on {SERIAL_PORT}!")

# ================= 2. সাউন্ড ইঞ্জিন সেটআপ =================
pygame.mixer.init()

# ফাইলের লোকেশন নিশ্চিত করার জন্য পাথ সেটআপ
base_dir = os.path.dirname(os.path.abspath(__file__))

AUDIO_MAP = {
    "Salam": os.path.join(base_dir, "salam.mp3"),
    "Food": os.path.join(base_dir, "food.mp3"),
    "Help": os.path.join(base_dir, "help.mp3"),
    "Yes": os.path.join(base_dir, "yes.mp3"),
    "No": os.path.join(base_dir, "no.mp3"),
    "Water": os.path.join(base_dir, "water.mp3"),
    "Victory": os.path.join(base_dir, "ok.mp3")
}

def play_audio(sign_name):
    file_path = AUDIO_MAP.get(sign_name)
    if file_path and os.path.exists(file_path):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
    else:
        print(f"[INFO] No audio file for {sign_name} at {file_path}")

def send_to_esp(data_type, text):
    if ser and ser.is_open:
        try:
            message = f"{data_type}:{text}\n"
            ser.write(message.encode('utf-8'))
        except Exception as e:
            print(f"[SERIAL ERROR] {e}")

# ================= 3. ভয়েস রিকগনিশন থ্রেড =================
def listen_to_voice():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n[🎤] Mic is ACTIVE!...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        while True:
            try:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                text = recognizer.recognize_google(audio, language="en-US")
                print(f">>> [🗣️ VOICE]: {text}")
                send_to_esp("VOICE", text)
            except: pass

voice_thread = threading.Thread(target=listen_to_voice, daemon=True)
voice_thread.start()

# ================= 4. Google AI সেটআপ =================
MODEL_PATH = os.path.join(base_dir, "gesture_recognizer.task")
if not os.path.exists(MODEL_PATH):
    urllib.request.urlretrieve("https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task", MODEL_PATH)

options = mp.tasks.vision.GestureRecognizerOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=mp.tasks.vision.RunningMode.IMAGE
)
recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)

# ================= 5. মেইন লুপ =================
SIGN_MAP = {
    "Open_Palm": "Salam", "Closed_Fist": "Food", "Pointing_Up": "Help",
    "Thumb_Up": "Yes", "Thumb_Down": "No", "ILoveYou": "Water", "Victory": "Victory"
}

cap = cv2.VideoCapture(1) 
cv2.namedWindow("Smart Glove AI", cv2.WINDOW_NORMAL)
last_sent_sign = "" 

print("\n[*] System READY. Press 'q' to Quit.")

while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    results = recognizer.recognize(mp_image)
    
    current_prediction = "Waiting..."
    
    if results.hand_landmarks:
        if results.gestures and len(results.gestures) > 0:
            ai_sign = results.gestures[0][0].category_name
            if ai_sign != "None":
                current_prediction = SIGN_MAP.get(ai_sign, ai_sign)
        
        landmarks = results.hand_landmarks[0]
        h, w, _ = frame.shape
        for lm in landmarks:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 5, (0, 0, 255), -1)

    # লজিক: ESP32-তে পাঠানো এবং সাউন্ড প্লে
    if current_prediction != "Waiting..." and current_prediction != last_sent_sign:
        send_to_esp("SIGN", current_prediction)
        play_audio(current_prediction)
        last_sent_sign = current_prediction

    # UI
    cv2.rectangle(frame, (10, 10), (450, 100), (0, 0, 0), -1)
    cv2.putText(frame, f"Sign: {current_prediction}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    cv2.imshow("Smart Glove AI", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
if ser: ser.close()
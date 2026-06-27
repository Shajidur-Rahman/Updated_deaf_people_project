import cv2
import mediapipe as mp
import random
import urllib.request
import os
import threading
import speech_recognition as sr
import serial

# ================= 1. ESP32 সিরিয়াল কানেকশন =================
SERIAL_PORT = 'COM3' 
BAUD_RATE = 115200
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"[SUCCESS] Connected to ESP32 Display on {SERIAL_PORT}")
except Exception as e:
    ser = None
    print(f"[WARNING] ESP32 not found on {SERIAL_PORT}! Running AI in standalone mode.")

# ডেটা পাঠানোর স্মার্ট ফাংশন (C++ কোডের সাথে সিঙ্ক করা)
def send_to_esp(data_type, text):
    if ser and ser.is_open:
        try:
            # ফরম্যাট: "SIGN:Salam\n" অথবা "VOICE:Hello World\n"
            message = f"{data_type}:{text}\n"
            ser.write(message.encode('utf-8'))
        except Exception as e:
            print(f"[SERIAL ERROR] {e}")

# ================= 2. কাস্টম সাইন ডিকশনারি =================
SIGN_MAP = {
    "Open_Palm": "Salam",
    "Closed_Fist": "Food",
    "Pointing_Up": "Help",
    "Thumb_Up": "Yes",
    "Thumb_Down": "No",
    "ILoveYou": "Water",
    "Victory": "Victory"
}

# ================= 3. ভয়েস রিকগনিশন (ব্যাকগ্রাউন্ড থ্রেড) =================
def listen_to_voice():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n[🎤] Mic is ACTIVE! Calibrating for background noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[🎤] Ready! Speak into the webcam mic...\n")
        
        while True:
            try:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                text = recognizer.recognize_google(audio, language="en-US")
                print(f">>> [🗣️ VOICE]: {text}")
                
                # ESP32 কে ভয়েস টেক্সট পাঠানো হচ্ছে (VOICE: ট্যাগ দিয়ে)
                send_to_esp("VOICE", text)
                
            except sr.WaitTimeoutError:
                pass 
            except sr.UnknownValueError:
                pass 
            except Exception:
                pass

voice_thread = threading.Thread(target=listen_to_voice, daemon=True)
voice_thread.start()

# ================= 4. Google AI Model ডাউনলোড =================
MODEL_PATH = "gesture_recognizer.task"
if not os.path.exists(MODEL_PATH):
    print("[*] Downloading Google's Real AI Gesture Model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
        MODEL_PATH
    )

# ================= 5. AI ব্রেইন সেটআপ =================
mp_tasks = mp.tasks
BaseOptions = mp_tasks.BaseOptions
GestureRecognizer = mp_tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp_tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp_tasks.vision.RunningMode

options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE
)
recognizer = GestureRecognizer.create_from_options(options)

# ================= 6. ক্যামেরা সেটআপ =================
cap = cv2.VideoCapture(1) 
cv2.namedWindow("Smart Glove AI", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Smart Glove AI", 800, 450)

hack_mode = False
last_sent_sign = "" 

print("\n[*] Full System READY (AI + Voice + ESP32 Display)")
print("[*] Press 'e' for Hack Mode, 'r' for Normal Mode, 'q' to Quit")

# ================= 7. মেইন লুপ =================
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

    # ================= 8. দ্য হ্যাক ইঞ্জিন =================
    if hack_mode:
        fake_results = ["ERROR", "GLITCH", "NOISE"]
        current_prediction = random.choice(fake_results)

    # ================= 9. ESP32 তে সাইন পাঠানো =================
    # শুধুমাত্র সাইন পরিবর্তন হলেই ESP32 কে পাঠানো হবে (ল্যাগ ফ্রি ডিসপ্লে)
    if current_prediction != "Waiting..." and current_prediction != last_sent_sign:
        send_to_esp("SIGN", current_prediction) # SIGN: ট্যাগ দিয়ে পাঠানো হচ্ছে
        last_sent_sign = current_prediction

    # UI ডিজাইন
    cv2.rectangle(frame, (10, 10), (450, 100), (0, 0, 0), -1)
    text_color = (0, 0, 255) if hack_mode else (0, 255, 0)
    cv2.putText(frame, f"Sign: {current_prediction}", (20, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, text_color, 3)

    cv2.imshow("Smart Glove AI", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('e'): hack_mode = True
    elif key == ord('r'): hack_mode = False

cap.release()
cv2.destroyAllWindows()
if ser: ser.close()
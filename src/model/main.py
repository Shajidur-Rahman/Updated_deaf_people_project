import cv2
import mediapipe as mp
import random
import urllib.request
import os

# ================= 1. Google AI Model ডাউনলোড =================
MODEL_PATH = "gesture_recognizer.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading Google's Real AI Gesture Model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
        MODEL_PATH
    )

# ================= 2. AI ব্রেইন সেটআপ =================
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

# ================= 3. ক্যামেরা সেটআপ =================
cap = cv2.VideoCapture(1)
cv2.namedWindow("Smart Glove Vision AI", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Smart Glove Vision AI", 800, 450)

hack_mode = False

print("\n[*] Google AI Tracker is READY!")
print("[*] I can see: Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou")
print("[*] Press 'e' for Hack Mode, 'r' for Normal Mode, 'q' to Quit\n")

# ================= 4. মেইন লুপ =================
while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # AI-এর জন্য ইমেজ রেডি করা
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    results = recognizer.recognize(mp_image)
    
    current_prediction = "Listening..."
    
    if results.hand_landmarks:
        # 🧠 গুগলের ৭টা সাইন ডিটেক্ট করা
        if results.gestures and len(results.gestures) > 0:
            ai_sign = results.gestures[0][0].category_name
            if ai_sign != "None":
                current_prediction = ai_sign
        
        # হাতের পয়েন্টগুলো ড্র করা (গোল্ডেন লুক)
        landmarks = results.hand_landmarks[0]
        h, w, _ = frame.shape
        for lm in landmarks:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 5, (0, 0, 255), -1)

    # ================= 5. দ্য হ্যাক ইঞ্জিন =================
    if hack_mode:
        fake_results = ["ERROR 404", "SYSTEM_GLITCH", "UNKNOWN_SIGN", "NOISE"]
        current_prediction = random.choice(fake_results)

    # UI ডিজাইন
    cv2.rectangle(frame, (10, 10), (450, 100), (0, 0, 0), -1)
    text_color = (0, 0, 255) if hack_mode else (0, 255, 0)
    cv2.putText(frame, f"AI Sign: {current_prediction}", (20, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, text_color, 3)

    cv2.imshow("Smart Glove Vision AI", frame)
    
    # স্পাই কন্ট্রোল
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    elif key == ord('e'): hack_mode = True
    elif key == ord('r'): hack_mode = False

cap.release()
cv2.destroyAllWindows()
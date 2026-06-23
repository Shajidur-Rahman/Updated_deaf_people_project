import cv2
import mediapipe as mp
import serial
import csv
import time

# তোর ESP32-S3 এর COM Port
SERIAL_PORT = 'COM8' 
BAUD_RATE = 115200

# সিরিয়াল পোর্ট কানেকশন সেটআপ
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"[SUCCESS] Connected to ESP32-S3 on {SERIAL_PORT}")
except Exception as e:
    print(f"[ERROR] Cannot connect to {SERIAL_PORT}. Check your cable and close Arduino Serial Monitor!")
    exit()

# MediaPipe হ্যান্ড ট্র্যাকিং সেটআপ
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# 1 নম্বর পোর্টের এক্সটার্নাল ক্যামেরা চালু করা (DSHOW দিয়ে)
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

# 🚀 ল্যাগ ফিক্স: ইউএসবি ব্যান্ডউইথ লিমিট ভাঙার জন্য MJPG ফরম্যাট
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# 🚀 ল্যাগ ফিক্স: C270-এর নেটিভ রেজোলিউশন (1280x720) সেট করা
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# 🚀 ল্যাগ ফিক্স: বাফার সাইজ 1 করে দেওয়া (রিয়েল-টাইম স্পিডের জন্য)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# 🚀 ল্যাগ ফিক্স: ক্যামেরাকে 30 FPS এ চলতে বাধ্য করা
cap.set(cv2.CAP_PROP_FPS, 30)

# ক্যামেরা রেজোলিউশন প্রিন্ট করা
print(f"[*] Camera Active: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)} x {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)} @ {cap.get(cv2.CAP_PROP_FPS)}FPS")

# CSV ফাইল তৈরি করা
csv_filename = "sign_language_dataset.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    
    # ফাইলের কলামগুলোর নাম (Headers) তৈরি করা
    headers = ['Timestamp', 'Flex1', 'Flex2', 'Flex3', 'Flex4', 'Flex5', 
               'AccelX', 'AccelY', 'AccelZ', 'GyroX', 'GyroY', 'GyroZ']
    
    # হাতের ২১টি জয়েন্টের X এবং Y পজিশনের জন্য ৪২টি কলাম
    for i in range(21):
        headers.extend([f'Hand_X_{i}', f'Hand_Y_{i}'])
    
    writer.writerow(headers)
    print("\n[READY] Recording started! Show your hand to the camera.")
    print(">>> Press 'q' on your keyboard to stop and save. <<<\n")

    while True:
        ret, frame = cap.read()
        if not ret: 
            print("[ERROR] Camera frame dropped! USB connection might be loose.")
            break

        # ওয়েবক্যামের ছবি প্রসেস করা (BGR থেকে RGB)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        # ডিফল্ট হাতের ডেটা (যদি হাত ক্যামেরায় না দেখা যায়)
        hand_data = [0.0] * 42 

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0] # প্রথম হাতটা নিচ্ছি
            # স্ক্রিনে হাতের ওপর জয়েন্টগুলো আঁকা
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            idx = 0
            for lm in hand_landmarks.landmark:
                hand_data[idx] = round(lm.x, 4)
                hand_data[idx+1] = round(lm.y, 4)
                idx += 2

        # গ্লাভস (ESP32-S3) থেকে ডেটা পড়া
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                
                # ডেটা পার্সিং (ESP32 এর আউটপুট ফরম্যাট অনুযায়ী)
                if line:
                    parts = line.split(' | ')
                    if len(parts) == 3:
                        flex_str = parts[0].split(':')[1].split(',')
                        accel_str = parts[1].split(':')[1].split(',')
                        gyro_str = parts[2].split(':')[1].split(',')

                        sensor_data = flex_str + accel_str + gyro_str

                        # সেন্সর ডেটা এবং ক্যামেরার ডেটা একসাথে মিলিয়ে CSV-তে সেভ করা
                        current_time = round(time.time(), 3)
                        row = [current_time] + sensor_data + hand_data
                        writer.writerow(row)
            except Exception as e:
                pass # সিরিয়ালে কোনো গার্বেজ ডেটা আসলে সেটা স্কিপ করবে

        # স্ক্রিনে ক্যামেরা ফিড দেখানো
        cv2.imshow("Smart Glove Vision (Press 'q' to Exit)", frame)
        
        # 'q' চাপলে রেকর্ড বন্ধ হয়ে যাবে
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# কাজ শেষে সবকিছু ঠিকঠাক বন্ধ করা
cap.release()
cv2.destroyAllWindows()
ser.close()
print(f"\n[SAVED] All data successfully saved to {csv_filename}!")
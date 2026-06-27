import cv2
import csv
import time
import os

try:
    import mediapipe as mp
except Exception as exc:
    mp = None
    print(f"[WARN] Mediapipe unavailable: {exc}")

try:
    import serial
except ImportError:
    serial = None

# ================= সেটআপ সেকশন =================
SERIAL_PORT = 'COM8' 
BAUD_RATE = 115200

ser = None
if serial is not None:
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"[SUCCESS] Connected to ESP32-S3 on {SERIAL_PORT}")
    except Exception as e:
        print(f"[WARN] Cannot connect to {SERIAL_PORT}. Check cable or serial settings: {e}")
else:
    print("[WARN] pyserial is not installed. Continuing without serial communication.")

mp_hands = None
hands = None
mp_draw = None
if mp is not None:
    try:
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)
        mp_draw = mp.solutions.drawing_utils
    except Exception as exc:
        print(f"[WARN] Mediapipe hand tracking setup failed: {exc}")
        mp_hands = None
        hands = None
        mp_draw = None

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 30)

print(f"[*] Camera Active: 1280x720 @ 30FPS")

# ================= স্মার্ট সিস্টেম ভেরিয়েবল =================
headers = ['Timestamp', 'Flex1', 'Flex2', 'Flex3', 'Flex4', 'Flex5', 
           'AccelX', 'AccelY', 'AccelZ', 'GyroX', 'GyroY', 'GyroZ']
for i in range(21):
    headers.extend([f'Hand_X_{i}', f'Hand_Y_{i}'])

sign_name = ""
take_number = 1
is_recording = False
recorded_data = [] # ডেটা র‍্যামে বাফার করার জন্য (ল্যাগ ফ্রি)
start_time = 0
last_sensor_data = [0.0] * 11 # সেন্সর ডেটা মিসিং হলে ব্যাকআপ

print("\n" + "="*50)
print("🚀 SMART DATA ACQUISITION SYSTEM READY 🚀")
print("="*50)
print("Select the Camera Window and use keyboard commands:")
print("[n] - Enter a new Sign Name (in terminal)")
print("[r] - Start recording")
print("[s] - Stop recording and save")
print("[v] - Verify the last recording status")
print("[d] - Delete the last recorded file")
print("[q] - Quit the system")
print("="*50 + "\n")

# ================= মেইন লুপ =================
while True:
    ret, frame = cap.read()
    if not ret: 
        break

    frame = cv2.flip(frame, 1) # আয়নার মতো সোজা ভিউ পাওয়ার জন্য
    hand_data = [0.0] * 42 

    if hands is not None and mp_draw is not None:
        try:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)
            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                idx = 0
                for lm in hand_landmarks.landmark:
                    hand_data[idx], hand_data[idx+1] = round(lm.x, 4), round(lm.y, 4)
                    idx += 2
        except Exception as exc:
            print(f"[WARN] Hand tracking frame failed: {exc}")

    # ESP32 থেকে ডেটা পড়া
    if ser is not None and ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                parts = line.split(' | ')
                if len(parts) == 3:
                    flex_str = parts[0].split(':')[1].split(',')
                    accel_str = parts[1].split(':')[1].split(',')
                    gyro_str = parts[2].split(':')[1].split(',')
                    last_sensor_data = flex_str + accel_str + gyro_str
        except Exception:
            pass 

    # রেকর্ডিং চালু থাকলে ডেটা র‍্যামে জমানো
    if is_recording:
        current_time = round(time.time() - start_time, 3)
        row = [current_time] + last_sensor_data + hand_data
        recorded_data.append(row)

    # ================= অন-স্ক্রিন HUD (Heads-Up Display) =================
    # ব্যাকগ্রাউন্ড প্যানেল আঁকা
    cv2.rectangle(frame, (10, 10), (450, 140), (0, 0, 0), -1)
    
    # স্ট্যাটাস টেক্সট
    status_color = (0, 0, 255) if is_recording else (0, 255, 0)
    status_text = "RECORDING (Press 's' to stop)" if is_recording else "READY (Press 'r' to start)"
    if not sign_name:
        status_text = "IDLE (Press 'n' to setup Sign)"
        status_color = (0, 255, 255)

    cv2.putText(frame, f"Sign: {sign_name if sign_name else 'None'}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"Take: {take_number}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"Status: {status_text}", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
    
    if is_recording:
        cv2.circle(frame, (420, 110), 10, (0, 0, 255), -1) # লাল রেকর্ডিং ডট

    cv2.imshow("Smart Glove Vision AI", frame)
    
    # ================= কীবোর্ড কন্ট্রোল প্যানেল =================
    key = cv2.waitKey(1) & 0xFF
    
    # [N] - New Sign
    if key == ord('n'):
        print("\n[SYSTEM PAUSED] Look at the terminal!")
        sign_name = input(">>> Enter the Sign Name (e.g., Hello): ").strip().replace(" ", "_")
        take_number = 1
        print(f"[SET] Sign configured to: '{sign_name}'. Click on the Camera Window to continue.")
        
    # [R] - Record
    elif key == ord('r') and sign_name and not is_recording:
        is_recording = True
        recorded_data = []
        start_time = time.time()
        print(f"\n[RECORDING] Action! Show the sign for '{sign_name}'...")

    # [S] - Stop and Save
    elif key == ord('s') and is_recording:
        is_recording = False
        duration = round(time.time() - start_time, 2)
        filename = f"dataset_{sign_name}_take_{take_number}.csv"
        
        # র‍্যাম থেকে ফাইলে সেভ করা
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(recorded_data)
            
        print(f"[SAVED] {len(recorded_data)} rows saved to '{filename}' (Duration: {duration}s)")
        take_number += 1

    # [V] - Verify
    elif key == ord('v'):
        prev_take = take_number - 1
        filename = f"dataset_{sign_name}_take_{prev_take}.csv"
        if prev_take > 0 and os.path.exists(filename):
            print(f"\n[VERIFY] File '{filename}' exists. Size: {os.path.getsize(filename)/1024:.2f} KB")
        else:
            print("\n[VERIFY] No recent file found to verify.")

    # [D] - Delete
    elif key == ord('d') and take_number > 1:
        prev_take = take_number - 1
        filename = f"dataset_{sign_name}_take_{prev_take}.csv"
        if os.path.exists(filename):
            os.remove(filename)
            take_number -= 1
            print(f"\n[DELETED] Trash can icon! '{filename}' removed. You are back to take {take_number}.")
        else:
            print("\n[DELETED] File not found.")

    # [Q] - Quit
    elif key == ord('q'):
        print("\n[EXIT] Shutting down Smart System...")
        break

# ক্লিনআপ
cap.release()
cv2.destroyAllWindows()
if ser is not None:
    ser.close()
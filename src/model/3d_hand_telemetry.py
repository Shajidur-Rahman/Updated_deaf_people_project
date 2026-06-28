import serial
import time
import math
import numpy as np
from vpython import *

# ================= ১. সিরিয়াল পোর্ট সেটআপ =================
SERIAL_PORT = 'COM5'  # তোর পোর্ট
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"[SUCCESS] Connected to Smart Glove on {SERIAL_PORT}")
except Exception as e:
    print(f"[ERROR] Could not open port {SERIAL_PORT}. Check USB cable!")
    exit()

# ================= ২. ডাইনামিক ফ্লেক্স ক্যালিব্রেশন =================
flex_min = [1500] * 5  # ডিফল্ট সেফ ভ্যালু
flex_max = [3500] * 5  

def calibrate_glove():
    global flex_min, flex_max
    print("\n" + "="*50)
    print("🤖 CALIBRATION SYSTEM 🤖")
    print("="*50)
    
    print("\n[STEP 1] Keep your hand FULLY OPEN for 3 seconds...")
    time.sleep(3)
    ser.reset_input_buffer()
    
    samples = []
    for _ in range(20):
        try:
            line = ser.readline().decode('utf-8').strip()
            if "FLEX:" in line and "ACCEL:" in line:
                parts = line.split(' | ')
                flex_vals = list(map(int, parts[0].replace("FLEX:", "").split(',')))
                if len(flex_vals) == 5: samples.append(flex_vals)
        except: pass
        time.sleep(0.05)
    
    if samples:
        flex_min = np.mean(samples, axis=0).tolist()
        print(f"-> Open Values Saved: {[int(x) for x in flex_min]}")
    
    print("\n[STEP 2] Make a TIGHT FIST for 3 seconds...")
    time.sleep(3)
    ser.reset_input_buffer()
    
    samples = []
    for _ in range(20):
        try:
            line = ser.readline().decode('utf-8').strip()
            if "FLEX:" in line and "ACCEL:" in line:
                parts = line.split(' | ')
                flex_vals = list(map(int, parts[0].replace("FLEX:", "").split(',')))
                if len(flex_vals) == 5: samples.append(flex_vals)
        except: pass
        time.sleep(0.05)
        
    if samples:
        flex_max = np.mean(samples, axis=0).tolist()
        print(f"-> Fist Values Saved: {[int(x) for x in flex_max]}")
        
    print("\n[SUCCESS] Starting 3D Visualizer...\n")

calibrate_glove()

# ================= ৩. 3D ওয়ার্ল্ড সেটআপ (VPython) =================
scene = canvas(title='NeuroSign Hub - Live 3D Telemetry', width=800, height=600, background=color.black)
scene.camera.pos = vector(0, 0, 15)

# হাতের তালু
palm = box(pos=vector(0,0,0), size=vector(4, 4, 0.5), color=color.cyan)

# ৫টা আঙুল (সিলিন্ডার)
finger_x = [-1.6, -0.8, 0, 0.8, 1.6]
fingers = []
for i in range(5):
    f = cylinder(pos=vector(finger_x[i], 2, 0), axis=vector(0, 3, 0), radius=0.3, color=color.white)
    fingers.append(f)

print("[*] Waiting for live data stream...")
ser.reset_input_buffer()

# ================= ৪. রিয়েল-টাইম লুপ =================
while True:
    rate(60) # ৬০ FPS
    
    if ser.in_waiting > 0:
        try:
            # ডেটা রিড করা
            line = ser.readline().decode('utf-8').strip()
            if not line: continue
            
            # ডেটা ভ্যালিডেশন
            if "FLEX:" in line and "ACCEL:" in line:
                parts = line.split(' | ')
                flex_str = parts[0].replace("FLEX:", "").split(',')
                accel_str = parts[1].replace("ACCEL:", "").split(',')
                
                flex_vals = [int(x) for x in flex_str]
                ac_x, ac_y, ac_z = [float(x) for x in accel_str]
                
                # 📐 A. MPU6050: Raw Accel থেকে 3D অ্যাঙ্গেল বের করা
                # Math.atan2 রেডিয়ানে ভ্যালু দেয়, যা VPython-এর জন্য পারফেক্ট
                roll = math.atan2(ac_y, math.sqrt(ac_x**2 + ac_z**2))
                pitch = math.atan2(-ac_x, math.sqrt(ac_y**2 + ac_z**2))
                
                # টার্মিনালে প্রিন্ট করা (যাতে তুই বুঝিস ডেটা ঠিক আসছে)
                print(f"Live -> Roll: {math.degrees(roll):.0f}° | Pitch: {math.degrees(pitch):.0f}° | Flex: {flex_vals}")
                
                # হাতের তালু ঘোরানো (Absolute Rotation)
                palm.axis = vector(0, 4, 0) # ডিফল্ট উপর দিকে
                palm.up = vector(0, 0, 1)   # Z অক্ষ বরাবর মুখ
                
                palm.rotate(angle=roll, axis=vector(0,1,0)) # X-অক্ষে রোল
                palm.rotate(angle=-pitch, axis=vector(1,0,0)) # Y-অক্ষে পিচ
                
                # 📐 B. ফ্লেক্স সেন্সর: আঙুল কন্ট্রোল (Vector Math)
                # তালু যেদিকে ঘুরবে, আঙুলগুলো ঠিক সেদিকেই স্টিক হয়ে থাকবে
                right_vec = cross(palm.axis, palm.up).norm()
                
                for i in range(5):
                    # ফ্লেক্স ডেটাকে 1.0 (খোলা) থেকে 0.2 (বন্ধ) এ ম্যাপ করা
                    # এতে মুঠি করলে আঙুলগুলো গুটিয়ে ছোট হয়ে যাবে (ভিজ্যুয়াল হ্যাক)
                    curl_factor = np.interp(flex_vals[i], [flex_min[i], flex_max[i]], [1.0, 0.2])
                    curl_factor = max(0.2, min(1.0, curl_factor)) # সেফটি লিমিট
                    
                    # আঙুলের বেস পজিশন (তালুর টপ এজ অনুযায়ী)
                    base_offset = (finger_x[i] * right_vec) + (palm.axis * 0.5)
                    fingers[i].pos = palm.pos + base_offset
                    
                    # আঙুলের ডিরেকশন এবং সাইজ
                    fingers[i].axis = palm.axis * (0.7 * curl_factor)
                    
                    # মুঠি করলে আঙুলের রঙ লালচে হবে (অতিরিক্ত ভিজ্যুয়াল ফিডব্যাক)
                    red_val = np.interp(curl_factor, [0.2, 1.0], [1, 0])
                    fingers[i].color = vector(red_val, 1-red_val, 1-red_val)

        except Exception as e:
            # এবার আর সাইলেন্ট বাগ নেই! কোনো সমস্যা হলে সরাসরি টার্মিনালে দেখাবে।
            print(f"⚠️ Data Parsing Error: {e} | Raw Line: {line}")
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <XPT2046_Touchscreen.h> 

// ================= ১. পিন সেটআপ (ESP32-S3) =================
#define TFT_CS   10
#define TFT_DC   8
#define TFT_RST  9
#define TFT_MOSI 11
#define TFT_CLK  12
#define TFT_MISO 13
#define TOUCH_CS 7 

// কাস্টম SPI চ্যানেল
SPIClass *customSPI = new SPIClass(FSPI);
Adafruit_ILI9341 tft = Adafruit_ILI9341(customSPI, TFT_DC, TFT_CS, TFT_RST);
XPT2046_Touchscreen ts(TOUCH_CS); 

// ================= ২. গ্লোবাল ভেরিয়েবল =================
String currentSign = "Waiting...";
String currentVoice = "Waiting...";

// 🧠 স্মার্ট মোড কন্ট্রোলার (0 = Both, 1 = Sign Only, 2 = Voice Only)
int displayMode = 0; 
unsigned long lastTouchTime = 0;

void setup() {
  Serial.begin(115200);
  
  // কাস্টম SPI চালু করা
  customSPI->begin(TFT_CLK, TFT_MISO, TFT_MOSI, TFT_CS);
  delay(500); // হার্ডওয়্যার স্ট্যাবল হওয়ার জন্য সময়

  // ডিসপ্লে সেটআপ
  tft.begin();
  tft.setRotation(0); // পোট্রেট মোড
  
  // টাচ সেটআপ
  ts.begin(*customSPI); 
  ts.setRotation(0); 

  // ডাবল ক্লিয়ার (গার্বেজ মুছতে)
  tft.fillScreen(ILI9341_WHITE); 
  delay(100);
  tft.fillScreen(ILI9341_BLACK);

  drawMainScreen(); 
  Serial.println("System Ready! Waiting for Data & Touch...");
}

void loop() {
  // ================= ৩. পাইথন থেকে ডেটা রিসিভ (Serial) =================
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();

    // সাইন ডেটা ফিল্টার
    if (data.startsWith("SIGN:")) {
      String newSign = data.substring(5);
      if (newSign != currentSign) {
        currentSign = newSign;
        updateSignDisplay(); 
      }
    } 
    // ভয়েস ডেটা ফিল্টার
    else if (data.startsWith("VOICE:")) {
      String newVoice = data.substring(6);
      if (newVoice != currentVoice) {
        currentVoice = newVoice;
        updateVoiceDisplay();
      }
    }
  }

  // ================= ৪. ম্যাজিক টাচ কন্ট্রোল (Level 2 Ghost Killer) =================
  if (ts.touched()) { 
    // ১. ফেক স্পাইক (Ghost) রিড করে ফেলে দেওয়া
    TS_Point fakePoint = ts.getPoint(); 
    
    // ২. ২০ মিলি-সেকেন্ড অপেক্ষা করা (ভূত হলে এতক্ষণে গায়েব হয়ে যাবে)
    delay(20); 
    
    // ৩. ২০ms পরেও যদি টাচ হয়ে থাকে, তার মানে এটা আসল মানুষ!
    if (ts.touched()) {
      TS_Point p = ts.getPoint(); 
      
      // ৪. এক্সট্রিম প্রেসার চেক (১০০০ এর নিচে সব বাতিল)
      if (p.z > 1000) { 
        
        // ডিবাইন্স ডিলে (ডাবল ক্লিক ঠেকানোর জন্য)
        if (millis() - lastTouchTime > 500) { 
          lastTouchTime = millis();
          
          Serial.print("🎯 REAL Human Touch! Z: ");
          Serial.println(p.z);
          
          // মোড চেঞ্জ করা (0 -> 1 -> 2 -> 0)
          displayMode++;
          if (displayMode > 2) {
            displayMode = 0;
          }
          
          Serial.print("Mode Changed to: ");
          Serial.println(displayMode);

          // মোড চেঞ্জ হলে স্ক্রিন মুছে নতুন ডিজাইন লোড করা
          tft.fillScreen(ILI9341_BLACK);
          drawMainScreen();
        }
      }
    }
  }
}

// ================= ৫. UI DRAWING FUNCTIONS =================

void drawMainScreen() {
  // উপরের টাইটেল বার
  tft.fillRect(0, 0, 240, 45, tft.color565(0, 50, 100)); 
  tft.setTextColor(ILI9341_CYAN);
  tft.setTextSize(2);
  tft.setCursor(40, 15);
  tft.print("NeuroSign Hub");

  // মোড অনুযায়ী লেআউট ড্র করা
  if (displayMode == 0) {
    // Mode 0: Both (Sign + Voice)
    tft.setTextColor(ILI9341_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 60);
    tft.print("GLOVE DETECTED:");
    tft.drawLine(10, 135, 230, 135, ILI9341_DARKGREY); // মাঝখানের দাগ
    tft.setTextColor(ILI9341_GREEN);
    tft.setCursor(10, 150);
    tft.print("VOICE DETECTED:");
  } 
  else if (displayMode == 1) {
    // Mode 1: Sign Only (বড় করে)
    tft.setTextColor(ILI9341_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 80);
    tft.print("SIGN LANGUAGE:");
  } 
  else if (displayMode == 2) {
    // Mode 2: Voice Only (বড় করে)
    tft.setTextColor(ILI9341_GREEN);
    tft.setTextSize(2);
    tft.setCursor(10, 80);
    tft.print("VOICE TEXT:");
  }

  // ডেটা আপডেট করা
  updateSignDisplay();
  updateVoiceDisplay();

  // নিচের ইনস্ট্রাকশন
  tft.setTextColor(ILI9341_DARKGREY);
  tft.setTextSize(1);
  tft.setCursor(35, 300);
  tft.print("Tap and hold to change mode");
}

void updateSignDisplay() {
  // যদি ভয়েস অনলি মোডে থাকে, সাইন রেন্ডার হবে না
  if (displayMode == 2) return; 

  int yPos = (displayMode == 0) ? 90 : 120; 
  int textSize = (displayMode == 0) ? 3 : 4; 

  // আগের লেখা মোছার জন্য কালো বক্স
  tft.fillRect(10, yPos - 5, 220, 45, ILI9341_BLACK); 
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(textSize); 
  tft.setCursor(10, yPos);
  tft.print(currentSign);
}

void updateVoiceDisplay() {
  // যদি সাইন অনলি মোডে থাকে, ভয়েস রেন্ডার হবে না
  if (displayMode == 1) return; 

  int yPos = (displayMode == 0) ? 180 : 120;
  int textSize = (displayMode == 0) ? 2 : 3; 

  // আগের লেখা মোছার জন্য কালো বক্স
  tft.fillRect(10, yPos - 5, 220, 50, ILI9341_BLACK); 
  tft.setTextColor(ILI9341_LIGHTGREY);
  tft.setTextSize(textSize); 
  tft.setCursor(10, yPos);
  tft.print(currentVoice);
}
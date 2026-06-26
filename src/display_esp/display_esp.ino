#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <XPT2046_Touchscreen.h> // টাচের লাইব্রেরি

// ডিসপ্লে ও টাচের পিন সেটআপ (তোর ESP32-S3 এর জন্য)
#define TFT_CS   10
#define TFT_DC   8
#define TFT_RST  9
#define TFT_MOSI 11
#define TFT_CLK  12
#define TFT_MISO 13

#define TOUCH_CS 7  // টাচের চিপ সিলেক্ট পিন

// কাস্টম SPI চ্যানেল (ESP32-S3 এর জন্য)
SPIClass *customSPI = new SPIClass(FSPI);
Adafruit_ILI9341 tft = Adafruit_ILI9341(customSPI, TFT_DC, TFT_CS, TFT_RST);
XPT2046_Touchscreen ts(TOUCH_CS); // টাচ কন্ট্রোলার

String currentSign = "Waiting...";
String currentVoice = "Waiting...";

// UI State Control (0 = Main Screen, 1 = About Screen)
int currentUIState = 0; 
unsigned long lastTouchTime = 0;

void setup() {
  Serial.begin(115200);
  
  // কাস্টম SPI চালু করা
  customSPI->begin(TFT_CLK, TFT_MISO, TFT_MOSI, TFT_CS);

  // 🚀 হার্ডওয়্যার স্ট্যাবল হওয়ার জন্য একটু সময় দেওয়া
  delay(500); 

  // ডিসপ্লে সেটআপ
  tft.begin();
  tft.setRotation(0); // পোট্রেট মোড (লম্বালম্বি)
  
  // টাচ সেটআপ
  ts.begin(*customSPI); 
  ts.setRotation(0); // ডিসপ্লের সাথে টাচের রোটেশন ম্যাচ করানো

  // 🚀 গার্বেজ বা ঝিরঝিরে দাগ মুছতে ডাবল ক্লিয়ার
  tft.fillScreen(ILI9341_WHITE); 
  delay(100);
  tft.fillScreen(ILI9341_BLACK);

  drawMainScreen(); // মেইন ডিজাইন লোড
  Serial.println("System Ready! Waiting for Touch...");
}

void loop() {
  // ================= ১. এআই ব্রেইন থেকে ডেটা রিসিভ করা =================
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();

    if (data.startsWith("SIGN:")) {
      String newSign = data.substring(5);
      if (newSign != currentSign) {
        currentSign = newSign;
        if (currentUIState == 0) updateSignDisplay(); 
      }
    } 
    else if (data.startsWith("VOICE:")) {
      currentVoice = data.substring(6);
      if (currentUIState == 0) updateVoiceDisplay();
    }
  }

  // ================= ২. টাচ রেসপন্স হ্যান্ডেল করা (With Serial Debugging) =================
  if (ts.touched()) { 
    
    if (millis() - lastTouchTime > 300) { // 300ms ডিবাইন্স ডিলে
      TS_Point p = ts.getPoint();
      lastTouchTime = millis();
      
      // 🚀 সিরিয়াল মনিটরে টাচের ডেটা প্রিন্ট করা (চেক করার জন্য)
      Serial.print("🎯 Touch Detected! X: "); 
      Serial.print(p.x);
      Serial.print(" | Y: "); 
      Serial.println(p.y);

      // পোট্রেট মোডের জন্য টাচ ক্যালিব্রেশন (Width: 240, Height: 320)
      int touchX = map(p.x, 200, 3800, 0, 240); 
      int touchY = map(p.y, 200, 3800, 0, 320);

      if (currentUIState == 0) { // মেইন স্ক্রিন
        // "CLEAR" বাটন চেক (X: 10 to 110, Y: 260 to 300)
        if (touchX > 10 && touchX < 110 && touchY > 260 && touchY < 300) {
          Serial.println("-> CLEAR Button Pressed!");
          currentSign = "Waiting...";
          currentVoice = "Waiting...";
          updateSignDisplay();
          updateVoiceDisplay();
          drawButton(10, 260, 100, 40, "DONE!", ILI9341_GREEN, ILI9341_BLACK); 
          delay(200);
          drawButton(10, 260, 100, 40, "CLEAR", ILI9341_RED, ILI9341_WHITE);
        }
        // "ABOUT" বাটন চেক (X: 130 to 230, Y: 260 to 300)
        else if (touchX > 130 && touchX < 230 && touchY > 260 && touchY < 300) {
          Serial.println("-> ABOUT Button Pressed!");
          currentUIState = 1;
          drawAboutScreen();
        }
      } 
      else if (currentUIState == 1) { // About স্ক্রিন
        // "BACK" বাটন চেক (X: 60 to 180, Y: 260 to 300)
        if (touchX > 60 && touchX < 180 && touchY > 260 && touchY < 300) {
          Serial.println("-> BACK Button Pressed!");
          currentUIState = 0;
          tft.fillScreen(ILI9341_BLACK);
          drawMainScreen();
        }
      }
    }
  }
}

// ================= UI DRAWING FUNCTIONS (Portrait 240x320) =================

void drawMainScreen() {
  tft.fillRect(0, 0, 240, 45, tft.color565(0, 50, 100)); 
  tft.setTextColor(ILI9341_CYAN);
  tft.setTextSize(2);
  tft.setCursor(40, 15);
  tft.print("NeuroSign Hub");

  tft.setTextColor(ILI9341_YELLOW);
  tft.setTextSize(2);
  tft.setCursor(10, 60);
  tft.print("GLOVE DETECTED:");
  
  tft.drawLine(10, 135, 230, 135, ILI9341_DARKGREY); 
  
  tft.setTextColor(ILI9341_GREEN);
  tft.setCursor(10, 150);
  tft.print("VOICE DETECTED:");

  updateSignDisplay();
  updateVoiceDisplay();

  // বাটন ড্র করা
  drawButton(10, 260, 100, 40, "CLEAR", ILI9341_RED, ILI9341_WHITE);
  drawButton(130, 260, 100, 40, "ABOUT", ILI9341_BLUE, ILI9341_WHITE);
}

void drawAboutScreen() {
  tft.fillScreen(ILI9341_NAVY); 
  
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(3);
  tft.setCursor(45, 30);
  tft.print("NeuroSign");
  
  tft.setTextSize(1);
  tft.setCursor(25, 70);
  tft.print("Embedded Communication Ecosystem");

  tft.setTextColor(ILI9341_CYAN);
  tft.setTextSize(1);
  tft.setCursor(20, 110);
  tft.print("> Edge AI Powered");
  tft.setCursor(20, 140);
  tft.print("> Two-way Comm.");
  tft.setCursor(20, 170);
  tft.print("> Offline System");

  drawButton(60, 260, 120, 40, "BACK", ILI9341_DARKGREY, ILI9341_WHITE);
}

void updateSignDisplay() {
  tft.fillRect(10, 85, 220, 45, ILI9341_BLACK); 
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(3); 
  tft.setCursor(10, 95);
  tft.print(currentSign);
}

void updateVoiceDisplay() {
  tft.fillRect(10, 175, 220, 50, ILI9341_BLACK); 
  tft.setTextColor(ILI9341_LIGHTGREY);
  tft.setTextSize(2); 
  tft.setCursor(10, 185);
  tft.print(currentVoice);
}

void drawButton(int x, int y, int w, int h, const char* label, uint16_t bgColor, uint16_t textColor) {
  tft.fillRoundRect(x, y, w, h, 8, bgColor);
  tft.drawRoundRect(x, y, w, h, 8, ILI9341_WHITE);
  
  tft.setTextColor(textColor);
  tft.setTextSize(2);
  
  int textLen = strlen(label) * 12; 
  int textX = x + (w - textLen) / 2;
  int textY = y + (h - 16) / 2; 
  
  tft.setCursor(textX, textY);
  tft.print(label);
}
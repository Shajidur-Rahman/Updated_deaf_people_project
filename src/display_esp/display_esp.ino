#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>

// তোর চেক করা 100% ওয়ার্কিং পিনগুলো
#define TFT_CS   10
#define TFT_DC   8
#define TFT_RST  9
#define TFT_MOSI 11
#define TFT_CLK  12
#define TFT_MISO 13

// ESP32-S3 এর জন্য কাস্টম SPI চ্যানেল 
SPIClass *customSPI = new SPIClass(FSPI);
Adafruit_ILI9341 tft = Adafruit_ILI9341(customSPI, TFT_DC, TFT_CS, TFT_RST);

String currentSign = "Waiting...";
String currentVoice = "Waiting for voice...";

void setup() {
  Serial.begin(115200);
  
  // জোর করে পিন সেটআপ করা
  customSPI->begin(TFT_CLK, TFT_MISO, TFT_MOSI, TFT_CS);

  tft.begin();
  tft.setRotation(1); // ল্যান্ডস্কেপ মোড

  tft.fillScreen(ILI9341_BLACK);
  drawSmartUI(); // মেইন ডিজাইন লোড
}

void loop() {
  // পাইথন (এআই ব্রেইন) থেকে ডেটা রিসিভ করা
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();

    if (data.startsWith("SIGN:")) {
      String newSign = data.substring(5);
      if (newSign != currentSign) {
        currentSign = newSign;
        updateSignDisplay();
      }
    } 
    else if (data.startsWith("VOICE:")) {
      currentVoice = data.substring(6);
      updateVoiceDisplay();
    }
  }
}

// 🎨 ইউজার ইন্টারফেস ডিজাইন (UI)
void drawSmartUI() {
  // ওপরের টাইটেল বার (গাঢ় নীল)
  tft.fillRect(0, 0, 320, 45, tft.color565(0, 50, 100)); 
  tft.setTextColor(ILI9341_CYAN);
  tft.setTextSize(3);
  tft.setCursor(10, 10);
  tft.print("AI SMART GLOVE");

  // সাইন রেজাল্ট সেকশন
  tft.setTextColor(ILI9341_YELLOW);
  tft.setTextSize(2);
  tft.setCursor(10, 60);
  tft.print("GLOVE SIGN DETECTED:");
  
  // মাঝখানের ডিভাইডার লাইন
  tft.drawLine(10, 150, 310, 150, ILI9341_DARKGREY); 
  
  // ভয়েস রেজাল্ট সেকশন
  tft.setTextColor(ILI9341_GREEN);
  tft.setCursor(10, 170);
  tft.print("VOICE DETECTED:");

  // ডিফল্ট টেক্সটগুলো প্রিন্ট করা
  updateSignDisplay();
  updateVoiceDisplay();
}

// 🖐️ সাইন টেক্সট আপডেট ফাংশন
void updateSignDisplay() {
  // আগের লেখাটা কালো রঙ দিয়ে মুছে ফেলা (Refresh)
  tft.fillRect(10, 85, 300, 50, ILI9341_BLACK); 
  
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(4); // সাইনের লেখাটা অনেক বড় হবে
  tft.setCursor(10, 95);
  tft.print(currentSign);
}

// 🗣️ ভয়েস টেক্সট আপডেট ফাংশন
void updateVoiceDisplay() {
  // আগের ভয়েসটা কালো রঙ দিয়ে মুছে ফেলা (Refresh)
  tft.fillRect(10, 195, 300, 40, ILI9341_BLACK); 
  
  tft.setTextColor(ILI9341_LIGHTGREY);
  tft.setTextSize(2); // ভয়েসের লেখা মাঝারি হবে
  tft.setCursor(10, 200);
  tft.print(currentVoice);
}
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <Adafruit_SSD1306.h>
#include <XPT2046_Touchscreen.h> 

// ================= ১. পিন সেটআপ =================
#define TFT_CS   10
#define TFT_DC   8
#define TFT_RST  9
#define TFT_MOSI 11
#define TFT_CLK  12
#define TFT_MISO 13
#define TOUCH_CS 7 
#define OLED_SDA 4 
#define OLED_SCL 5 

// ডিসপ্লে অবজেক্টস
SPIClass *customSPI = new SPIClass(FSPI);
Adafruit_ILI9341 tft = Adafruit_ILI9341(customSPI, TFT_DC, TFT_CS, TFT_RST);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
XPT2046_Touchscreen ts(TOUCH_CS); 

String currentSign = "Waiting...";
String currentVoice = "Waiting...";
int displayMode = 0; 
unsigned long lastTouchTime = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(OLED_SDA, OLED_SCL);
  customSPI->begin(TFT_CLK, TFT_MISO, TFT_MOSI, TFT_CS);
  
  tft.begin();
  tft.setRotation(0);
  ts.begin(*customSPI); 
  ts.setRotation(0);
  
  // OLED ইনিশিয়ালাইজ
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  oled.clearDisplay();
  oled.display();
  
  tft.fillScreen(ILI9341_BLACK);
  drawMainScreen(); 
  Serial.println("System Ready! Waiting for Data...");
}

void loop() {
  // সিরিয়াল ডেটা রিসিভ
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();

    if (data.startsWith("SIGN:")) {
      String newSign = data.substring(5);
      if (newSign != currentSign) {
        currentSign = newSign;
        updateSignDisplay(); 
        
        // OLED আপডেট (শুধু টেক্সট)
        oled.clearDisplay();
        oled.setTextSize(2);
        oled.setTextColor(SSD1306_WHITE);
        oled.setCursor(0, 0);
        oled.println("SIGN:");
        oled.println(currentSign);
        oled.display();
      }
    } 
    else if (data.startsWith("VOICE:")) {
      String newVoice = data.substring(6);
      if (newVoice != currentVoice) {
        currentVoice = newVoice;
        updateVoiceDisplay();
      }
    }
  }

  // টাচ হ্যান্ডেলিং
  if (ts.touched()) { 
    delay(20); 
    if (ts.touched() && ts.getPoint().z > 1000) {
      if (millis() - lastTouchTime > 500) { 
        lastTouchTime = millis();
        displayMode = (displayMode + 1) % 3;
        tft.fillScreen(ILI9341_BLACK);
        drawMainScreen();
      }
    }
  }
}

// ================= UI DRAWING FUNCTIONS =================
void drawMainScreen() {
  tft.fillRect(0, 0, 240, 45, tft.color565(0, 50, 100)); 
  tft.setTextColor(ILI9341_CYAN);
  tft.setTextSize(2);
  tft.setCursor(40, 15);
  tft.print("NeuroSign Hub");

  if (displayMode == 0) {
    tft.setTextColor(ILI9341_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 60);
    tft.print("GLOVE DETECTED:");
    tft.drawLine(10, 135, 230, 135, ILI9341_DARKGREY);
    tft.setTextColor(ILI9341_GREEN);
    tft.setCursor(10, 150);
    tft.print("VOICE DETECTED:");
  } 
  else if (displayMode == 1) {
    tft.setTextColor(ILI9341_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 80);
    tft.print("SIGN LANGUAGE:");
  } 
  else if (displayMode == 2) {
    tft.setTextColor(ILI9341_GREEN);
    tft.setTextSize(2);
    tft.setCursor(10, 80);
    tft.print("VOICE TEXT:");
  }
  updateSignDisplay();
  updateVoiceDisplay();
}

void updateSignDisplay() {
  if (displayMode == 2) return; 
  int yPos = (displayMode == 0) ? 90 : 120; 
  tft.fillRect(10, yPos - 5, 220, 45, ILI9341_BLACK); 
  tft.setTextColor(ILI9341_WHITE);
  tft.setTextSize(3);
  tft.setCursor(10, yPos);
  tft.print(currentSign);
}

void updateVoiceDisplay() {
  if (displayMode == 1) return; 
  int yPos = (displayMode == 0) ? 180 : 120;
  int textSize = (displayMode == 0) ? 2 : 3; 
  tft.fillRect(10, yPos - 5, 220, 50, ILI9341_BLACK); 
  tft.setTextColor(ILI9341_LIGHTGREY);
  tft.setTextSize(textSize);
  tft.setCursor(10, yPos);
  tft.print(currentVoice);
}
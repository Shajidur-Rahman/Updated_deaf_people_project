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

// বিটম্যাপ অ্যারে (তোমার ৭টি ছবির কোড এখানে বসাও)
const unsigned char epd_bitmap_salam[] PROGMEM = { help.cpp };
const unsigned char epd_bitmap_help[] PROGMEM = { help.cpp };
const unsigned char epd_bitmap_food[] PROGMEM = { food.cpp };
const unsigned char epd_bitmap_yes[] PROGMEM = { /* yes.cpp */ };
const unsigned char epd_bitmap_no[] PROGMEM = { /* no.cpp */ };
const unsigned char epd_bitmap_water[] PROGMEM = { /* water.cpp */ };
const unsigned char epd_bitmap_victory[] PROGMEM = { /* victory.cpp */ };

SPIClass *customSPI = new SPIClass(FSPI);
Adafruit_ILI9341 tft = Adafruit_ILI9341(customSPI, TFT_DC, TFT_CS, TFT_RST);
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
XPT2046_Touchscreen ts(TOUCH_CS); 

String currentSign = "Waiting...", currentVoice = "Waiting...";
int displayMode = 0; 
unsigned long lastTouchTime = 0;

void showOLEDImage(const unsigned char* bitmap) {
  oled.clearDisplay();
  oled.drawBitmap(0, 0, bitmap, 128, 64, 1);
  oled.display();
}

void updateOLED() {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0, 0);
  oled.setTextSize(1);
  oled.println("VOICE:");
  oled.setTextSize(2);
  oled.println(currentVoice);
  oled.display();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(OLED_SDA, OLED_SCL);
  customSPI->begin(TFT_CLK, TFT_MISO, TFT_MOSI, TFT_CS);
  tft.begin();
  tft.setRotation(0);
  ts.begin(*customSPI); 
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  oled.clearDisplay();
  oled.display();
  tft.fillScreen(ILI9341_BLACK);
  drawMainScreen(); 
}

void loop() {
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();
    if (data.startsWith("SIGN:")) {
      currentSign = data.substring(5);
      updateSignDisplay(); 
    } else if (data.startsWith("VOICE:")) {
      currentVoice = data.substring(6);
      updateVoiceDisplay();
      // ইমেজ লজিক
      if (currentVoice == "salam") showOLEDImage(epd_bitmap_salam);
      else if (currentVoice == "help") showOLEDImage(epd_bitmap_help);
      else if (currentVoice == "food") showOLEDImage(epd_bitmap_food);
      else if (currentVoice == "yes") showOLEDImage(epd_bitmap_yes);
      else if (currentVoice == "no") showOLEDImage(epd_bitmap_no);
      else if (currentVoice == "water") showOLEDImage(epd_bitmap_water);
      else if (currentVoice == "victory") showOLEDImage(epd_bitmap_victory);
      else updateOLED();
    }
  }
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

void drawMainScreen() {
  tft.fillRect(0, 0, 240, 45, tft.color565(0, 50, 100)); 
  tft.setTextColor(ILI9341_CYAN);
  tft.setTextSize(2);
  tft.setCursor(40, 15);
  tft.print("NeuroSign Hub");
  updateSignDisplay(); updateVoiceDisplay();
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
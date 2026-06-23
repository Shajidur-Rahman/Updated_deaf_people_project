#include <Arduino.h>

void setup() {
  // সিরিয়াল কমিউনিকেশন চালু করলাম ৪০০ মেগাহার্টজের এই দানবের জন্য!
  Serial.begin(115200);
  delay(2000); // বোর্ডটা একটু থিতু হওয়ার জন্য সময় দিলাম
  
  Serial.println("====================================");
  Serial.println("   ESP32-P4 INITIALIZATION SUCCESS   ");
  Serial.println("====================================");
}

void loop() {
  // প্রতি ১ সেকেন্ড পর পর সিরিয়াল মনিটরে প্রিন্ট হবে
  Serial.print("Hello Boss! ESP32-P4 is Alive! | Core: ");
  Serial.print(xPortGetCoreID()); // কোন কোরে রান হচ্ছে তাও দেখে নিলাম
  Serial.print(" | Uptime: ");
  Serial.print(millis() / 1000);
  Serial.println("s");
  
  delay(1000); 
}
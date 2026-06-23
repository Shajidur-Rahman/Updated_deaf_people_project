#include <Arduino.h>
#include <Wire.h>

// ফ্লেক্স সেন্সরের অ্যানালগ পিনগুলো
const int flexPins[5] = {14, 5, 6, 7, 15};

// MPU6050 এর কাস্টম I2C পিন ও অ্যাড্রেস
#define I2C_SDA 8
#define I2C_SCL 9
const int MPU_ADDR = 0x68; 

int16_t AcX, AcY, AcZ, Tmp, GyX, GyY, GyZ;

void setup() {
  Serial.begin(115200);
  delay(2000); 
  
  Serial.println("\n=== SMART GLOVE SYSTEM INITIALIZING ===");

  // কাস্টম পিন দিয়ে I2C লাইন চালু করা
  Wire.begin(I2C_SDA, I2C_SCL);

  // MPU6050 কে ঘুম থেকে জাগানোর (Wake-Up) ডিরেক্ট কমান্ড
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);  // PWR_MGMT_1 রেজিস্টার
  Wire.write(0);     // 0 পাঠিয়ে সেন্সর অন করা হলো
  byte error = Wire.endTransmission();

  if (error == 0) {
    Serial.println("[SUCCESS] MPU6050 Woken Up via Raw I2C!");
  } else {
    Serial.println("[ERROR] Check wiring again!");
    while (1) { delay(10); } 
  }

  // ফ্লেক্স সেন্সর পিনগুলোকে ইনপুট হিসেবে সেট করা
  for (int i = 0; i < 5; i++) {
    pinMode(flexPins[i], INPUT);
  }
  
  Serial.println("=== SYSTEM READY. STREAMING DATA ===");
  delay(1000);
}

void loop() {
  // ১. ফ্লেক্স সেন্সরের ডেটা রিড করা
  int flexValues[5];
  for (int i = 0; i < 5; i++) {
    flexValues[i] = analogRead(flexPins[i]);
  }

  // ২. MPU6050 থেকে ডেটা টেনে আনা (ডিরেক্ট রেজিস্টার রিড)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);  // 0x3B (ACCEL_XOUT_H) থেকে পড়া শুরু
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true); // মোট ১৪ বাইট ডেটা রিকোয়েস্ট

  AcX = Wire.read()<<8 | Wire.read(); 
  AcY = Wire.read()<<8 | Wire.read(); 
  AcZ = Wire.read()<<8 | Wire.read(); 
  Tmp = Wire.read()<<8 | Wire.read(); // টেম্পারেচার (চাইলে বাদ দেওয়া যায়)
  GyX = Wire.read()<<8 | Wire.read(); 
  GyY = Wire.read()<<8 | Wire.read(); 
  GyZ = Wire.read()<<8 | Wire.read(); 

  // ৩. সিরিয়াল মনিটরে এক লাইনে প্রিন্ট করা
  Serial.print("FLEX:");
  for (int i = 0; i < 5; i++) {
    Serial.print(flexValues[i]);
    if (i < 4) Serial.print(",");
  }

  Serial.print(" | ACCEL:");
  Serial.print(AcX); Serial.print(",");
  Serial.print(AcY); Serial.print(",");
  Serial.print(AcZ);

  Serial.print(" | GYRO:");
  Serial.print(GyX); Serial.print(",");
  Serial.print(GyY); Serial.print(",");
  Serial.println(GyZ); 

  delay(500); // একটু ডিলে (যাতে মনিটরে ডেটা পড়ার সময় পাস)
}
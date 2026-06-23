#include <Arduino.h>
#include <Wire.h>
#include <driver/i2s_std.h>

// Waveshare ESP32-P4 NANO অফিশিয়াল পিনম্যাপ
#define I2S_MCLK_IO      (gpio_num_t)13
#define I2S_BCLK_IO      (gpio_num_t)12
#define I2S_DOUT_IO      (gpio_num_t)11
#define I2S_WS_IO        (gpio_num_t)10

#define I2C_SDA          7
#define I2C_SCL          8
#define ES8311_ADDR      0x18 

i2s_chan_handle_t tx_handle = NULL;

void es8311_write_reg(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(ES8311_ADDR);
    Wire.write(reg);
    Wire.write(val);
    Wire.endTransmission();
}

// ES8311-এর একদম ডিপ লেভেল স্পিকার ড্রাইভার অ্যাক্টিভেশন
void init_es8311_hardware_final() {
    Wire.begin(I2C_SDA, I2C_SCL, 100000);
    delay(100);

    Serial.println("[INFO] Forcing ES8311 Speaker Driver Online...");
    
    es8311_write_reg(0x00, 0x80); // Reset
    delay(50);
    es8311_write_reg(0x00, 0x00); // Normal State
    
    es8311_write_reg(0x01, 0x30); // En MCLK
    es8311_write_reg(0x02, 0x00); // Digital filter clock
    
    // I2S Standard Mode Setup (16-bit)
    es8311_write_reg(0x03, 0x10); 
    es8311_write_reg(0x04, 0x10); 
    es8311_write_reg(0x05, 0x00); 
    es8311_write_reg(0x06, 0x00); 
    
    // Power & Mixer Management - স্পিকার এবং ড্যাক ফুল পাওয়ার অন
    es8311_write_reg(0x0C, 0x00); // Analog Power On
    es8311_write_reg(0x0D, 0x02); // DAC Power On
    es8311_write_reg(0x0E, 0x0F); // Enable Mixers
    es8311_write_reg(0x12, 0x00); // Unmute DAC
    
    // ভলিউম কন্ট্রোল (0xBF = 0dB Max Volume)
    es8311_write_reg(0x13, 0xBF); 
    es8311_write_reg(0x14, 0xBF); 
    
    // !!! এই দুইটা রেজিস্টারই স্পিকারের ইন্টারনাল Class-D Amp অন করে !!!
    es8311_write_reg(0x15, 0x20); // Control Speaker Driver Output Gain
    es8311_write_reg(0x1B, 0xA0); // Class-D Speaker Power Amp Enable
    
    Serial.println("[SUCCESS] Speaker Hardware Registers Fully Armed!");
}

void init_i2s_clock_final() {
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    i2s_new_channel(&chan_cfg, &tx_handle, NULL);

    i2s_std_config_t std_cfg = {
        .clk_cfg = {
            .sample_rate_hz = 44100,
            .clk_src = I2S_CLK_SRC_DEFAULT, // আর্ডুইনোর ইন্টারনাল ক্লক সোর্স লক করলাম
            .mclk_multiple = I2S_MCLK_MULTIPLE_256
        },
        .slot_cfg = I2S_STD_MSB_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO), 
        .gpio_cfg = {
            .mclk = I2S_MCLK_IO, 
            .bclk = I2S_BCLK_IO,
            .ws = I2S_WS_IO,
            .dout = I2S_DOUT_IO,
            .din = I2S_GPIO_UNUSED,
            .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false }
        }
    };
    i2s_channel_init_std_mode(tx_handle, &std_cfg);
    i2s_channel_enable(tx_handle);
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    // স্পিকার এনাবল করার জন্য যদি কোনো পিন বাকি থাকে (নিরাপত্তার জন্য জিপিআইও ৫৩ ও ২৬ হাই করে রাখলাম)
    pinMode(53, OUTPUT); digitalWrite(53, HIGH);
    pinMode(26, OUTPUT); digitalWrite(26, HIGH);
    delay(200);
    
    init_es8311_hardware_final();
    init_i2s_clock_final();
    
    Serial.println("\n=== CRITICAL SPEAKER FIXED CODE ONLINE ===");
}

void loop() {
    size_t bytes_written;
    int16_t samples[200]; 
    
    // হাই-পিচ বিপ সাউন্ড তৈরি করলাম
    for (int i = 0; i < 200; i++) {
        samples[i] = (int16_t)(32000 * sin(i * 2 * PI / 15)); 
    }

    Serial.println("[AUDIO] Pumping Data into ES8311 Codec...");
    for(int duration = 0; duration < 800; duration++) {
        i2s_channel_write(tx_handle, samples, sizeof(samples), &bytes_written, portMAX_DELAY);
    }
    
    Serial.println("[AUDIO] Intermission...");
    delay(1500); 
}
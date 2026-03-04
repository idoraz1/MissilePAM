#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <HardwareSerial.h>
#include "DFRobotDFPlayerMini.h"

// ── הגדרות רשת ──
const char* ssid          = "YOUR_WIFI_SSID";     // צונזר: הכנס את שם הרשת שלך כאן
const char* password      = "YOUR_WIFI_PASSWORD"; // צונזר: הכנס את סיסמת ה-Wi-Fi שלך כאן
const char* statusUrl     = "http://YOUR_LOCAL_IP:5000/api/status"; // צונזר: הכנס את ה-IP המקומית
const char* espCommandUrl = "http://YOUR_LOCAL_IP:5000/api/esp_command"; // צונזר: הכנס את ה-IP המקומית
const char* espConfigUrl  = "http://YOUR_LOCAL_IP:5000/api/esp_config"; // צונזר: הכנס את ה-IP המקומית

// ── LED מובנה ──
const int LED_PIN = 2;

// ── DFPlayer ──
HardwareSerial mySoftwareSerial(2);
DFRobotDFPlayerMini myDFPlayer;
bool isMp3Ready = false;
bool inAlert    = false;

// ── ווליומים (ברירות מחדל — יתעדכנו מהשרת) ──
int volAlert    = 30;
int volUav      = 30;
int volEarly    = 25;
int volAllClear = 20;
int volStartup  = 20;

// ── מיפוי קבצים (ברירות מחדל) ──
int fileAlertImmediate = 1;
int fileAllClear       = 2;
int fileStartup        = 3;
int fileUav            = 4;
int fileAlertEarly     = 5;

// ══════════════════════════════════════════
//  ניגון קובץ
// ══════════════════════════════════════════
void playFile(int fileNum, int volume) {
    if (!isMp3Ready) {
        Serial.println("[WARN] DFPlayer לא מוכן");
        return;
    }
    myDFPlayer.volume(volume);
    delay(150);
    myDFPlayer.playMp3Folder(fileNum);
    Serial.printf("[MP3] ▶ קובץ %04d.mp3 | ווליום %d\n", fileNum, volume);
}

// ══════════════════════════════════════════
//  LED
// ══════════════════════════════════════════
void heartbeatBlink() {
    digitalWrite(LED_PIN, HIGH); delay(50);
    digitalWrite(LED_PIN, LOW);
}

void alertBlink() {
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_PIN, HIGH); delay(80);
        digitalWrite(LED_PIN, LOW);  delay(80);
    }
}

// ══════════════════════════════════════════
//  טעינת קונפיג ESP32 מהשרת
//  (ווליומים + מיפוי קבצים)
// ══════════════════════════════════════════
void fetchEspConfig() {
    HTTPClient http;
    http.begin(espConfigUrl);
    http.setTimeout(4000);
    int code = http.GET();

    if (code == HTTP_CODE_OK) {
        String body = http.getString();
        StaticJsonDocument<512> doc;

        if (!deserializeJson(doc, body)) {
            // ווליומים
            volAlert    = doc["volume_alert"]     | volAlert;
            volUav      = doc["volume_uav"]       | volUav;
            volEarly    = doc["volume_early"]     | volEarly;
            volAllClear = doc["volume_all_clear"] | volAllClear;
            volStartup  = doc["volume_startup"]   | volStartup;

            // מיפוי קבצים
            fileAlertImmediate = doc["file_alert_immediate"] | fileAlertImmediate;
            fileAllClear       = doc["file_all_clear"]       | fileAllClear;
            fileStartup        = doc["file_startup"]         | fileStartup;
            fileUav            = doc["file_uav"]             | fileUav;
            fileAlertEarly     = doc["file_alert_early"]     | fileAlertEarly;

            Serial.println("[CONFIG] קונפיג ESP32 עודכן מהשרת:");
            Serial.printf("  ווליום אזעקה=%d | כטב\"מ=%d | מוקדמת=%d | שגרה=%d | פתיחה=%d\n",
                volAlert, volUav, volEarly, volAllClear, volStartup);
            Serial.printf("  קבצים: אזעקה=%d | שגרה=%d | פתיחה=%d | כטב\"מ=%d | מוקדמת=%d\n",
                fileAlertImmediate, fileAllClear, fileStartup, fileUav, fileAlertEarly);
        } else {
            Serial.println("[CONFIG] שגיאת פענוח JSON");
        }
    } else {
        Serial.printf("[CONFIG] שגיאת HTTP %d — משתמש בברירות מחדל\n", code);
    }
    http.end();
}

// ══════════════════════════════════════════
//  בדיקת פקודות ידניות מהאתר (one-shot)
// ══════════════════════════════════════════
void checkEspCommand() {
    HTTPClient http;
    http.begin(espCommandUrl);
    http.setTimeout(3000);
    int code = http.GET();

    if (code == HTTP_CODE_OK) {
        String body = http.getString();
        StaticJsonDocument<256> doc;

        if (!deserializeJson(doc, body)) {
            String cmd = doc["command"] | "idle";
            if (cmd == "play") {
                int fileNum = doc["file"]   | 1;
                int vol     = doc["volume"] | 25;
                Serial.printf("[CMD] פקודת בדיקה: קובץ %d | ווליום %d\n", fileNum, vol);
                playFile(fileNum, vol);
            }
        } else {
            Serial.println("[CMD] שגיאת פענוח JSON");
        }
    } else {
        Serial.printf("[CMD] שגיאת HTTP %d\n", code);
    }
    http.end();
}

// ══════════════════════════════════════════
//  בדיקת סטטוס התרעות
// ══════════════════════════════════════════
void checkStatus() {
    HTTPClient http;
    http.begin(statusUrl);
    http.setTimeout(3000);
    int code = http.GET();

    if (code == HTTP_CODE_OK) {
        String body = http.getString();
        StaticJsonDocument<1024> doc;
        heartbeatBlink();

        if (!deserializeJson(doc, body)) {
            String status    = doc["status"]     | "0";
            String alertType = doc["alert_type"] | "";

            Serial.printf("[STATUS] %s | סוג: %s\n", status.c_str(), alertType.c_str());

            // ── אזעקה ──
            if (status == "1") {
                if (!inAlert) {
                    inAlert = true;
                    alertBlink();
                    Serial.println(">>> אזעקה! <<<");

                    if (alertType.indexOf("התרעה מקדימה") >= 0) {
                        playFile(fileAlertEarly, volEarly);
                    } else if (alertType.indexOf("כטבם")     >= 0 ||
                               alertType.indexOf("כלי טיס")  >= 0 ||
                               alertType.indexOf("UAV")       >= 0) {
                        playFile(fileUav, volUav);
                    } else {
                        playFile(fileAlertImmediate, volAlert);
                    }
                }
            }
            // ── סיום ──
            else if (status == "2") {
                if (inAlert) {
                    inAlert = false;
                    Serial.println(">>> סיום אירוע <<<");
                    playFile(fileAllClear, volAllClear);
                }
            }
            // ── שגרה ──
            else {
                if (inAlert) {
                    inAlert = false;
                    digitalWrite(LED_PIN, LOW);
                }
            }
        } else {
            Serial.println("[STATUS] שגיאת פענוח JSON");
        }
    } else {
        Serial.printf("[ERROR] שרת לא זמין (HTTP %d)\n", code);
    }
    http.end();
}

// ══════════════════════════════════════════
void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    // אתחול DFPlayer
    mySoftwareSerial.begin(9600, SERIAL_8N1, 16, 17);
    Serial.println("\n[INIT] מאתחל DFPlayer Mini...");

    if (!myDFPlayer.begin(mySoftwareSerial)) {
        Serial.println("[ERROR] DFPlayer לא נמצא!");
    } else {
        Serial.println("[INIT] DFPlayer מוכן ✓");
        isMp3Ready = true;
        delay(1500);
        myDFPlayer.volume(20);
    }

    // חיבור WiFi
    Serial.print("[INIT] מתחבר ל-WiFi");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500); Serial.print(".");
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    }
    digitalWrite(LED_PIN, LOW);
    Serial.printf("\n[INIT] WiFi מחובר! IP: %s\n", WiFi.localIP().toString().c_str());

    // טעינת קונפיג מהשרת
    fetchEspConfig();

    // צליל פתיחה
    if (isMp3Ready) {
        delay(500);
        Serial.println("[INIT] מנגן צליל פתיחה...");
        playFile(fileStartup, volStartup);
    }
}

// ── מחזור עדכון קונפיג (כל 5 דקות) ──
unsigned long lastConfigFetch = 0;
const unsigned long CONFIG_INTERVAL = 5 * 60 * 1000UL;

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[WARN] WiFi נותק, מחבר מחדש...");
        WiFi.reconnect();
        delay(3000);
        return;
    }

    // עדכון קונפיג כל 5 דקות
    if (millis() - lastConfigFetch >= CONFIG_INTERVAL) {
        fetchEspConfig();
        lastConfigFetch = millis();
    }

    // 1. פקודות ידניות מהאתר
    checkEspCommand();
    delay(200);

    // 2. סטטוס התרעות
    checkStatus();
    delay(1200);
}
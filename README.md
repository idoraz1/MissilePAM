# 🚨 MissilePAM - Missiles Public Address Map

מערכת התרעות חכמה המנטרת את אתר פיקוד העורף בזמן אמת, מציגה התרעות על גבי מפה אינטראקטיבית, ומכריזה קולית דרך רמקולים חכמים (Google Cast) ובקרי ESP32.

## ✨ תכונות מרכזיות

*   **ניטור זמן אמת:** שימוש ב-Playwright (דפדפן Chromium) להאזנה ישירה לתעבורת הרשת של פיקוד העורף – שיטה עמידה בפני חסימות ושינויי API.
*   **דשבורד מתקדם:** ממשק Web (React + Tailwind) המציג סטטוס כוננות, מפה חיה עם מיקומי נפילות, ומונה זמן לממ"ד.
*   **מצב קיוסק (Simple Mode):** תצוגת מסך מלא נקייה למסכים תלויים או טאבלטים.
*   **כריזה חכמה (TTS):** הקראת סוג האיום והאזור בעברית ("חדירת כלי טיס עוין באזור חיפה").
*   **Google Cast Integration:** זיהוי וחיבור אוטומטי לרמקולים של Google בבית לשידור הכריזה.
*   **תמיכת חומרה (ESP32):** אינטגרציה מלאה עם בקר ESP32 ו-DFPlayer Mini לניגון MP3 מקומי (אזעקות, צפירות וכריזות) ללא תלות באינטרנט אלחוטי יציב.
*   **הגדרות מתקדמות:** ניהול אזורי עניין, רדיוס זיהוי קרוב (ק"מ), שליטה בעוצמות שמע ובחירת טקסטים לכריזה.

---

# 🌐 מדריך פריסה לשרת ענן (Oracle Cloud) ב-Ubuntu

המדריך הבא מסביר צעד אחר צעד כיצד להגדיר את שרת ה-Ubuntu שלכם ב-Oracle Cloud (או בכל שרת ענן אחר מבוסס Ubuntu) על מנת להריץ את מערכת MissilePAM כ-Service הפועל ברקע ועולה באופן אוטומטי.

**⚠️ אזהרה חמורה לגבי חסימת גישה (Geo-blocking):**
**חובה** לוודא שהשרת יושב בישראל (לדוגמה: Data Center בירושלים). הפעלת המערכת על שרת שלא בישראל, **תחסום את הגישה** לאתר פיקוד העורף, והמערכת לא תעבוד!

---

## 🔑 התחברות לשרת באמצעות SSH
לאחר יצירת השרת ב-Oracle Cloud, תקבלו כתובת IP ציבורית (Public IP). עליכם להשתמש במפתח הפרטי (`.key` או `.pem`) שהורדתם במהלך יצירת השרת כדי להתחבר.

שם המשתמש ברירת המחדל במערכות Ubuntu של Oracle הוא לרוב **`ubuntu`**.

### התחברות מ-Windows (דרך CMD או PowerShell):
1. פתחו את Command Prompt או PowerShell.
2. נווטו לתיקייה בה שמרתם את המפתח, או ספקו את הנתיב המלא אליו.
3. הריצו את הפקודה (החליפו את `<your-key-file>` בשם המפתח ואת `<ip-address>` בכתובת ה-IP של השרת):
```cmd
ssh -i "C:\path\to\<your-key-file>.key" ubuntu@<ip-address>
```

### התחברות מ-Mac / Linux:
1. פתחו את ה-Terminal.
2. ראשית, עליכם להגביל את ההרשאות לקובץ המפתח (חובה כדי ש-SSH יסכים להשתמש בו):
```bash
chmod 400 /path/to/<your-key-file>.key
```
3. לאחר מכן, התחברו:
```bash
ssh -i /path/to/<your-key-file>.key ubuntu@<ip-address>
```

*(אם המערכת מבקשת לאשר את טביעת האצבע של השרת בפעם הראשונה - הקלידו `yes` ולחצו Enter).*

---

## 🛠️ שלב 1: עדכון המערכת
לאחר שהתחברתם בהצלחה לשרת, הריצו את הפקודות הבאות כדי לעדכן את המערכת ולוודא שכל הכלים מותקנים:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git curl
```

## 📥 שלב 2: הורדת הקוד (בראנץ' Public) והגדרת הסביבה
נוריד את הקוד, ניצור סביבה וירטואלית ונתקין את הספריות הנדרשות. נמשוך ספציפית את הבראנץ' `Public` המיועד לשרת.

```bash
# מעבר לספריית הבית
cd ~

# הורדת הפרויקט מהבראנץ' Public
git clone -b Public https://github.com/idoraz1/MissilePAM.git
cd MissilePAM

# יצירת סביבה וירטואלית בשם venv
python3 -m venv venv

# הפעלת הסביבה הווירטואלית
source venv/bin/activate

# התקנת התלויות
pip install -r requirements.txt

# התקנת דפדפן Chromium עבור Playwright (חובה גם לסביבת הענן)
playwright install chromium
playwright install-deps
```

## 🌍 שלב 3: פתיחת פורטים ו-Firewall
כדי לאפשר גישה מבחוץ לשרת שלנו, עלינו לפתוח את פורט `5000`. 
ב-Oracle Cloud, נדרש לפתוח את הפורט **בשני מקומות**: במערכת ההפעלה (iptables / UFW) ובממשק האינטרנט של Oracle.

### 1. פתיחה בממשק של Oracle Cloud:
1. היכנסו ל-Dashboard של Oracle Cloud.
2. נווטו אל ה-Instance שלכם -> **Primary VNIC** -> לחצו על ה- **Subnet**.
3. היכנסו ל- **Security Lists** ולחצו על ה-Default Security List.
4. הוסיפו **Ingress Rule**:
   - Source Type: `CIDR`
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: `TCP`
   - Destination Port Range: `5000`
5. שמרו את השינויים.

### 2. פתיחה בשרת (מערכת ההפעלה):
באובונטו של Oracle לרוב מותקן `iptables` כברירת מחדל:

```bash
sudo iptables -I INPUT 1 -p tcp --dport 5000 -j ACCEPT
```
**במידה והאתר לא נטען בגלל בעיות בחסימות הרשת של אובונטו בענן, נסו להריץ במקום את הפקודה הזו (הוסיף את החוק במיקום השישי ברשימה, פתר בעיות בעבר):**
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 5000 -j ACCEPT
```

לאחר שהוספתם את החוק, שמרו את ההגדרות של ה-Firewall כדי שלא יימחקו בהפעלה מחדש:
```bash
sudo netfilter-persistent save
```
*(אם אתם משתמשים ב-UFW במקום iptables, הריצו: `sudo ufw allow 5000/tcp`)*

## ⚙️ שלב 4: יצירת Systemd Service
כדי שהמערכת תרוץ ברקע באופן קבוע ותעלה מחדש גם אם השרת מבצע הפעלה מחדש (Reboot), ניצור Service. כיוון שזהו שרת פומבי, אנו משתמשים במשתנה סביבה `PUBLIC_MODE=true` המכבה תכונות התחברות לרשת מקומית (Chromecast וכו').

ניצור את קובץ ה-Service:

```bash
sudo vi /etc/systemd/system/missilepam.service
```

העתיקו את התוכן הבא לתוך הקובץ (הקפידו לוודא שהנתיבים `/home/ubuntu/MissilePAM` תואמים למיקום שלכם, ייתכן שתצטרכו לשנות את `ubuntu` לשם המשתמש שלכם ב-Oracle אם הוא שונה - למשל `opc`):

```ini
[Unit]
Description=MissilePAM Public Address Map
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/MissilePAM
Environment="PATH=/home/ubuntu/MissilePAM/venv/bin"
Environment="PUBLIC_MODE=true"
ExecStart=/home/ubuntu/MissilePAM/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
*הערה: אם שם המשתמש שלכם ב-Oracle הוא `opc`, שנו את `User=ubuntu` ל-`User=opc`, ואת הנתיבים מ-`/home/ubuntu` ל-`/home/opc`.*

שמרו וצאו.

## 🚀 שלב 5: הפעלה ובדיקה
עכשיו ניתן ל-Systemd פקודה לטעון מחדש את ההגדרות, להפעיל את ה-Service, ולהגדיר אותו לפעול עם הדלקת המחשב:

```bash
# טעינת ההגדרות החדשות
sudo systemctl daemon-reload

# הפעלת ה-Service
sudo systemctl start missilepam.service

# הגדרת ה-Service שיפעל אוטומטית בהפעלה מחדש של השרת
sudo systemctl enable missilepam.service

# בדיקת סטטוס (לוודא שרץ כראוי)
sudo systemctl status missilepam.service
```

## 🔄 מדריך: עדכון התוכנה (מ-Branch ספציפי)
כאשר יוצא עדכון למערכת, תוכלו לעדכן אותה בצורה פשוטה ללא צורך בהתקנה מחדש.

**שים לב שאתה עובד על בראנץ' מסוים (Public). התהליך הזה ימשוך ויעדכן את השינויים מהבראנץ' הזה.**

### 1. התחברות ל-VM (לשרת)
כמו שעשינו בהתחלה:
```bash
ssh -i /path/to/<your-key-file>.key ubuntu@<ip-address>
```

### 2. מעבר לתיקיית הפרויקט
```bash
cd ~/MissilePAM
```

### 3. משיכת השינויים מה-Branch שלכם
```bash
git pull origin Public
```

### 4. במידה ויש צורך (התקנת תלויות חדשות)
אם עודכן קובץ ה- `requirements.txt`, תצטרכו גם להריץ:
```bash
source venv/bin/activate && pip install -r requirements.txt
```

### 5. הפעלת השירות מחדש
כדי שהשינויים ייכנסו לתוקף, עליכם לאתחל את המערכת:
```bash
sudo systemctl restart missilepam.service
```

### 6. לאימות שהכל עלה תקין
```bash
sudo systemctl status missilepam.service
```
ואם רוצים לראות לוגים בזמן אמת:
```bash
sudo journalctl -u missilepam.service -f
```

*(בגדול כל עדכון עתידי יצטמצם לשלושה פקודות בלבד - `git pull`, `restart`, `status`)*

---

## 🐳 הרצת המערכת באמצעות Docker

למערכת צורף גם קובץ `Dockerfile`. הקובץ מיועד למי שרוצה להרים את המערכת כשרת שיהיה פומבי, אבל רוצה לאחסן אותו בבית (לדוגמא על גבי Raspberry Pi, שרת NAS או מחשב ביתי).
השימוש ב-Docker הופך את התהליך של פריסה, אריזה והרצה להרבה יותר נוח ופשוט, כיוון שאין צורך להתקין את התלויות והדפדפנים ישירות על מערכת ההפעלה שלכם - הכל סגור בתוך ה-Container.

**⚠️ ושוב נדגיש: גם באחסון דרך Docker - אם אתם מפעילים אותו על שרת שלא ממוקם בישראל (לדוגמה דרך VPS זר), הגישה לפיקוד העורף תיחסם! המערכת תעבוד כראוי רק בשרתים (או רשתות ביתיות) בישראל.**

---

## ⚙️ הגדרת ESP32 (אופציונלי להפעלה מקומית)

המערכת תומכת בבקר ESP32 המחובר ל-DFPlayer Mini לטובת התרעות אמינות גם ללא רמקולים חכמים (בשימוש ביתי - לא פומבי).

1.  צרוב את הקוד המצורף בתיקיית `arduino_code` (או `MissilePA_ESP32`) לבקר ה-ESP32 שלך.
2.  וודא שהגדרות ה-Wi-Fi בקוד תואמות לרשת הביתית שלך.
3.  העתק את קבצי ה-MP3 (ניתן להוריד מהממשק: "הגדרות" -> "ניהול כרטיס SD") לכרטיס הזיכרון של ה-DFPlayer.
4.  חבר את הבקר לחשמל. הוא יתחבר אוטומטית לשרת וישמיע צליל "מערכת מוכנה".

## 🛡️ פתרון בעיות נפוצות

*   **שגיאת Playwright:** וודא שהרצת `playwright install chromium`.
*   **לא שומעים ברמקולים של גוגל:** וודא שהמחשב המריץ והרמקולים נמצאים באותה רשת Wi-Fi (ולא ב-Guest Network).
*   **המפה לא נטענת:** וודא שיש חיבור אינטרנט לטעינת אריחי OpenStreetMap.

## 📜 רישיון

פרויקט זה משוחרר תחת רישיון MIT. השימוש באחריות המשתמש בלבד. מערכת זו אינה מחליפה את האפליקציה הרשמית של פיקוד העורף.

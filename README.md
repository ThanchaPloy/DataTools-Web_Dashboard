# Bank Call Tracker

เว็บสำหรับทีมขายธนาคาร: บันทึกผลการโทรลง Google Sheet, วิเคราะห์อัตราตอบรับ 5 มิติ,
ฝัง dashboard Tableau และจัดอันดับว่าควรโทรหาลูกค้าคนไหนก่อนด้วยคะแนนจากโมเดล Machine Learning

เขียนด้วย Python + Streamlit ทั้งหมด

## สถาปัตยกรรม

```
เว็บ Streamlit ──อ่าน/เขียน──► Google Sheet ◄──อ่านลูกค้า / เขียนคะแนน── Google Colab (โมเดล ML)
                                   │
                                   └──► Tableau Public (Connect → Google Sheets)
```

- เว็บไม่โหลดโมเดลเอง คะแนนโอกาสตอบรับมาจาก Colab (Step 19 ใน notebook) ที่เขียนลง Sheet
- ชีตใน Google Sheet: `customers` (ลูกค้า + คะแนน), `change_log` (ประวัติการแก้ไข), `model_info` (ข้อมูลโมเดล)

## โครงสร้างโปรเจค

```
bank-call-tracker/
├── app.py                       # จุดเริ่มต้น: เมนู + หน้าภาพรวม
├── views/                       # หน้าต่าง ๆ ของเว็บ
│   ├── 1_Customer_Records.py    # รายชื่อลูกค้า: ค้นหา แก้ไข เพิ่ม ลบ แล้วบันทึก
│   ├── 2_Add_Customer.py        # ฟอร์มเพิ่มลูกค้าใหม่
│   ├── 3_Analytics.py           # Insight, อัตราตอบรับ 5 มิติ, สถิติ, Chi-square
│   ├── 4_Tableau_Dashboard.py   # ฝัง Tableau Public
│   └── 5_Lead_Scoring.py        # จัดอันดับลูกค้าจากคะแนนที่ Colab เขียนไว้
├── core/                        # โค้ดที่ทุกหน้าใช้ร่วมกัน
│   ├── config.py                # STORAGE, SHEET_ID, คอลัมน์, ค่าที่อนุญาต, ป้ายภาษาไทย, URL Tableau
│   ├── storage.py               # อ่าน/เขียน Google Sheet หรือ Excel (เลือกที่ config)
│   ├── data_io.py               # โหลด/บันทึกข้อมูลลูกค้า, change log, รหัสลูกค้า, นำเข้า CSV
│   ├── validation.py            # ตรวจข้อมูลก่อนบันทึก
│   ├── analytics.py             # อัตราตอบรับ, สถิติ, Chi-square
│   └── ui.py                    # ธีม ฟอนต์ การ์ด และรูปแบบกราฟ
├── colab/step19_score_google_sheet.py   # บล็อกที่ต้องวางต่อท้าย notebook ใน Colab
├── credentials/                 # วางไฟล์ key ของ service account (ไม่ถูกอัปขึ้น GitHub)
├── data/raw/bank-additional.csv # ไฟล์ต้นฉบับ (วางเอง)
├── scripts/prepare_data.py      # นำเข้า CSV ลง Sheet (ทางเลือกแทนปุ่มในเว็บ)
├── docs/user_manual/screenshots/
├── .streamlit/config.toml       # ธีมสว่าง
└── requirements.txt
```

## 1. ตั้งค่า Google Sheet (ครั้งเดียว)

1. สร้าง service account ใน Google Cloud และดาวน์โหลดไฟล์ key (.json) (ไม่ต้องเปิด Billing)
2. วางไฟล์ key ที่ `credentials/service_account.json`
3. สร้าง Google Sheet ว่าง แล้ว Share ให้อีเมลของ service account เป็น **Editor**
4. คัดลอก Sheet ID (ส่วนของลิงก์ระหว่าง `/d/` กับ `/edit`) ไปใส่ใน `core/config.py`

```python
SHEET_ID = "1AbCdEf...XyZ"
```

ไม่มีอินเทอร์เน็ต หรืออยากทดสอบแบบออฟไลน์: เปลี่ยน `STORAGE = "excel"` ใน `core/config.py` เว็บจะใช้ไฟล์ `data/bank_data.xlsx` แทน

## 2. ติดตั้ง (ครั้งแรก)

ใช้ Python 3.11–3.13

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Windows PowerShell ถ้า activate ไม่ได้: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## 3. นำเข้าข้อมูลและรันเว็บ

1. วาง `bank-additional.csv` ไว้ที่ `data/raw/`
2. รันเว็บ

```bash
streamlit run app.py
```

3. ที่หน้าภาพรวม กด **นำเข้าข้อมูลจาก bank-additional.csv** (ครั้งแรกครั้งเดียว)

## 4. ให้คะแนนลูกค้าด้วย Colab

1. คัดลอกเนื้อหาไฟล์ `colab/step19_score_google_sheet.py` ไปวางเป็นบล็อกใหม่ต่อท้าย notebook ML
2. ใส่ `SHEET_ID` บรรทัดบนสุดของบล็อก
3. รัน notebook ให้เทรนโมเดลเสร็จ แล้วรันบล็อกนี้ (ครั้งแรกจะขอสิทธิ์บัญชี Google ให้กดอนุญาต)
4. กลับมาที่เว็บ กด **โหลดข้อมูลล่าสุด** ที่เมนูด้านซ้าย

ทุกครั้งที่เพิ่มลูกค้าหรือแก้ข้อมูลลูกค้าในเว็บ ให้รันบล็อกนี้ใหม่ (แก้ข้อมูลลูกค้าแล้วคะแนนเดิมของแถวนั้นจะถูกล้าง)

## 5. Tableau

1. Tableau Public → Connect → **Google Sheets** → ล็อกอิน → เลือก Sheet → ใช้ชีต `customers`
2. สร้าง dashboard แล้ว Save to Tableau Public
3. คัดลอกลิงก์มาใส่ `TABLEAU_URL` ใน `core/config.py` (หรือวางในหน้า Tableau ของเว็บ)

## การใช้งานแต่ละหน้า

| หน้า | ใช้ทำอะไร |
|---|---|
| ภาพรวม | ตัวเลขสรุป, อัตราตอบรับรายเดือน, สถานะลูกค้า, การแก้ไขล่าสุด |
| รายชื่อลูกค้า | กรองข้อมูล แก้ไขในตาราง เพิ่มแถว ลบแถว แล้วกด **บันทึก** |
| เพิ่มลูกค้าใหม่ | กรอกฟอร์ม ระบบสร้างรหัสลูกค้าให้ (คะแนนมาหลังรัน Colab Step 19) |
| บทวิเคราะห์ | Insight อัตโนมัติ, กราฟ 5 มิติ, สถิติเชิงพรรณนา, Chi-square test |
| Tableau Dashboard | แสดง dashboard ที่ publish บน Tableau Public |
| จัดอันดับลูกค้า (ML) | จัดอันดับลูกค้า "รอโทร", โหมดทดสอบเทียบผลจริง, ข้อมูลโมเดล |

## ปัญหาที่พบบ่อย

| อาการ | วิธีแก้ |
|---|---|
| ยังไม่ได้ใส่ SHEET_ID / ไม่พบไฟล์ key | ทำตามหัวข้อ 1 |
| เปิด Google Sheet ไม่ได้ | ตรวจ SHEET_ID และแชร์ Sheet ให้อีเมล service account เป็น Editor แล้ว |
| แก้ใน Sheet โดยตรงแล้วเว็บไม่เปลี่ยน | เว็บจำข้อมูลไว้ 1 นาที กด **โหลดข้อมูลล่าสุด** |
| หน้า ML ขึ้นว่ายังไม่มีคะแนน | รัน Colab Step 19 แล้วกด **โหลดข้อมูลล่าสุด** |
| บันทึกผิด อยากย้อนกลับ | Google Sheet → File → Version history |
| อยากเริ่มข้อมูลใหม่จากต้นฉบับ | `python scripts/prepare_data.py --reset` |

## ข้อมูล

UCI Machine Learning Repository: Bank Marketing (`bank-additional.csv`, ราว 4,000 แถว)
ชื่อคอลัมน์ที่มีจุด เช่น `emp.var.rate` ถูกเปลี่ยนเป็น `emp_var_rate` ตอนนำเข้า

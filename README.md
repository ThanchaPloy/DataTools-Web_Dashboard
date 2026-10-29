# Bank Call Tracker

เว็บสำหรับทีมขายธนาคาร: บันทึกผลการโทรลงไฟล์ Excel, วิเคราะห์อัตราตอบรับ 5 มิติ,
สร้างไฟล์ Excel วิเคราะห์สถิติ (Descriptive, t-test, ANOVA, Chi-square, Z-test, Correlation, Solver),
ฝัง dashboard Tableau และจัดอันดับว่าควรโทรหาลูกค้าคนไหนก่อนด้วยคะแนนจากโมเดล Machine Learning

เขียนด้วย Python + Streamlit ทั้งหมด

## สถาปัตยกรรม

```
เว็บ Streamlit ──อ่าน/เขียน──► data/bank_data.xlsx ──อัปโหลด──► Google Colab (โมเดล ML, Step 19)
      ▲                              │                                  │
      └──── นำเข้า scores_from_colab.xlsx ◄──────────────────────────────┘
                                     └──► Tableau Public (Connect → Microsoft Excel)
เว็บ ──► ไฟล์ Excel วิเคราะห์สถิติ (หน้าบทวิเคราะห์ หรือ scripts/build_analysis_excel.py)
```

- ค่าเริ่มต้นใช้ไฟล์ Excel (`STORAGE = "excel"` ใน `core/config.py`) เปลี่ยนเป็น Google Sheet ได้ด้วย `STORAGE = "gsheet"`
- เว็บไม่โหลดโมเดลเอง คะแนนโอกาสตอบรับมาจาก Colab (Step 19 ใน notebook)
- ชีตในไฟล์ข้อมูล: `customers` (ลูกค้า + คะแนน), `change_log` (ประวัติการแก้ไข), `model_info` (ข้อมูลโมเดล)

## โครงสร้างโปรเจค

```
bank-call-tracker/
├── app.py                       # จุดเริ่มต้น: เมนู + หน้าภาพรวม
├── views/                       # หน้าต่าง ๆ ของเว็บ
│   ├── 1_Customer_Records.py    # รายชื่อลูกค้า: ค้นหา แก้ไข เพิ่ม ลบ แล้วบันทึก
│   ├── 2_Add_Customer.py        # ฟอร์มเพิ่มลูกค้าใหม่
│   ├── 3_Analytics.py           # Insight, อัตราตอบรับ 5 มิติ, สถิติ, Chi-square
│   ├── 4_Tableau_Dashboard.py   # ฝัง Tableau Public
│   ├── 5_Lead_Scoring.py        # จัดอันดับลูกค้าจากคะแนนที่ Colab เขียนไว้
│   ├── 6_Inferential_Stats.py   # สถิติเชิงอนุมาน: Descriptive, T-Test, ANOVA, Z-Test, Correlation, Solver
│   └── 7_About.py               # เกี่ยวกับโปรเจค: โจทย์ แหล่งข้อมูล ภาพรวมระบบ (เวอร์ชันสั้นไว้เปิดก่อนเดโม)
├── core/                        # โค้ดที่ทุกหน้าใช้ร่วมกัน
│   ├── config.py                # STORAGE, SHEET_ID, คอลัมน์, ค่าที่อนุญาต, ป้ายภาษาไทย, URL Tableau
│   ├── storage.py               # อ่าน/เขียน Google Sheet หรือ Excel (เลือกที่ config)
│   ├── data_io.py               # โหลด/บันทึกข้อมูลลูกค้า, change log, รหัสลูกค้า, นำเข้า CSV
│   ├── validation.py            # ตรวจข้อมูลก่อนบันทึก
│   ├── analytics.py             # อัตราตอบรับ, สถิติ, Chi-square
│   ├── inferential.py           # คำนวณสถิติของหน้าสถิติเชิงอนุมาน (สูตรเดียวกับไฟล์ Excel)
│   ├── excel_report.py          # สร้างไฟล์ Excel วิเคราะห์สถิติ (สูตร Excel จริงทุกค่า)
│   └── ui.py                    # ธีม ฟอนต์ การ์ด และรูปแบบกราฟ
├── colab/step19_score_excel.py          # Step 19 สำหรับโหมด Excel (วางต่อท้าย notebook ใน Colab)
├── colab/step19_score_google_sheet.py   # Step 19 สำหรับโหมด Google Sheet
├── credentials/                 # วางไฟล์ key ของ service account (ไม่ถูกอัปขึ้น GitHub)
├── data/raw/bank-additional.csv # ไฟล์ต้นฉบับ (วางเอง)
├── scripts/prepare_data.py      # นำเข้า CSV (ทางเลือกแทนปุ่มในเว็บ)
├── scripts/build_analysis_excel.py  # สร้างไฟล์ Excel วิเคราะห์สถิติลง outputs/
├── scripts/build_tableau.py     # สร้างไฟล์ Tableau workbook ลง tableau/
├── tableau/README.md            # วิธีเปิด/บันทึก .twbx และ publish
├── docs/user_manual/screenshots/
├── .streamlit/config.toml       # ธีมสว่าง
└── requirements.txt
```

## 1. ตั้งค่า (ครั้งเดียว)

- ใส่ชื่อกลุ่มใน `core/config.py` → `GROUP_NAME = "..."` (ใช้ตั้งชื่อไฟล์ที่เว็บสร้าง)
- ใช้ไฟล์ Excel (ค่าเริ่มต้น) ไม่ต้องตั้งค่าอะไรเพิ่ม ข้ามหัวข้อย่อยด้านล่างได้

### ถ้าจะใช้ Google Sheet แทน

1. สร้าง service account ใน Google Cloud และดาวน์โหลดไฟล์ key (.json) (ไม่ต้องเปิด Billing)
2. วางไฟล์ key ที่ `credentials/service_account.json`
3. สร้าง Google Sheet ว่าง แล้ว Share ให้อีเมลของ service account เป็น **Editor**
4. คัดลอก Sheet ID (ส่วนของลิงก์ระหว่าง `/d/` กับ `/edit`) ไปใส่ใน `core/config.py`

```python
SHEET_ID = "1AbCdEf...XyZ"
```

แล้วเปลี่ยน `STORAGE = "gsheet"` ใน `core/config.py`

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

## 4. ให้คะแนนลูกค้าด้วย Colab (โหมด Excel)

1. คัดลอกเนื้อหาไฟล์ `colab/step19_score_excel.py` ไปวางเป็นบล็อกใหม่ต่อท้าย notebook ML
2. รัน notebook ให้เทรนโมเดลเสร็จ แล้วรันบล็อกนี้ → กดเลือกไฟล์ `data/bank_data.xlsx` ของเว็บ
3. Colab ดาวน์โหลดไฟล์ `scores_from_colab.xlsx` ให้
4. ในเว็บ หน้า **จัดอันดับลูกค้า (ML)** → **นำเข้าคะแนนจาก Colab** → อัปโหลดไฟล์ → กด **นำเข้าคะแนน**

ทุกครั้งที่เพิ่มลูกค้าหรือแก้ข้อมูลลูกค้าในเว็บ ให้ทำซ้ำ (แก้ข้อมูลลูกค้าแล้วคะแนนเดิมของแถวนั้นจะถูกล้าง)
โหมด Google Sheet ใช้ `colab/step19_score_google_sheet.py` แทน (Colab เขียนลง Sheet ให้เอง)

## 4.1 ไฟล์ Excel วิเคราะห์สถิติ (ส่งงาน)

หน้า **บทวิเคราะห์** → แท็บ **ไฟล์ Excel วิเคราะห์สถิติ** → **สร้างไฟล์ Excel** → **ดาวน์โหลด**
(หรือ `python scripts/build_analysis_excel.py` ได้ไฟล์ใน `outputs/`)

ชีต (เรียงตามจริงในไฟล์): README (สรุปทุกชีต + หมายเหตุ), Descriptive, Conversion (Pivot), T-Test, ANOVA, Chi-Square, Z-Test, Correlation, Solver, Data (อยู่ท้ายสุด)
ผลชุดเดียวกันดูในเว็บได้ที่หน้า **สถิติเชิงอนุมาน** (คำนวณด้วย Python ตัวเลขตรงกับไฟล์)
ทุกค่าเป็นสูตร Excel ที่อ้างอิงชีต Data ชีต Solver ตั้งค่าไว้แล้ว เปิด Data → Solver แล้วกด Solve ได้ทันที
ต้องมีลูกค้าที่โทรแล้ว (ตอบรับ/ไม่ตอบรับ) อย่างน้อย **30 คน** ไม่งั้นระบบจะแจ้งเตือนว่าข้อมูลน้อยเกินไปและไม่สร้างไฟล์ให้

## 5. Tableau

```bash
python scripts/build_tableau.py
```

ได้ `tableau/<ชื่อกลุ่ม>_dashboard.twb` (10 ชีต + Dashboard เชื่อมกับ `data/bank_data.xlsx`)
เปิดใน Tableau Public → Save to Tableau Public → คัดลอกลิงก์มาใส่ `TABLEAU_URL` ใน `core/config.py`
รายละเอียดและวิธีสร้างเองถ้าเปิดไฟล์ไม่ได้: `tableau/README.md`

## การใช้งานแต่ละหน้า

| หน้า | ใช้ทำอะไร |
|---|---|
| ภาพรวม | ตัวเลขสรุป, อัตราตอบรับรายเดือน, สถานะลูกค้า, การแก้ไขล่าสุด |
| รายชื่อลูกค้า | กรองข้อมูล แก้ไขในตาราง เพิ่มแถว ลบแถว แล้วกด **บันทึก** |
| เพิ่มลูกค้าใหม่ | กรอกฟอร์ม ระบบสร้างรหัสลูกค้าให้ (คะแนนมาหลังรัน Colab Step 19) |
| บทวิเคราะห์ | Insight อัตโนมัติ, กราฟ 5 มิติ, สถิติเชิงพรรณนา, Chi-square test, สร้างไฟล์ Excel วิเคราะห์สถิติ |
| สถิติเชิงอนุมาน | Descriptive + Histogram, T-Test / ANOVA / Z-Test (เลือกตัวแปรเอง ปรับ α ได้), Correlation heatmap, Solver จัดสรรสายโทรด้วยแถบเลื่อน (ผลตรงกับไฟล์ Excel) |
| Tableau Dashboard | แสดง dashboard ที่ publish บน Tableau Public |
| จัดอันดับลูกค้า (ML) | จัดอันดับลูกค้า "รอโทร", โหมดทดสอบเทียบผลจริง, ข้อมูลโมเดล |
| เกี่ยวกับโปรเจค | สรุปโจทย์ แหล่งข้อมูล และภาพรวมระบบในหน้าเดียว ไว้เปิดก่อนเริ่มเดโม/พรีเซนต์ |

## ปัญหาที่พบบ่อย

| อาการ | วิธีแก้ |
|---|---|
| ยังไม่ได้ใส่ SHEET_ID / ไม่พบไฟล์ key | ทำตามหัวข้อ 1 |
| เปิด Google Sheet ไม่ได้ | ตรวจ SHEET_ID และแชร์ Sheet ให้อีเมล service account เป็น Editor แล้ว |
| แก้ใน Sheet โดยตรงแล้วเว็บไม่เปลี่ยน | เว็บจำข้อมูลไว้ 1 นาที กด **โหลดข้อมูลล่าสุด** |
| หน้า ML ขึ้นว่ายังไม่มีคะแนน | รัน Colab Step 19 แล้วนำเข้าไฟล์คะแนนในหน้า ML |
| บันทึกไม่ได้ ไฟล์ถูกเปิดอยู่ | ปิด `bank_data.xlsx` ในโปรแกรม Excel ก่อน |
| บันทึกผิด อยากย้อนกลับ | โหมด Excel: สำรองไฟล์ `data/bank_data.xlsx` ไว้เองก่อนแก้ครั้งใหญ่ · โหมด Google Sheet: File → Version history |
| ไม่มีเมนู Solver ใน Excel | File → Options → Add-ins → Manage: Excel Add-ins → Go → ติ๊ก Solver Add-in |
| อยากเริ่มข้อมูลใหม่จากต้นฉบับ | `python scripts/prepare_data.py --reset` |

## ข้อมูล

UCI Machine Learning Repository: Bank Marketing (`bank-additional.csv`, ราว 4,000 แถว)
ชื่อคอลัมน์ที่มีจุด เช่น `emp.var.rate` ถูกเปลี่ยนเป็น `emp_var_rate` ตอนนำเข้า
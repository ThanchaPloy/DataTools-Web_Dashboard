"""
ค่าตั้งกลางของทั้งเว็บ
- ที่อยู่ไฟล์
- รายชื่อคอลัมน์
- ค่าที่อนุญาตของแต่ละช่อง (ใช้ทั้ง dropdown ในฟอร์มและการตรวจข้อมูล)
- ป้ายภาษาไทย
แก้ที่ไฟล์นี้ไฟล์เดียว มีผลกับทุกหน้า
"""
from pathlib import Path

# ------------------------------------------------------------
# แหล่งเก็บข้อมูล
#   "gsheet" = Google Sheet (ใช้จริง)
#   "excel"  = ไฟล์ Excel ในเครื่อง (ทางสำรอง ใช้ได้โดยไม่ต้องต่ออินเทอร์เน็ต)
# ------------------------------------------------------------
STORAGE = "excel"

# Sheet ID: ส่วนของลิงก์ระหว่าง /d/ กับ /edit
# https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
SHEET_ID = ""

# ชื่อกลุ่ม: ใช้ตั้งชื่อไฟล์ที่เว็บสร้างให้ (ข้อกำหนดวิชา: ชื่อไฟล์ต้องเป็นชื่อกลุ่ม)
GROUP_NAME = "66050762-67050131"

# ------------------------------------------------------------
# ที่อยู่ไฟล์
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_CSV = DATA_DIR / "raw" / "bank-additional.csv"      # ไฟล์ต้นฉบับ ห้ามแก้
EXCEL_PATH = DATA_DIR / "bank_data.xlsx"                 # ใช้เมื่อ STORAGE = "excel"
OUTPUT_DIR = BASE_DIR / "outputs"                        # ไฟล์ Excel วิเคราะห์สถิติที่สร้างจากสคริปต์
CREDENTIALS_PATH = BASE_DIR / "credentials" / "service_account.json"   # key ของ service account

# ชื่อชีต (แท็บ) ใน Google Sheet / Excel
SHEET_CUSTOMERS = "customers"
SHEET_LOG = "change_log"
SHEET_MODEL_INFO = "model_info"      # Colab เป็นคนเขียน

# ------------------------------------------------------------
# Tableau Public: วาง URL ของ dashboard ที่ publish แล้วตรงนี้
# เช่น "https://public.tableau.com/views/BankMarketing/Dashboard1"
# ------------------------------------------------------------
TABLEAU_URL = "https://public.tableau.com/app/profile/thanchanok.klinkamol/viz/66050762-67050131_dashboard/Dashboard?publish=yes"

# ------------------------------------------------------------
# ค่าสมมติทางธุรกิจ (ตรงกับใน notebook ML)
# ------------------------------------------------------------
PROFIT_PER_YES = 100
COST_PER_CALL = 20

# ------------------------------------------------------------
# คอลัมน์
# ------------------------------------------------------------
ID_COL = "customer_id"
TARGET_COL = "y"
UPDATED_COL = "updated_at"

DATA_COLUMNS = [
    "age", "job", "marital", "education", "default", "housing", "loan",
    "contact", "month", "day_of_week", "duration", "campaign", "pdays",
    "previous", "poutcome", "emp_var_rate", "cons_price_idx", "cons_conf_idx",
    "euribor3m", "nr_employed", "y",
]
# คอลัมน์คะแนนที่ Colab เขียนกลับมา (Step 19 ใน notebook) เว็บไม่คำนวณเอง
SCORE_COLUMNS = ["prob_yes", "persona", "action", "scored_at"]
ALL_COLUMNS = [ID_COL] + DATA_COLUMNS + [UPDATED_COL] + SCORE_COLUMNS
LOG_COLUMNS = ["timestamp", "action", "customer_id", "details"]

# ------------------------------------------------------------
# ค่าที่อนุญาตของคอลัมน์ข้อความ (ตามชุดข้อมูล UCI Bank Marketing)
# ------------------------------------------------------------
ALLOWED = {
    "job": ["admin.", "blue-collar", "entrepreneur", "housemaid", "management",
            "retired", "self-employed", "services", "student", "technician",
            "unemployed", "unknown"],
    "marital": ["married", "single", "divorced", "unknown"],
    "education": ["basic.4y", "basic.6y", "basic.9y", "high.school", "illiterate",
                  "professional.course", "university.degree", "unknown"],
    "default": ["no", "yes", "unknown"],
    "housing": ["no", "yes", "unknown"],
    "loan": ["no", "yes", "unknown"],
    "contact": ["cellular", "telephone"],
    "month": ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"],
    "day_of_week": ["mon", "tue", "wed", "thu", "fri"],
    "poutcome": ["nonexistent", "failure", "success"],
    "y": ["pending", "yes", "no"],
}

# ช่วงค่าที่อนุญาตของคอลัมน์ตัวเลข (min, max)
NUMERIC_RANGES = {
    "age": (17, 100),
    "duration": (0, 6000),
    "campaign": (0, 60),
    "pdays": (0, 999),
    "previous": (0, 10),
    "emp_var_rate": (-5.0, 5.0),
    "cons_price_idx": (90.0, 96.0),
    "cons_conf_idx": (-60.0, -20.0),
    "euribor3m": (0.0, 6.0),
    "nr_employed": (4900.0, 5300.0),
}
INT_COLUMNS = ["age", "duration", "campaign", "pdays", "previous"]

# ------------------------------------------------------------
# ป้ายภาษาไทย
# ------------------------------------------------------------
LABELS = {
    "customer_id": "รหัสลูกค้า",
    "age": "อายุ",
    "job": "อาชีพ",
    "marital": "สถานภาพ",
    "education": "การศึกษา",
    "default": "เคยผิดนัดชำระ",
    "housing": "สินเชื่อบ้าน",
    "loan": "สินเชื่อส่วนบุคคล",
    "contact": "ช่องทางติดต่อ",
    "month": "เดือนที่ติดต่อ",
    "day_of_week": "วันที่ติดต่อ",
    "duration": "ความยาวสาย (วินาที)",
    "campaign": "จำนวนครั้งที่โทร",
    "pdays": "วันนับจากติดต่อครั้งก่อน",
    "previous": "จำนวนครั้งที่ติดต่อก่อนหน้า",
    "poutcome": "ผลแคมเปญก่อน",
    "emp_var_rate": "อัตราเปลี่ยนแปลงการจ้างงาน",
    "cons_price_idx": "ดัชนีราคาผู้บริโภค",
    "cons_conf_idx": "ดัชนีความเชื่อมั่นผู้บริโภค",
    "euribor3m": "อัตราดอกเบี้ย Euribor 3 เดือน",
    "nr_employed": "จำนวนผู้มีงานทำ (พันคน)",
    "y": "ผลการโทร",
    "updated_at": "แก้ไขล่าสุด",
    "age_group": "กลุ่มอายุ",
    "was_contacted_before": "เคยติดต่อมาก่อน",
    "campaign_group": "จำนวนครั้งที่โทร (กลุ่ม)",
    "prob_yes": "โอกาสตอบรับ",
    "persona": "กลุ่มลูกค้า",
    "action": "คำแนะนำ",
    "scored_at": "ให้คะแนนเมื่อ",
}

# ลำดับของกลุ่มที่สร้างขึ้นเอง (ใช้เรียงกราฟ)
GROUP_ORDER = {
    "age_group": ["<30", "30-39", "40-49", "50-59", "60+"],
    "campaign_group": ["0-1", "2", "3", "4-5", "6+"],
}
STATUS_LABELS = {"pending": "รอโทร", "yes": "ตอบรับ", "no": "ไม่ตอบรับ"}

# มิติการวิเคราะห์ 5 มิติ (ใช้ในหน้า Analytics)
DIMENSIONS = {
    "1. ข้อมูลประชากร": ["age_group", "job", "marital", "education"],
    "2. สถานะการเงิน": ["default", "housing", "loan"],
    "3. ช่องทางและจังหวะเวลา": ["contact", "month", "day_of_week"],
    "4. ประวัติการติดต่อ": ["poutcome", "was_contacted_before", "campaign_group"],
    "5. ภาวะเศรษฐกิจ": ["emp_var_rate", "cons_price_idx", "cons_conf_idx", "euribor3m", "nr_employed"],
}
MACRO_COLUMNS = DIMENSIONS["5. ภาวะเศรษฐกิจ"]

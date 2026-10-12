"""
จัดการข้อมูลลูกค้า (ใช้ core/storage.py เป็นที่เก็บ จะเป็น Google Sheet หรือ Excel ก็ได้)
- โหลดข้อมูลพร้อมแปลงชนิด (และจำไว้ชั่วคราวเพื่อความเร็ว)
- บันทึกตารางลูกค้า / ต่อท้ายประวัติการแก้ไข
- สร้างรหัสลูกค้าใหม่
- นำเข้าข้อมูลครั้งแรกจาก CSV
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from core import config as C
from core.storage import StorageError, make_storage

__all__ = ["StorageError", "load_data", "require_data", "save_customers", "append_log",
           "append_customer", "next_ids", "now_str", "log_entries", "is_initialized",
           "build_from_csv", "load_model_info", "add_derived", "refresh", "storage_label"]

NUMERIC_COLUMNS = C.INT_COLUMNS + C.MACRO_COLUMNS + ["prob_yes"]
CACHE_TTL = 60          # วินาที: อ่านข้อมูลจาก Google Sheet ใหม่อย่างน้อยทุก 1 นาที


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@st.cache_resource(show_spinner="กำลังเชื่อมต่อแหล่งข้อมูล...")
def _storage():
    return make_storage()


def storage():
    try:
        return _storage()
    except StorageError:
        _storage.clear()          # ไม่จำการเชื่อมต่อที่ล้มเหลว
        raise


def storage_label() -> str:
    return {"gsheet": "Google Sheet", "excel": "Excel ในเครื่อง"}.get(C.STORAGE, C.STORAGE)


# ------------------------------------------------------------
# อ่าน
# ------------------------------------------------------------
def _clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for col in C.ALL_COLUMNS:                 # ชีตเก่าที่ยังไม่มีคอลัมน์คะแนน
        if col not in d.columns:
            d[col] = pd.NA
    d = d[C.ALL_COLUMNS]
    d = d.replace("", pd.NA)
    for col in NUMERIC_COLUMNS:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    for col in C.INT_COLUMNS:
        d[col] = d[col].round().astype("Int64")
    for col in [C.ID_COL, C.UPDATED_COL, "persona", "action", "scored_at"] + list(C.ALLOWED):
        d[col] = d[col].astype("string")
    return d[d[C.ID_COL].notna()].reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL, show_spinner="กำลังโหลดข้อมูล...")
def _read_all():
    s = storage()
    customers = s.read(C.SHEET_CUSTOMERS)
    if customers.empty:
        return None, None
    log = s.read(C.SHEET_LOG)
    if log.empty:
        log = pd.DataFrame(columns=C.LOG_COLUMNS)
    log = log.reindex(columns=C.LOG_COLUMNS).astype("string")
    return _clean_customers(customers), log


def load_data():
    """คืนค่า (ตารางลูกค้า, ตารางประวัติ) ถ้ายังไม่ได้นำเข้าข้อมูล คืน (None, None)"""
    customers, log = _read_all()
    if customers is None:
        return None, None
    return customers.copy(), log.copy()


def refresh():
    """ล้างข้อมูลที่จำไว้ ให้โหลดใหม่จากแหล่งข้อมูล (เช่น หลัง Colab เขียนคะแนนลง Sheet)"""
    _read_all.clear()
    _read_model_info.clear()


def require_data():
    """ใช้ในหน้าต่าง ๆ: โหลดข้อมูล ถ้าเชื่อมต่อไม่ได้หรือยังไม่มีข้อมูล แสดงข้อความแล้วหยุดหน้า"""
    try:
        customers, log = load_data()
    except StorageError as e:
        st.error(str(e))
        st.stop()
    if customers is None:
        st.warning("ยังไม่มีข้อมูลลูกค้า ไปที่หน้า 'ภาพรวม' เพื่อนำเข้าข้อมูลก่อน")
        st.stop()
    return customers, log


def is_initialized() -> bool:
    return storage().has_sheet(C.SHEET_CUSTOMERS)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _read_model_info():
    df = storage().read(C.SHEET_MODEL_INFO)
    if df.empty or not {"key", "value"} <= set(df.columns):
        return {}
    return dict(zip(df["key"].astype(str), df["value"]))


def load_model_info() -> dict:
    """ข้อมูลโมเดลที่ Colab เขียนไว้ในชีต model_info (ว่างถ้ายังไม่เคยรัน Step 19)"""
    try:
        return _read_model_info()
    except StorageError:
        return {}


# ------------------------------------------------------------
# เขียน
# ------------------------------------------------------------
def save_customers(customers: pd.DataFrame):
    storage().write(C.SHEET_CUSTOMERS, customers[C.ALL_COLUMNS])
    refresh()


def log_entries(rows: list) -> pd.DataFrame:
    """rows = [(action, customer_id, details), ...] -> ตาราง log"""
    ts = now_str()
    return pd.DataFrame([{"timestamp": ts, "action": a, "customer_id": cid, "details": d}
                         for a, cid, d in rows], columns=C.LOG_COLUMNS)


def append_log(rows: list):
    if rows:
        storage().append(C.SHEET_LOG, log_entries(rows))
        refresh()


def next_ids(customers: pd.DataFrame, n: int) -> list:
    """สร้างรหัสลูกค้าใหม่ n รหัส ต่อจากเลขที่มากที่สุด (รูปแบบ C0001)"""
    nums = (customers[C.ID_COL].dropna().astype(str)
            .str.extract(r"(\d+)")[0].dropna().astype(int))
    start = int(nums.max()) + 1 if len(nums) else 1
    return [f"C{i:04d}" for i in range(start, start + n)]


def append_customer(record: dict) -> str:
    """เพิ่มลูกค้าใหม่ 1 คน (ต่อท้ายชีต ไม่เขียนทับทั้งตาราง) คืนค่ารหัสลูกค้า"""
    refresh()                                   # อ่านค่าล่าสุดก่อนสร้างรหัส กันรหัสซ้ำ
    customers, _ = load_data()
    new_id = next_ids(customers, 1)[0]
    row = {col: pd.NA for col in C.ALL_COLUMNS}
    row.update(record)
    row.update({C.ID_COL: new_id, C.UPDATED_COL: now_str()})
    storage().append(C.SHEET_CUSTOMERS, pd.DataFrame([row], columns=C.ALL_COLUMNS))
    append_log([("เพิ่ม", new_id, "เพิ่มจากฟอร์มลูกค้าใหม่")])
    return new_id


def build_from_csv(overwrite: bool = False) -> int:
    """
    นำเข้า data/raw/bank-additional.csv ไปที่แหล่งข้อมูล (ครั้งแรก)
    - เปลี่ยนชื่อคอลัมน์ที่มีจุดเป็นขีดล่าง (emp.var.rate -> emp_var_rate)
    - เพิ่ม customer_id, updated_at และคอลัมน์คะแนน (ว่าง)
    คืนค่าจำนวนแถว
    """
    if not C.RAW_CSV.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ต้นฉบับที่ {C.RAW_CSV}")
    if not overwrite and is_initialized():
        raise FileExistsError("มีข้อมูลลูกค้าอยู่แล้ว")

    raw = pd.read_csv(C.RAW_CSV, sep=";")
    if raw.shape[1] == 1:                       # เผื่อไฟล์คั่นด้วย comma
        raw = pd.read_csv(C.RAW_CSV)
    raw.columns = raw.columns.str.strip().str.replace(".", "_", regex=False)
    missing = [c for c in C.DATA_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"ไฟล์ต้นฉบับขาดคอลัมน์: {missing}")

    df = raw[C.DATA_COLUMNS].copy()
    df.insert(0, C.ID_COL, [f"C{i:04d}" for i in range(1, len(df) + 1)])
    df[C.UPDATED_COL] = now_str()
    for col in C.SCORE_COLUMNS:
        df[col] = pd.NA

    s = storage()
    s.write(C.SHEET_CUSTOMERS, df[C.ALL_COLUMNS])
    s.write(C.SHEET_LOG, log_entries(
        [("สร้างข้อมูล", "-", f"นำเข้าจาก {C.RAW_CSV.name} จำนวน {len(df):,} แถว")]))
    refresh()
    return len(df)


# ------------------------------------------------------------
# คอลัมน์สำหรับวิเคราะห์ (ไม่บันทึก)
# ------------------------------------------------------------
def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    age = d["age"].astype(float)
    d["age_group"] = pd.cut(age, bins=[0, 29, 39, 49, 59, 200],
                            labels=C.GROUP_ORDER["age_group"]).astype(str)
    d["was_contacted_before"] = (d["pdays"] != 999).map({True: "เคย", False: "ไม่เคย"})
    d["campaign_group"] = pd.cut(d["campaign"].astype(float), bins=[-1, 1, 2, 3, 5, 1000],
                                 labels=C.GROUP_ORDER["campaign_group"]).astype(str)
    d["status"] = d[C.TARGET_COL].map(C.STATUS_LABELS)
    return d

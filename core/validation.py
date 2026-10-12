"""
ตรวจข้อมูลก่อนบันทึก
- ช่องข้อความต้องเป็นค่าที่อยู่ในรายการ (config.ALLOWED)
- ช่องตัวเลขต้องอยู่ในช่วงที่กำหนด (config.NUMERIC_RANGES)
- ห้ามว่าง
"""
import pandas as pd

from core import config as C


def _is_missing(val) -> bool:
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except (TypeError, ValueError):
        return False
    return isinstance(val, str) and val.strip() == ""


def validate_record(rec: dict) -> list:
    """ตรวจลูกค้า 1 คน คืนรายการข้อผิดพลาด (ว่าง = ผ่าน)"""
    errors = []
    for col in C.DATA_COLUMNS:
        label = C.LABELS.get(col, col)
        val = rec.get(col)
        if _is_missing(val):
            errors.append(f"{label}: ห้ามว่าง")
            continue
        if col in C.ALLOWED and val not in C.ALLOWED[col]:
            errors.append(f"{label}: ค่า '{val}' ไม่อยู่ในรายการที่อนุญาต")
        if col in C.NUMERIC_RANGES:
            lo, hi = C.NUMERIC_RANGES[col]
            try:
                num = float(val)
            except (TypeError, ValueError):
                errors.append(f"{label}: ต้องเป็นตัวเลข")
                continue
            if not lo <= num <= hi:
                errors.append(f"{label}: ต้องอยู่ระหว่าง {lo} ถึง {hi}")
    # ความสอดคล้องของข้อมูลการติดต่อครั้งก่อน
    if rec.get("pdays") == 999 and rec.get("poutcome") == "success":
        errors.append("ผลแคมเปญก่อนเป็น success แต่ระบุว่าไม่เคยติดต่อ (pdays = 999)")
    return errors


def validate_frame(df: pd.DataFrame) -> list:
    """ตรวจทั้งตาราง คืนรายการข้อความ 'รหัสลูกค้า: ข้อผิดพลาด'"""
    messages = []
    for _, row in df.iterrows():
        cid = row.get(C.ID_COL) or "(แถวใหม่)"
        for err in validate_record(row.to_dict()):
            messages.append(f"{cid} — {err}")
    return messages


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """แปลงชนิดข้อมูลให้ถูกต้องก่อนบันทึก"""
    d = df.copy()
    for col in C.INT_COLUMNS:
        d[col] = pd.to_numeric(d[col], errors="coerce").round().astype("Int64")
    for col in C.MACRO_COLUMNS:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    for col in C.ALLOWED:
        d[col] = d[col].astype("string").str.strip().str.lower()
    # job มีจุดท้าย 'admin.' ต้องคงไว้; lower() ไม่กระทบ
    return d

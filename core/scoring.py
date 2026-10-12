"""
โหลดโมเดลจากวิชา ML (models/model_bundle.joblib) และให้คะแนนโอกาสตอบรับ
ขั้นตอนเหมือนใน notebook: add_features -> โมเดล -> calibrate (Platt) -> threshold
"""
import numpy as np
import pandas as pd
import streamlit as st

from core import config as C

REQUIRED_VERSIONS = {"sklearn": "1.6.1", "xgboost": "3.4.1"}


def installed_versions() -> dict:
    out = {}
    try:
        import sklearn
        out["sklearn"] = sklearn.__version__
    except ImportError:
        out["sklearn"] = "ไม่ได้ติดตั้ง"
    try:
        import xgboost
        out["xgboost"] = xgboost.__version__
    except ImportError:
        out["xgboost"] = "ไม่ได้ติดตั้ง"
    return out


@st.cache_resource(show_spinner="กำลังโหลดโมเดล...")
def _load_cached(path: str, mtime: float, size: int):
    # จำโมเดลไว้ตามเวลาแก้ไขและขนาดไฟล์ ถ้าเปลี่ยนไฟล์จะโหลดใหม่เอง
    # ถ้าโหลดไม่สำเร็จจะ raise ออกไป และ Streamlit จะไม่จำผลที่ล้มเหลว
    import joblib
    return joblib.load(path)


def load_bundle():
    """คืนค่า (bundle, ข้อความ error) ถ้าโหลดไม่ได้ bundle = None"""
    if not C.MODEL_PATH.exists():
        return None, ("ไม่พบไฟล์โมเดล ให้คัดลอก model_bundle.joblib จากโฟลเดอร์ outputs "
                      "ของ Colab มาไว้ในโฟลเดอร์ models/")
    stat = C.MODEL_PATH.stat()
    try:
        bundle = _load_cached(str(C.MODEL_PATH), stat.st_mtime, stat.st_size)
    except Exception as e:                       # มักเกิดจากเวอร์ชันไลบรารีไม่ตรงกับ Colab
        v = installed_versions()
        return None, (f"โหลดโมเดลไม่สำเร็จ ({type(e).__name__}: {e}) "
                      f"เวอร์ชันที่ติดตั้ง: scikit-learn {v['sklearn']}, xgboost {v['xgboost']} "
                      f"ต้องใช้ scikit-learn {REQUIRED_VERSIONS['sklearn']} และ "
                      f"xgboost {REQUIRED_VERSIONS['xgboost']} ให้ตรงกับ Colab")
    return bundle, None


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    # ต้องเหมือนฟังก์ชัน add_features ใน notebook ML
    d = df.copy()
    d["was_contacted_before"] = (d["pdays"] != 999).astype(int)
    d["age_group"] = pd.cut(d["age"], bins=[0, 29, 39, 49, 59, 120],
                            labels=["<30", "30-39", "40-49", "50-59", "60+"]).astype(str)
    return d


def _calibrate(platt, p_raw):
    # Platt scaling แบบเดียวกับ notebook: Logistic Regression บน log-odds
    p = np.clip(np.asarray(p_raw, dtype=float), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    return platt.predict_proba(logit)[:, 1]


def score(df: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    """
    ให้คะแนนลูกค้า คืนตารางเดิม + prob_yes, expected_profit, persona, action
    ใช้ได้ทั้งลูกค้าคนเดียวและหลายคน
    """
    d = _add_features(df)
    for col in ["age", "pdays", "previous"]:
        d[col] = pd.to_numeric(d[col])

    model = bundle["model"]
    features = bundle["features"]
    missing = [c for c in features if c not in d.columns]
    if missing:
        raise ValueError(f"ข้อมูลขาดคอลัมน์ที่โมเดลต้องใช้: {missing}")

    raw = model.predict_proba(d[features])[:, 1]
    d["prob_yes"] = _calibrate(bundle["platt"], raw)

    profit = bundle.get("profit_per_yes", C.PROFIT_PER_YES)
    cost = bundle.get("cost_per_call", C.COST_PER_CALL)
    d["expected_profit"] = d["prob_yes"] * profit - cost

    threshold = bundle["threshold"]
    d["action"] = np.where(d["prob_yes"] >= threshold, "ควรโทรก่อน", "ลำดับรอง")

    try:                                          # persona จาก K-Means (ถ้ามีใน bundle)
        seg = bundle["kmeans"].predict(bundle["seg_prep"].transform(d))
        names = bundle.get("segment_names", {})
        d["persona"] = [names.get(int(s), f"Segment {int(s)}") for s in seg]
    except Exception:
        d["persona"] = "-"
    return d


def model_info(bundle: dict) -> dict:
    return {
        "ชนิดโมเดล": type(bundle["model"].named_steps.get("model", bundle["model"])).__name__,
        "จำนวนฟีเจอร์": len(bundle["features"]),
        "ฟีเจอร์": ", ".join(bundle["features"]),
        "threshold": round(float(bundle["threshold"]), 3),
        "กำไรต่อคนที่ตอบรับ (สมมติ)": bundle.get("profit_per_yes", C.PROFIT_PER_YES),
        "ต้นทุนต่อสาย (สมมติ)": bundle.get("cost_per_call", C.COST_PER_CALL),
    }
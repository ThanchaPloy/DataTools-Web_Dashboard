"""
คำนวณสถิติสำหรับหน้า Analytics และหน้าแรก
ทุกฟังก์ชันใช้เฉพาะลูกค้าที่โทรแล้ว (ตอบรับ / ไม่ตอบรับ) ไม่นับ 'รอโทร'
"""
import pandas as pd
from scipy.stats import chi2_contingency

from core import config as C


def called_only(df: pd.DataFrame) -> pd.DataFrame:
    """เฉพาะลูกค้าที่โทรแล้ว พร้อมคอลัมน์ target (1 = ตอบรับ)"""
    d = df[df[C.TARGET_COL].isin(["yes", "no"])].copy()
    d["target"] = (d[C.TARGET_COL] == "yes").astype(int)
    return d


def kpis(df: pd.DataFrame) -> dict:
    called = called_only(df)
    return {
        "total": len(df),
        "called": len(called),
        "yes": int(called["target"].sum()),
        "pending": int((df[C.TARGET_COL] == "pending").sum()),
        "conversion": called["target"].mean() if len(called) else 0.0,
    }


def conversion_by(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """อัตราตอบรับแยกตามกลุ่มของคอลัมน์ col"""
    called = called_only(df)
    out = (called.groupby(col, observed=True)["target"]
                 .agg(conversion="mean", contacts="count", yes="sum")
                 .reset_index())
    if col == "month":                                   # เรียงเดือนตามปฏิทิน
        order = {m: i for i, m in enumerate(C.ALLOWED["month"])}
        return out.sort_values(col, key=lambda s: s.map(order))
    if col == "day_of_week":
        order = {d: i for i, d in enumerate(C.ALLOWED["day_of_week"])}
        return out.sort_values(col, key=lambda s: s.map(order))
    if col in C.GROUP_ORDER:
        order = {g: i for i, g in enumerate(C.GROUP_ORDER[col])}
        return out.sort_values(col, key=lambda s: s.map(order))
    return out.sort_values("conversion", ascending=False)


def describe_numeric(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """สถิติเชิงพรรณนาของคอลัมน์ตัวเลข"""
    called = called_only(df)
    desc = called[cols].describe().T
    desc["median"] = called[cols].median()
    desc = desc[["count", "mean", "median", "std", "min", "max"]]
    desc.index = [C.LABELS.get(c, c) for c in desc.index]
    desc.columns = ["จำนวน", "ค่าเฉลี่ย", "มัธยฐาน", "ส่วนเบี่ยงเบนมาตรฐาน", "ต่ำสุด", "สูงสุด"]
    return desc.round(2)


def compare_groups(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """ค่าเฉลี่ยของคอลัมน์ตัวเลข แยกระหว่างคนตอบรับ กับ ไม่ตอบรับ"""
    called = called_only(df)
    out = called.groupby(C.TARGET_COL)[cols].mean().T
    out.index = [C.LABELS.get(c, c) for c in out.index]
    out = out.rename(columns={"yes": "ตอบรับ", "no": "ไม่ตอบรับ"})
    return out.round(3)


def chi_square(df: pd.DataFrame, col: str, alpha: float = 0.05) -> dict:
    """
    Chi-square test of independence: ตัวแปร col กับผลการโทร เกี่ยวข้องกันหรือไม่
    H0: ไม่เกี่ยวข้องกัน | ถ้า p-value < alpha ปฏิเสธ H0
    """
    called = called_only(df)
    table = pd.crosstab(called[col], called[C.TARGET_COL])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"col": col, "chi2": None, "p": None, "dof": None, "significant": None,
                "table": table}
    chi2, p, dof, _ = chi2_contingency(table)
    return {"col": col, "chi2": chi2, "p": p, "dof": dof,
            "significant": p < alpha, "table": table}


def chi_square_summary(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    rows = []
    for col in cols:
        r = chi_square(df, col)
        if r["chi2"] is None:
            continue
        rows.append({
            "ตัวแปร": C.LABELS.get(col, col),
            "Chi-square": round(r["chi2"], 2),
            "df": r["dof"],
            "p-value": r["p"],
            "สรุป (α = 0.05)": "เกี่ยวข้องอย่างมีนัยสำคัญ" if r["significant"] else "ไม่พบความเกี่ยวข้อง",
        })
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values("Chi-square", ascending=False)
    return out

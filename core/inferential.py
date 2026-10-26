"""
คำนวณสถิติเชิงพรรณนาและเชิงอนุมานด้วย Python (หน้า 'สถิติเชิงอนุมาน')
สูตรเดียวกับไฟล์ Excel (core/excel_report.py) ผลจึงตรงกัน ใช้ยืนยันกันได้
ทุกฟังก์ชันรับข้อมูลลูกค้าที่โทรแล้ว (y เป็น yes/no) ที่ผ่าน prepare() แล้ว
"""
import math

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import linprog

from core import config as C
from core.excel_report import AGE_GROUPS, CORR_VARS, NUMERIC_VARS

AGE_BINS = [(0, 29), (30, 39), (40, 49), (50, 59), (60, 200)]           # ตรงกับ AGE_GROUPS
FREQ_BINS = [(17, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 98)]


def prepare(customers: pd.DataFrame) -> pd.DataFrame:
    """เฉพาะลูกค้าที่โทรแล้ว + target + กลุ่มอายุแบบเดียวกับไฟล์ Excel"""
    d = customers[customers[C.TARGET_COL].isin(["yes", "no"])].copy()
    for col in C.INT_COLUMNS + C.MACRO_COLUMNS:
        d[col] = pd.to_numeric(d[col]).astype(float)
    d["target"] = (d[C.TARGET_COL] == "yes").astype(int)
    d["age_group_x"] = np.select([d["age"].between(lo, hi) for lo, hi in AGE_BINS], AGE_GROUPS, "")
    return d.reset_index(drop=True)


def _verdict(p, alpha, yes_text, no_text):
    rejected = p < alpha
    return rejected, (f"ปฏิเสธ H₀: {yes_text}" if rejected else f"ไม่ปฏิเสธ H₀: {no_text}")


# ============================================================
# Descriptive
# ============================================================
def _excel_mode(s: pd.Series):
    """ฐานนิยมแบบ MODE.SNGL ของ Excel: ถ้ามีหลายค่าที่ซ้ำเท่ากัน เลือกค่าที่พบก่อนในข้อมูล"""
    counts = s.value_counts()
    if counts.empty or counts.iloc[0] < 2:
        return None
    tops = set(counts[counts == counts.iloc[0]].index)
    return next(v for v in s if v in tops)


def describe_full(d: pd.DataFrame, cols=NUMERIC_VARS) -> pd.DataFrame:
    rows = {}
    for col in cols:
        x = d[col].astype(float)
        n, sd = x.count(), x.std(ddof=1)
        rows[C.LABELS.get(col, col)] = {
            "จำนวน (n)": n,
            "ค่าเฉลี่ย": x.mean(),
            "มัธยฐาน": x.median(),
            "ฐานนิยม": _excel_mode(x),
            "SD": sd,
            "ความแปรปรวน": x.var(ddof=1),
            "ต่ำสุด": x.min(),
            "Q1": x.quantile(0.25),
            "Q3": x.quantile(0.75),
            "สูงสุด": x.max(),
            "พิสัย": x.max() - x.min(),
            "ความเบ้": stats.skew(x, bias=False),
            "ความโด่ง": stats.kurtosis(x, bias=False),
            "เฉลี่ย กลุ่มตอบรับ": x[d[C.TARGET_COL] == "yes"].mean(),
            "เฉลี่ย กลุ่มไม่ตอบรับ": x[d[C.TARGET_COL] == "no"].mean(),
            "CI 95% (±)": stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n),
        }
    return pd.DataFrame(rows)


def frequency_table(d: pd.DataFrame) -> pd.DataFrame:
    age = d["age"]
    freq = [int(age.between(lo, hi).sum()) for lo, hi in FREQ_BINS]
    out = pd.DataFrame({"ช่วงอายุ": [f"{lo}-{hi}" for lo, hi in FREQ_BINS], "ความถี่": freq})
    out["ความถี่สัมพัทธ์"] = out["ความถี่"] / out["ความถี่"].sum()
    out["ความถี่สะสม"] = out["ความถี่"].cumsum()
    return out


# ============================================================
# T-Test (Welch)
# ============================================================
def welch_ttest(d, var, group_col, g1, g2, alpha=0.05) -> dict:
    a = d.loc[d[group_col] == g1, var].astype(float)
    b = d.loc[d[group_col] == g2, var].astype(float)
    n1, n2, m1, m2, v1, v2 = len(a), len(b), a.mean(), b.mean(), a.var(ddof=1), b.var(ddof=1)
    if min(n1, n2) < 2:
        raise ValueError("แต่ละกลุ่มต้องมีข้อมูลอย่างน้อย 2 ค่า")
    se = math.sqrt(v1 / n1 + v2 / n2)
    t = (m1 - m2) / se
    df = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    p = 2 * stats.t.sf(abs(t), df)
    rejected, text = _verdict(p, alpha, "ค่าเฉลี่ยสองกลุ่มต่างกันอย่างมีนัยสำคัญ",
                              "ไม่พบความแตกต่างอย่างมีนัยสำคัญ")
    return {"groups": pd.DataFrame({"กลุ่ม": [g1, g2], "n": [n1, n2], "ค่าเฉลี่ย": [m1, m2],
                                    "ความแปรปรวน": [v1, v2]}),
            "diff": m1 - m2, "t": t, "df": df, "p": p, "t_crit": stats.t.ppf(1 - alpha / 2, df),
            "rejected": rejected, "conclusion": text}


# ============================================================
# One-way ANOVA
# ============================================================
def one_way_anova(d, var, factor, groups=None, alpha=0.05) -> dict:
    groups = groups or d[factor].value_counts().index.tolist()
    sub = d[d[factor].isin(groups)]
    grand = sub[var].mean()
    rows = []
    for g in groups:
        x = sub.loc[sub[factor] == g, var].astype(float)
        if len(x) == 0:
            continue
        rows.append({"กลุ่ม": g, "n": len(x), "ค่าเฉลี่ย": x.mean(),
                     "ความแปรปรวน": x.var(ddof=1) if len(x) > 1 else 0.0,
                     "SS ภายใน": ((x - x.mean()) ** 2).sum(),
                     "SS ระหว่าง": len(x) * (x.mean() - grand) ** 2})
    g = pd.DataFrame(rows)
    k, n = len(g), int(g["n"].sum())
    if k < 2:
        raise ValueError("ต้องมีอย่างน้อย 2 กลุ่ม")
    ssb, ssw = g["SS ระหว่าง"].sum(), g["SS ภายใน"].sum()
    dfb, dfw = k - 1, n - k
    msb, msw = ssb / dfb, ssw / dfw
    f = msb / msw
    p = stats.f.sf(f, dfb, dfw)
    table = pd.DataFrame({
        "แหล่งความแปรปรวน": ["ระหว่างกลุ่ม (Between)", "ภายในกลุ่ม (Within)", "รวม (Total)"],
        "SS": [ssb, ssw, ssb + ssw], "df": [dfb, dfw, n - 1], "MS": [msb, msw, np.nan],
        "F": [f, np.nan, np.nan], "p-value": [p, np.nan, np.nan]})
    rejected, text = _verdict(p, alpha, "ค่าเฉลี่ยอย่างน้อย 1 กลุ่มต่างกันอย่างมีนัยสำคัญ",
                              "ไม่พบความแตกต่างอย่างมีนัยสำคัญ")
    return {"groups": g, "table": table, "grand_mean": grand, "f": f, "df": (dfb, dfw), "p": p,
            "f_crit": stats.f.isf(alpha, dfb, dfw), "eta2": ssb / (ssb + ssw),
            "rejected": rejected, "conclusion": text}


# ============================================================
# Two-proportion z-test + CI
# ============================================================
def two_proportion_ztest(d, group_col, g1, g2, alpha=0.05) -> dict:
    a, b = d[d[group_col] == g1], d[d[group_col] == g2]
    n1, n2, x1, x2 = len(a), len(b), int(a["target"].sum()), int(b["target"].sum())
    if min(n1, n2) == 0:
        raise ValueError("กลุ่มที่เลือกไม่มีข้อมูล")
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    rejected, text = _verdict(p, alpha, "อัตราตอบรับสองกลุ่มต่างกันอย่างมีนัยสำคัญ",
                              "ไม่พบความแตกต่างอย่างมีนัยสำคัญ")
    return {"groups": pd.DataFrame({"กลุ่ม": [g1, g2], "n": [n1, n2], "ตอบรับ": [x1, x2],
                                    "อัตราตอบรับ": [p1, p2]}),
            "pooled": pooled, "z": z, "p": p, "z_crit": stats.norm.ppf(1 - alpha / 2),
            "rejected": rejected, "conclusion": text}


def proportion_ci(d, alpha=0.05) -> dict:
    n = len(d)
    p = d["target"].mean()
    moe = stats.norm.ppf(1 - alpha / 2) * math.sqrt(p * (1 - p) / n)
    return {"n": n, "p": p, "moe": moe, "low": p - moe, "high": p + moe}


# ============================================================
# Correlation
# ============================================================
def correlation_matrix(d, cols=CORR_VARS) -> pd.DataFrame:
    m = d[cols].astype(float).corr()
    labels = [C.LABELS.get(c, c) if c != "target" else "ผลการโทร (target)" for c in cols]
    m.index, m.columns = labels, labels
    return m


# ============================================================
# Solver: Linear Programming จัดสรรจำนวนสายโทร
# ============================================================
def segment_table(d) -> pd.DataFrame:
    rows = []
    for a in AGE_GROUPS:
        for c in ["cellular", "telephone"]:
            s = d[(d["age_group_x"] == a) & (d["contact"] == c)]
            rows.append({"กลุ่มอายุ": a, "ช่องทาง": c, "ลูกค้าในกลุ่ม": len(s),
                         "อัตราตอบรับ": s["target"].mean() if len(s) else 0.0})
    return pd.DataFrame(rows)


def optimize_calls(seg: pd.DataFrame, profit: float, cost: float, budget: float,
                   min_pct: float) -> dict:
    """
    max  Σ calls_i × (conv_i × profit − cost)
    s.t. Σ calls_i ≤ budget,  min_i ≤ calls_i ≤ pool_i,  min_i = ⌈pool_i × min_pct⌉
    """
    s = seg.copy()
    s["กำไรคาดหวังต่อสาย"] = s["อัตราตอบรับ"] * profit - cost
    s["ขั้นต่ำ"] = np.ceil(s["ลูกค้าในกลุ่ม"] * min_pct - 1e-9)
    pool, low = s["ลูกค้าในกลุ่ม"].to_numpy(float), s["ขั้นต่ำ"].to_numpy(float)
    if low.sum() > budget:
        return {"ok": False, "message": f"ทำไม่ได้: โทรขั้นต่ำรวม {low.sum():,.0f} สาย เกินงบ {budget:,.0f} สาย "
                                        "ให้เพิ่มงบหรือลด % ขั้นต่ำ", "table": s}
    res = linprog(-s["กำไรคาดหวังต่อสาย"].to_numpy(), A_ub=[np.ones(len(s))], b_ub=[budget],
                  bounds=list(zip(low, pool)), method="highs")
    if not res.success:
        return {"ok": False, "message": f"คำนวณไม่สำเร็จ: {res.message}", "table": s}
    s["จำนวนสายที่โทร"] = np.round(res.x, 2)
    s["ผู้ตอบรับคาดหวัง"] = s["จำนวนสายที่โทร"] * s["อัตราตอบรับ"]
    s["กำไรคาดหวัง"] = s["จำนวนสายที่โทร"] * s["กำไรคาดหวังต่อสาย"]

    equal = np.full(len(s), round(budget / len(s)))                     # ค่าเริ่มต้นแบบในไฟล์ Excel
    return {"ok": True, "table": s, "profit": s["กำไรคาดหวัง"].sum(),
            "calls": s["จำนวนสายที่โทร"].sum(), "yes": s["ผู้ตอบรับคาดหวัง"].sum(),
            "equal_profit": float((equal * s["กำไรคาดหวังต่อสาย"]).sum()),
            "breakeven": cost / profit if profit else np.nan}

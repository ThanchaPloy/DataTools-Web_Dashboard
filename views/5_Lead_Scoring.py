"""
หน้า 5: จัดอันดับลูกค้าด้วยคะแนนจากโมเดล ML
เว็บไม่โหลดโมเดลเอง คะแนนมาจาก Colab (Step 19 ใน notebook)
- โหมด Google Sheet: Colab เขียนคะแนนลง Sheet โดยตรง
- โหมด Excel: Colab สร้างไฟล์ scores_from_colab.xlsx แล้วนำเข้าผ่านหน้านี้
- จัดอันดับลูกค้า 'รอโทร' ว่าควรโทรหาใครก่อน
- โหมดทดสอบ: เทียบคะแนนกับผลจริงของลูกค้าที่โทรแล้ว
- ข้อมูลโมเดลจากชีต model_info
"""
import html

import pandas as pd
import streamlit as st

from core import config as C
from core import ui
from core.data_io import StorageError, import_scores, load_model_info, require_data

ui.page_header("ควรโทรหาใครก่อน",
               "จัดอันดับรายชื่อด้วยคะแนนโอกาสตอบรับจากโมเดล Machine Learning (ให้คะแนนผ่าน Google Colab)",
               eyebrow="Machine Learning")

customers, _ = require_data()
info = load_model_info()
THRESHOLD = float(info.get("threshold", 0.2) or 0.2)
PROFIT = float(info.get("profit_per_yes", C.PROFIT_PER_YES) or C.PROFIT_PER_YES)
COST = float(info.get("cost_per_call", C.COST_PER_CALL) or C.COST_PER_CALL)

df = customers.copy()
df["expected_profit"] = df["prob_yes"] * PROFIT - COST
scored = df["prob_yes"].notna()

# ------------------------------------------------------------
# นำเข้าคะแนนจาก Colab (ใช้ในโหมด Excel: Colab เขียนลงไฟล์ในเครื่องเราไม่ได้)
# ------------------------------------------------------------
if msg := st.session_state.pop("score_import_msg", None):
    st.success(msg)
if C.STORAGE == "excel":
    with st.expander("นำเข้าคะแนนจาก Colab (scores_from_colab.xlsx)", expanded=not scored.any(),
                     icon=":material/upload_file:"):
        st.markdown(
            "1) ใน Colab รันบล็อก Step 19 (ไฟล์ `colab/step19_score_excel.py`) แล้วอัปโหลด "
            f"`{C.EXCEL_PATH.name}` จากโฟลเดอร์ `data` ของเว็บ  \n"
            "2) Colab จะดาวน์โหลดไฟล์ `scores_from_colab.xlsx` ให้ นำมาอัปโหลดที่นี่  \n"
            "3) ถ้าเพิ่มหรือแก้ลูกค้าหลังจากอัปโหลดไฟล์ไป Colab ลูกค้าเหล่านั้นจะยังไม่มีคะแนน ให้ทำซ้ำอีกรอบ")
        up = st.file_uploader("ไฟล์คะแนนจาก Colab", type=["xlsx"], label_visibility="collapsed")
        if up is not None and st.button("นำเข้าคะแนน", type="primary", icon=":material/download_done:"):
            try:
                sheets = pd.read_excel(up, sheet_name=None, dtype={C.ID_COL: str})
                if "scores" not in sheets:
                    raise ValueError("ไม่พบชีต 'scores' ในไฟล์ (ต้องเป็นไฟล์ที่ได้จาก Colab Step 19)")
                with st.spinner("กำลังนำเข้า..."):
                    n_ok, n_missing = import_scores(sheets["scores"], sheets.get("model_info"))
            except (ValueError, StorageError) as e:
                st.error(str(e))
                st.stop()
            note = f" (ไม่พบในข้อมูลปัจจุบัน {n_missing:,} รหัส เช่น ลูกค้าที่ถูกลบไปแล้ว)" if n_missing else ""
            st.session_state.score_import_msg = f"นำเข้าคะแนนเรียบร้อย {n_ok:,} คน{note}"
            st.rerun()

if not scored.any():
    how = ("รัน Step 19 ใน Colab แล้วนำเข้าไฟล์คะแนนในกล่องด้านบน" if C.STORAGE == "excel" else
           "เปิด notebook ใน Colab แล้วรันให้ถึง Step 19 จากนั้นกด 'โหลดข้อมูลล่าสุด' ที่เมนูด้านซ้าย")
    ui.card("ยังไม่มีคะแนนจากโมเดล", how)
    st.stop()

SHOW = {"rank": "อันดับ", C.ID_COL: "รหัสลูกค้า", "age": "อายุ", "job": "อาชีพ",
        "education": "การศึกษา", "contact": "ช่องทาง", "persona": "กลุ่มลูกค้า",
        "prob_yes": "โอกาสตอบรับ", "expected_profit": "กำไรคาดหวัง", "action": "คำแนะนำ"}
COLCFG = {
    "โอกาสตอบรับ": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
    "กำไรคาดหวัง": st.column_config.NumberColumn(format="%.1f"),
}


def ranked(d: pd.DataFrame) -> pd.DataFrame:
    out = d.sort_values("prob_yes", ascending=False).copy()
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


tab_rank, tab_about = st.tabs(["จัดอันดับรายชื่อ", "เกี่ยวกับโมเดล"])

# ============================================================
# แท็บ 1: จัดอันดับรายชื่อ
# ============================================================
with tab_rank:
    demo = st.toggle("โหมดทดสอบ: จัดอันดับลูกค้าที่โทรแล้ว แล้วเทียบกับผลจริง",
                     help="ใช้สาธิตว่าโมเดลจัดอันดับได้แม่นแค่ไหน")
    if demo:
        pool = df[df[C.TARGET_COL].isin(["yes", "no"]) & scored]
    else:
        pending = df[df[C.TARGET_COL] == "pending"]
        waiting = pending[pending["prob_yes"].isna()]
        pool = pending[pending["prob_yes"].notna()]
        if len(waiting):
            st.warning(f"มีลูกค้ารอโทร {len(waiting):,} คนที่ยังไม่มีคะแนน "
                       f"({', '.join(waiting[C.ID_COL].head(8))}{' ...' if len(waiting) > 8 else ''}) "
                       + ("ให้รัน Step 19 ใน Colab แล้วนำเข้าไฟล์คะแนนอีกครั้ง" if C.STORAGE == "excel"
                          else "ให้รัน Step 19 ใน Colab แล้วกด 'โหลดข้อมูลล่าสุด'"))

    if len(pool) == 0:
        st.info("ยังไม่มีลูกค้าสถานะ 'รอโทร' ที่มีคะแนน เพิ่มได้ที่หน้า 'เพิ่มลูกค้าใหม่' หรือเปิดโหมดทดสอบ")
    else:
        r = ranked(pool)
        first = r[r["prob_yes"] >= THRESHOLD]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ui.kpi("รายชื่อที่จัดอันดับ", ui.fmt_int(len(r)), "โทรแล้ว (ทดสอบ)" if demo else "รอโทร")
        with c2:
            ui.kpi("ควรโทรก่อน", ui.fmt_int(len(first)),
                   f"โอกาสตอบรับ ≥ {ui.fmt_pct(THRESHOLD, 0)}", "teal")
        with c3:
            ui.kpi("โอกาสตอบรับเฉลี่ยของกลุ่มนี้",
                   ui.fmt_pct(first["prob_yes"].mean() if len(first) else 0),
                   f"ทั้งรายชื่อ {ui.fmt_pct(r['prob_yes'].mean())}", "teal")
        with c4:
            ui.kpi("กำไรคาดหวัง (โทรเฉพาะกลุ่มนี้)", f"{first['expected_profit'].sum():,.0f}",
                   f"โทรทุกคน {r['expected_profit'].sum():,.0f}", "amber")

        show = dict(SHOW)
        if demo:
            r["actual"] = (r[C.TARGET_COL] == "yes").astype(int)
            n10 = max(len(r) // 10, 1)
            top10, bot10, allr = (r.head(n10)["actual"].mean(), r.tail(n10)["actual"].mean(),
                                  r["actual"].mean())
            st.write("")
            ui.card("ผลทดสอบกับข้อมูลจริง",
                    f"10% ที่โมเดลจัดไว้บนสุด ตอบรับจริง <b>{ui.fmt_pct(top10)}</b> · "
                    f"ทั้งหมด {ui.fmt_pct(allr)} · 10% ล่างสุด {ui.fmt_pct(bot10)} "
                    f"(บนสุดดีกว่าค่าเฉลี่ย {top10 / max(allr, 1e-9):.1f} เท่า) "
                    "หมายเหตุ: ข้อมูลชุดนี้ซ้อนกับข้อมูลที่ใช้เทรนบางส่วน ตัวเลขจึงอาจดีกว่าตอนใช้จริง")
            r[C.TARGET_COL] = r[C.TARGET_COL].map(C.STATUS_LABELS)
            show[C.TARGET_COL] = "ผลจริง"

        st.write("")
        only_first = st.checkbox("แสดงเฉพาะ 'ควรโทรก่อน'", value=False)
        table = (first if only_first else r)[list(show)].rename(columns=show)
        st.dataframe(table, hide_index=True, width="stretch", column_config=COLCFG,
                     height=min(460, 36 * (len(table) + 1) + 4))
        st.download_button("ดาวน์โหลดรายชื่อตามอันดับ (CSV)",
                           table.to_csv(index=False).encode("utf-8-sig"),
                           "call_priority_list.csv", icon=":material/download:")

# ============================================================
# แท็บ 2: เกี่ยวกับโมเดล
# ============================================================
with tab_about:
    left, right = st.columns([1, 1])
    with left:
        ui.card("โมเดลทำงานอย่างไร",
                "โมเดลเรียนจากการโทรในอดีตว่าลูกค้าแบบไหนตอบรับ แล้วให้คะแนนโอกาสตอบรับของลูกค้าแต่ละคน "
                "ใช้เฉพาะข้อมูลที่รู้ก่อนโทร (ข้อมูลส่วนตัว การเงิน ช่องทาง และประวัติการติดต่อ) "
                "ความน่าจะเป็นผ่านการ calibrate แล้ว จึงนำไปคำนวณกำไรคาดหวังได้")
        ui.card("ขั้นตอนการให้คะแนน",
                "เว็บบันทึกลูกค้าลงไฟล์ข้อมูล → Colab อ่านลูกค้าแล้วให้คะแนนด้วยโมเดลที่เทรนไว้ (Step 19) "
                "→ คะแนนกลับมาที่เว็บ (โหมด Excel: นำเข้าไฟล์ scores_from_colab.xlsx) → เว็บแสดงอันดับ "
                "ถ้าแก้ข้อมูลลูกค้า คะแนนของแถวนั้นจะถูกล้าง และต้องรัน Step 19 ใหม่")
        ui.card("กำไรคาดหวัง",
                f"= โอกาสตอบรับ × {PROFIT:g} − {COST:g} (กำไรต่อคนที่ตอบรับและต้นทุนต่อสายเป็นค่าสมมติ) "
                "ค่าบวก = โทรแล้วคุ้ม")
    with right:
        # ป้ายภาษาไทย และรูปแบบการแสดงผลของค่าจากชีต model_info
        INFO_LABELS = {
            "model": ("โมเดลที่ใช้", "text"),
            "test_roc_auc": ("ROC-AUC บน test set", "num"),
            "test_recall": ("Recall บน test set", "pct"),
            "test_f1": ("F1 บน test set", "num"),
            "threshold": ("เกณฑ์ 'ควรโทรก่อน' (โอกาสตอบรับขั้นต่ำ)", "pct"),
            "profit_per_yes": ("กำไรต่อคนที่ตอบรับ (สมมติ)", "money"),
            "cost_per_call": ("ต้นทุนต่อสาย (สมมติ)", "money"),
            "n_scored": ("จำนวนลูกค้าที่ Colab ให้คะแนน", "int"),
            "scored_at": ("ให้คะแนนล่าสุดเมื่อ", "text"),
        }

        def fmt(value, kind):
            try:
                if kind == "pct":
                    return ui.fmt_pct(float(value))
                if kind == "num":
                    return f"{float(value):.3f}"
                if kind == "int":
                    return f"{int(float(value)):,} คน"
                if kind == "money":
                    return f"{float(value):,.0f}"
            except (TypeError, ValueError):
                pass
            return str(value)

        rows = [("ลูกค้าที่มีคะแนน", f"{int(scored.sum()):,} จาก {len(df):,} คน")]
        rows += [(label, fmt(info[key], kind)) for key, (label, kind) in INFO_LABELS.items()
                 if key in info and str(info[key]) != ""]
        rows += [(k, str(v)) for k, v in info.items()            # ค่าอื่นที่ไม่รู้จัก แสดงตามเดิม
                 if k not in INFO_LABELS and k != "features"]
        # ตาราง HTML: ขยายตามเนื้อหา แสดงครบทุกแถวและทุกตัวอักษร ไม่ต้องเลื่อน
        body = "".join(f"<tr><td>{html.escape(k)}</td><td>{html.escape(v)}</td></tr>" for k, v in rows)
        st.markdown(f'<table class="info-table"><thead><tr><th>รายการ</th><th>ค่า</th></tr></thead>'
                    f'<tbody>{body}</tbody></table>', unsafe_allow_html=True)

        if info.get("features"):
            st.markdown("**ฟีเจอร์ที่โมเดลใช้**")
            st.markdown(" ".join(ui.badge(f.strip(), "good")
                                 for f in str(info["features"]).split(",")),
                        unsafe_allow_html=True)
        if not info:
            st.caption("ยังไม่มีชีต model_info (Colab จะสร้างให้ตอนรัน Step 19)")

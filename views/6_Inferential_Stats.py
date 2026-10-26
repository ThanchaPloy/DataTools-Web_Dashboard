"""
หน้า 6: สถิติเชิงอนุมาน
แสดงผลชุดเดียวกับไฟล์ Excel วิเคราะห์สถิติ (core/excel_report.py) แต่คำนวณด้วย Python
และให้ผู้ใช้เลือกตัวแปรที่จะทดสอบเองได้
คำนวณจากลูกค้าที่โทรแล้วเท่านั้น (ไม่นับ 'รอโทร')
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import config as C
from core import inferential as I
from core import ui
from core.data_io import require_data

ui.page_header("สถิติเชิงอนุมาน",
               "ทดสอบสมมติฐานว่าความแตกต่างที่เห็นในข้อมูลเกิดขึ้นจริงหรือเป็นแค่ความบังเอิญ "
               "ผลตรงกับไฟล์ Excel วิเคราะห์สถิติ แต่เลือกตัวแปรเองได้",
               eyebrow="วิเคราะห์")

customers, _ = require_data()
d = I.prepare(customers)
if d["target"].nunique() < 2:
    st.info("ต้องมีลูกค้าที่โทรแล้วทั้งกลุ่ม 'ตอบรับ' และ 'ไม่ตอบรับ' จึงจะทดสอบได้")
    st.stop()

NUMERIC = list(I.NUMERIC_VARS)
CATEGORICAL = ["job", "marital", "education", "default", "housing", "loan", "contact",
               "month", "day_of_week", "poutcome", "age_group_x", C.TARGET_COL]
LBL = {**C.LABELS, "age_group_x": "กลุ่มอายุ", C.TARGET_COL: "ผลการโทร"}


def lbl(col):
    return LBL.get(col, col)


def num(x, digits=4):
    return "-" if pd.isna(x) else f"{x:,.{digits}f}"


def pval(p):
    return "< 0.0001" if p < 0.0001 else f"{p:.4f}"


def result_box(h0, h1, stats_rows, res):
    """กล่องสรุป H₀ / ค่าสถิติ / p-value / ข้อสรุปภาษาไทย"""
    kind = "good" if res["rejected"] else "warn"
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in stats_rows)
    st.markdown(
        f'<div class="card"><h4>สมมติฐาน</h4>'
        f'<p><b>H₀:</b> {h0}<br><b>H₁:</b> {h1}</p>'
        f'<table class="info-table" style="margin:0.7rem 0">{rows}</table>'
        f'<p>{ui.badge(res["conclusion"], kind)}</p></div>', unsafe_allow_html=True)


with st.sidebar:
    alpha = st.select_slider("ระดับนัยสำคัญ (α)", options=[0.01, 0.05, 0.10], value=0.05)

c1, c2, c3 = st.columns(3)
with c1:
    ui.kpi("ลูกค้าที่ใช้ทดสอบ", ui.fmt_int(len(d)), "เฉพาะที่โทรแล้ว")
with c2:
    ui.kpi("อัตราตอบรับ", ui.fmt_pct(d["target"].mean()), "สัดส่วนผู้ตอบรับ", "teal")
with c3:
    ui.kpi("ระดับนัยสำคัญ (α)", f"{alpha:.2f}", "ปรับได้ที่แถบด้านซ้าย", "amber")
st.write("")

t_desc, t_t, t_anova, t_z, t_corr, t_solver = st.tabs(
    ["Descriptive", "T-Test", "ANOVA", "Z-Test", "Correlation", "Solver (จัดสรรสายโทร)"])

# ============================================================
# 1) Descriptive
# ============================================================
with t_desc:
    st.subheader("สถิติเชิงพรรณนา (ตัวแปรเชิงปริมาณ 9 ตัว)")
    desc = I.describe_full(d)
    st.dataframe(desc.style.format(lambda v: "-" if pd.isna(v) else
                                   (f"{v:,.0f}" if float(v).is_integer() else f"{v:,.3f}")),
                 width="stretch", height=(len(desc) + 1) * 35 + 3)
    st.caption("ความเบ้/ความโด่งใช้สูตรแบบเดียวกับ SKEW/KURT ของ Excel · Q1/Q3 แบบ QUARTILE.INC · "
               "CI 95% (±) คือค่าคลาดเคลื่อนของค่าเฉลี่ยแบบ CONFIDENCE.T")

    st.subheader("ตารางแจกแจงความถี่และ Histogram")
    left, right = st.columns([1, 1.6])
    with left:
        freq = I.frequency_table(d)
        st.dataframe(freq.style.format({"ความถี่": "{:,}", "ความถี่สัมพัทธ์": "{:.1%}",
                                        "ความถี่สะสม": "{:,}"}),
                     hide_index=True, width="stretch")
    with right:
        var = st.selectbox("ตัวแปรสำหรับ Histogram", NUMERIC, format_func=lbl, key="hist_var")
        split = st.toggle("แยกตามผลการโทร", value=False)
        fig = px.histogram(d, x=var, color=d["target"].map({1: "ตอบรับ", 0: "ไม่ตอบรับ"}) if split else None,
                           nbins=30, barmode="overlay", opacity=0.75 if split else 1,
                           color_discrete_map=ui.STATUS_COLORS,
                           labels={var: lbl(var), "color": "ผลการโทร"})
        fig.update_layout(height=330, yaxis_title="จำนวนลูกค้า", margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")

# ============================================================
# 2) T-Test
# ============================================================
with t_t:
    st.subheader("Welch's t-test: เทียบค่าเฉลี่ยของสองกลุ่ม")
    a, b, c_ = st.columns(3)
    var = a.selectbox("ตัวแปรเชิงปริมาณ", NUMERIC, format_func=lbl, key="t_var")
    grp = b.selectbox("แบ่งกลุ่มตาม", CATEGORICAL, index=CATEGORICAL.index(C.TARGET_COL),
                      format_func=lbl, key="t_grp")
    levels = d[grp].value_counts().index.tolist()
    default = ["yes", "no"] if grp == C.TARGET_COL else levels[:2]
    pair = c_.multiselect("เลือก 2 กลุ่ม", levels, default=default, max_selections=2, key=f"t_pair_{grp}")
    if len(pair) != 2:
        st.info("เลือกให้ครบ 2 กลุ่ม")
    else:
        try:
            r = I.welch_ttest(d, var, grp, pair[0], pair[1], alpha)
        except ValueError as e:
            st.warning(str(e))
        else:
            left, right = st.columns([1.1, 1])
            with left:
                result_box(f"ค่าเฉลี่ย{lbl(var)}ของกลุ่ม {pair[0]} เท่ากับกลุ่ม {pair[1]} (μ₁ = μ₂)",
                           "ค่าเฉลี่ยสองกลุ่มไม่เท่ากัน (μ₁ ≠ μ₂)",
                           [("ผลต่างค่าเฉลี่ย", num(r["diff"])), ("ค่า t", num(r["t"])),
                            ("df (Welch)", num(r["df"], 2)), ("p-value (สองหาง)", pval(r["p"])),
                            (f"ค่าวิกฤต t (α = {alpha})", f"± {num(r['t_crit'])}")], r)
            with right:
                st.dataframe(r["groups"].style.format({"n": "{:,}", "ค่าเฉลี่ย": "{:,.3f}",
                                                        "ความแปรปรวน": "{:,.3f}"}),
                             hide_index=True, width="stretch")
                sub = d[d[grp].isin(pair)]
                fig = px.box(sub, x=grp, y=var, color=grp, labels={grp: lbl(grp), var: lbl(var)},
                             color_discrete_map={"yes": ui.TEAL, "no": ui.CORAL})
                fig.update_layout(height=280, showlegend=False, margin=dict(t=10))
                st.plotly_chart(fig, width="stretch")
    st.caption("ใช้ Welch's t-test (ไม่สมมติว่าความแปรปรวนเท่ากัน) เหมือน T.TEST(…, 2, 3) ในไฟล์ Excel")

# ============================================================
# 3) ANOVA
# ============================================================
with t_anova:
    st.subheader("One-way ANOVA: เทียบค่าเฉลี่ยมากกว่า 2 กลุ่ม")
    a, b = st.columns(2)
    var = a.selectbox("ตัวแปรเชิงปริมาณ", NUMERIC, format_func=lbl, key="a_var")
    factors = [c for c in CATEGORICAL if c != C.TARGET_COL]
    factor = b.selectbox("ปัจจัย (แบ่งกลุ่มตาม)", factors, index=factors.index("marital"),
                         format_func=lbl, key="a_fac")
    levels = d[factor].value_counts().index.tolist()
    default = [m for m in ["married", "single", "divorced"] if m in levels] if factor == "marital" else levels
    groups = st.multiselect("กลุ่มที่นำมาเทียบ", levels, default=default, key=f"a_groups_{factor}")
    if len(groups) < 2:
        st.info("เลือกอย่างน้อย 2 กลุ่ม")
    else:
        try:
            r = I.one_way_anova(d, var, factor, groups, alpha)
        except ValueError as e:
            st.warning(str(e))
        else:
            left, right = st.columns([1.1, 1])
            with left:
                result_box(f"ค่าเฉลี่ย{lbl(var)}ของทุกกลุ่ม{lbl(factor)}เท่ากัน",
                           "มีอย่างน้อย 1 กลุ่มที่ค่าเฉลี่ยต่างจากกลุ่มอื่น",
                           [("ค่า F", num(r["f"])), ("df", f"{r['df'][0]}, {r['df'][1]:,}"),
                            ("p-value", pval(r["p"])), (f"ค่าวิกฤต F (α = {alpha})", num(r["f_crit"])),
                            ("η² (ขนาดอิทธิพล)", num(r["eta2"]))], r)
            with right:
                g = r["groups"][["กลุ่ม", "n", "ค่าเฉลี่ย", "ความแปรปรวน"]]
                st.dataframe(g.style.format({"n": "{:,}", "ค่าเฉลี่ย": "{:,.3f}",
                                             "ความแปรปรวน": "{:,.3f}"}),
                             hide_index=True, width="stretch")
            st.markdown("**ตาราง ANOVA**")
            st.dataframe(r["table"].style.format({"SS": "{:,.3f}", "df": "{:,.0f}", "MS": "{:,.3f}",
                                                  "F": "{:,.4f}", "p-value": "{:.6f}"}, na_rep=""),
                         hide_index=True, width="stretch")
            st.caption("η² < 0.01 ถือว่าผลเล็กมาก · 0.06 ปานกลาง · 0.14 ขึ้นไปผลใหญ่ "
                       "(มีนัยสำคัญทางสถิติไม่ได้แปลว่าต่างกันมากในทางธุรกิจ)")

# ============================================================
# 4) Z-Test (สัดส่วน)
# ============================================================
with t_z:
    st.subheader("Two-proportion z-test: เทียบอัตราตอบรับของสองกลุ่ม")
    a, b = st.columns(2)
    zf = [c for c in CATEGORICAL if c != C.TARGET_COL]
    grp = a.selectbox("แบ่งกลุ่มตาม", zf, index=zf.index("contact"), format_func=lbl, key="z_grp")
    levels = d[grp].value_counts().index.tolist()
    default = ["cellular", "telephone"] if grp == "contact" else levels[:2]
    pair = b.multiselect("เลือก 2 กลุ่ม", levels, default=default, max_selections=2, key=f"z_pair_{grp}")
    if len(pair) != 2:
        st.info("เลือกให้ครบ 2 กลุ่ม")
    else:
        try:
            r = I.two_proportion_ztest(d, grp, pair[0], pair[1], alpha)
        except ValueError as e:
            st.warning(str(e))
        else:
            left, right = st.columns([1.1, 1])
            with left:
                result_box(f"อัตราตอบรับของกลุ่ม {pair[0]} เท่ากับกลุ่ม {pair[1]} (p₁ = p₂)",
                           "อัตราตอบรับสองกลุ่มไม่เท่ากัน (p₁ ≠ p₂)",
                           [("ผลต่างอัตราตอบรับ",
                             ui.fmt_pct(r["groups"]["อัตราตอบรับ"][0] - r["groups"]["อัตราตอบรับ"][1], 2)),
                            ("สัดส่วนรวม (pooled)", ui.fmt_pct(r["pooled"], 2)), ("ค่า z", num(r["z"])),
                            ("p-value (สองหาง)", pval(r["p"])),
                            (f"ค่าวิกฤต z (α = {alpha})", f"± {num(r['z_crit'])}")], r)
            with right:
                st.dataframe(r["groups"].style.format({"n": "{:,}", "ตอบรับ": "{:,}",
                                                        "อัตราตอบรับ": "{:.2%}"}),
                             hide_index=True, width="stretch")
                fig = px.bar(r["groups"], x="กลุ่ม", y="อัตราตอบรับ", text_auto=".1%")
                fig.update_traces(marker_color=ui.PRIMARY)
                fig.update_layout(height=250, yaxis_tickformat=".0%", margin=dict(t=10))
                st.plotly_chart(fig, width="stretch")

    ci = I.proportion_ci(d, alpha)
    st.markdown(f"**ช่วงความเชื่อมั่น {1 - alpha:.0%} ของอัตราตอบรับรวม**")
    k1, k2, k3 = st.columns(3)
    with k1:
        ui.kpi("อัตราตอบรับ", ui.fmt_pct(ci["p"], 2), f"n = {ci['n']:,}", "teal")
    with k2:
        ui.kpi("ค่าคลาดเคลื่อน", f"± {ui.fmt_pct(ci['moe'], 2)}", "Margin of error")
    with k3:
        ui.kpi("ช่วงความเชื่อมั่น", f"{ui.fmt_pct(ci['low'], 2)} – {ui.fmt_pct(ci['high'], 2)}",
               "ประมาณการอัตราตอบรับจริง")

# ============================================================
# 5) Correlation
# ============================================================
with t_corr:
    st.subheader("ค่าสหสัมพันธ์ (Pearson) ระหว่างตัวแปร")
    m = I.correlation_matrix(d)
    fig = go.Figure(go.Heatmap(z=m.values, x=m.columns, y=m.index, zmin=-1, zmax=1,
                               colorscale=[[0, ui.CORAL], [0.5, "#FFFFFF"], [1, ui.PRIMARY]],
                               text=m.round(2).values, texttemplate="%{text}",
                               hovertemplate="%{y} × %{x}<br>r = %{z:.3f}<extra></extra>"))
    fig.update_layout(height=560, yaxis_autorange="reversed", margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")

    tgt = m.iloc[-1, :-1].sort_values(key=abs, ascending=False)
    top = tgt.index[0]
    ui.card("อ่านผลอย่างไร",
            f"ตัวแปรที่สัมพันธ์กับผลการโทรมากที่สุดคือ <b>{top}</b> (r = {tgt.iloc[0]:.3f}) "
            "ค่าใกล้ +1 / −1 แปลว่าสัมพันธ์กันมาก ค่าใกล้ 0 แปลว่าแทบไม่สัมพันธ์ · "
            "ระยะเวลาสนทนารู้ได้หลังโทรเท่านั้น จึงไม่ได้ใช้ในโมเดลจัดอันดับ · "
            "ตัวแปรเศรษฐกิจ (อัตราจ้างงาน, Euribor, จำนวนผู้มีงานทำ) สัมพันธ์กันเองสูงมาก")

# ============================================================
# 6) Solver (Linear Programming)
# ============================================================
with t_solver:
    st.subheader("จัดสรรจำนวนสายโทรให้กำไรคาดหวังสูงสุด")
    st.caption("ปรับค่าสมมติด้วยแถบเลื่อน ระบบหาคำตอบที่ดีที่สุดด้วย Linear Programming "
               "(แบบเดียวกับ Solver วิธี Simplex LP ในไฟล์ Excel)")
    a, b, c_, e = st.columns(4)
    profit = a.slider("กำไรต่อคนที่ตอบรับ", 20, 500, int(C.PROFIT_PER_YES), 10)
    cost = b.slider("ต้นทุนต่อสาย", 1, 100, int(C.COST_PER_CALL), 1)
    budget = c_.slider("งบจำนวนสายทั้งหมด", 100, max(len(d), 200), min(800, len(d)), 50)
    min_pct = e.slider("โทรขั้นต่ำต่อกลุ่ม (%)", 0, 20, 5, 1) / 100

    seg = I.segment_table(d)
    r = I.optimize_calls(seg, profit, cost, budget, min_pct)
    if not r["ok"]:
        st.error(r["message"])
    else:
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            ui.kpi("กำไรคาดหวังสูงสุด", f"{r['profit']:,.0f}",
                   f"แบ่งเท่ากันทุกกลุ่มได้ {r['equal_profit']:,.0f}", "teal")
        with k2:
            ui.kpi("จำนวนสายที่ควรโทร", f"{r['calls']:,.0f}", f"จากงบ {budget:,} สาย")
        with k3:
            ui.kpi("ผู้ตอบรับคาดหวัง", f"{r['yes']:,.1f}", "คน", "teal")
        with k4:
            ui.kpi("จุดคุ้มทุน", ui.fmt_pct(r["breakeven"]), "อัตราตอบรับขั้นต่ำที่โทรแล้วคุ้ม", "amber")
        st.write("")

        t = r["table"].copy()
        t["กลุ่ม"] = t["กลุ่มอายุ"] + " · " + t["ช่องทาง"]
        show = t[["กลุ่มอายุ", "ช่องทาง", "ลูกค้าในกลุ่ม", "อัตราตอบรับ", "กำไรคาดหวังต่อสาย",
                  "ขั้นต่ำ", "จำนวนสายที่โทร", "ผู้ตอบรับคาดหวัง", "กำไรคาดหวัง"]]
        st.dataframe(show.style.format({"ลูกค้าในกลุ่ม": "{:,}", "อัตราตอบรับ": "{:.1%}",
                                        "กำไรคาดหวังต่อสาย": "{:,.2f}", "ขั้นต่ำ": "{:,.0f}",
                                        "จำนวนสายที่โทร": "{:,.0f}", "ผู้ตอบรับคาดหวัง": "{:,.1f}",
                                        "กำไรคาดหวัง": "{:,.2f}"}),
                     hide_index=True, width="stretch", height=(len(show) + 1) * 35 + 3)

        fig = go.Figure()
        fig.add_bar(y=t["กลุ่ม"], x=t["ลูกค้าในกลุ่ม"], orientation="h", name="ลูกค้าในกลุ่ม",
                    marker_color=ui.GRID)
        fig.add_bar(y=t["กลุ่ม"], x=t["จำนวนสายที่โทร"], orientation="h",
                    name="จำนวนสายที่ควรโทร (เขียว = คุ้มค่า, แดง = โทรแค่ขั้นต่ำ)",
                    marker_color=[ui.TEAL if v > 0 else ui.CORAL for v in t["กำไรคาดหวังต่อสาย"]])
        fig.update_layout(barmode="overlay", height=380, xaxis_title="จำนวนสาย",
                          yaxis_autorange="reversed", legend=dict(orientation="h", y=-0.2),
                          margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")

        worth = t[t["กำไรคาดหวังต่อสาย"] > 0]
        if worth.empty:
            msg = (f"ทุกกลุ่มมีอัตราตอบรับต่ำกว่าจุดคุ้มทุน ({ui.fmt_pct(r['breakeven'])}) "
                   "คำตอบที่ดีที่สุดจึงโทรแค่ขั้นต่ำตามนโยบาย ควรใช้คะแนนจากโมเดล ML "
                   "เลือกเฉพาะลูกค้าที่มีโอกาสสูงแทนการโทรทั้งกลุ่ม")
        else:
            msg = ("กลุ่มที่คุ้มค่าโทร (อัตราตอบรับสูงกว่าจุดคุ้มทุน): "
                   + ", ".join(f"<b>{g}</b> ({p:.1%})" for g, p in zip(worth["กลุ่ม"], worth["อัตราตอบรับ"]))
                   + " · กลุ่มอื่นโทรเฉพาะขั้นต่ำ")
        ui.card("ข้อสรุป", msg)
        st.caption("ตัวแปรตัดสินใจ: จำนวนสายต่อกลุ่ม · เป้าหมาย: กำไรคาดหวังรวมสูงสุด · "
                   "ข้อจำกัด: รวมไม่เกินงบ, ไม่เกินจำนวนลูกค้าในกลุ่ม, ไม่ต่ำกว่าขั้นต่ำ · "
                   "Excel ให้คำตอบเดียวกันเมื่อใส่ค่าสมมติชุดเดียวกันแล้วกด Solve")

"""
หน้า 3: บทวิเคราะห์
- Insight สำคัญ (คำนวณอัตโนมัติ)
- อัตราตอบรับแยกตาม 5 มิติ
- สถิติเชิงพรรณนา + Chi-square test
คำนวณจากลูกค้าที่โทรแล้วเท่านั้น (ไม่นับ 'รอโทร')
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from core import config as C
from core import ui
from core.analytics import (called_only, chi_square, chi_square_summary, compare_groups,
                            conversion_by, describe_numeric, kpis)
from core.data_io import add_derived, require_data

ui.page_header("บทวิเคราะห์อัตราตอบรับ",
               "ลูกค้าแบบไหนตอบรับมากที่สุด ควรติดต่อช่องทางไหน เมื่อไร และภาวะเศรษฐกิจมีผลอย่างไร",
               eyebrow="วิเคราะห์")

customers, _ = require_data()

df = add_derived(customers)
k = kpis(df)
if k["called"] == 0:
    st.info("ยังไม่มีลูกค้าที่โทรแล้ว จึงยังวิเคราะห์ไม่ได้")
    st.stop()
OVERALL = k["conversion"]
CATEGORICAL = [c for dims in list(C.DIMENSIONS.values())[:4] for c in dims]

c1, c2, c3 = st.columns(3)
with c1:
    ui.kpi("ลูกค้าที่โทรแล้ว", ui.fmt_int(k["called"]), "ใช้ในการวิเคราะห์หน้านี้")
with c2:
    ui.kpi("อัตราตอบรับเฉลี่ย", ui.fmt_pct(k["conversion"]), "เส้นประในทุกกราฟ", "teal")
with c3:
    ui.kpi("ตอบรับ", ui.fmt_int(k["yes"]), "คน", "teal")
st.write("")

tab_insight, tab_dim, tab_stat = st.tabs(["Insight สำคัญ", "อัตราตอบรับ 5 มิติ", "สถิติและการทดสอบ"])

# ============================================================
# แท็บ 1: Insight สำคัญ (หากลุ่มที่ตอบรับสูง / ต่ำกว่าค่าเฉลี่ยมากที่สุด)
# ============================================================
with tab_insight:
    MIN_CONTACTS = 30
    rows = []
    for col in CATEGORICAL:
        t = conversion_by(df, col)
        t = t[t["contacts"] >= MIN_CONTACTS]
        for _, r in t.iterrows():
            rows.append({"col": col, "group": r[col], "conversion": r["conversion"],
                         "contacts": r["contacts"], "lift": r["conversion"] / OVERALL})
    groups = pd.DataFrame(rows)

    st.markdown("##### กลุ่มที่ตอบรับสูงกว่าค่าเฉลี่ยมากที่สุด")
    top = groups.sort_values("lift", ascending=False).head(4)
    cols = st.columns(4)
    for c, (_, r) in zip(cols, top.iterrows()):
        with c:
            ui.kpi(f"{C.LABELS.get(r['col'], r['col'])}: {r['group']}",
                   ui.fmt_pct(r["conversion"]),
                   f"{r['lift']:.1f} เท่าของค่าเฉลี่ย · {int(r['contacts']):,} คน", "teal")

    st.write("")
    st.markdown("##### กลุ่มที่ตอบรับต่ำกว่าค่าเฉลี่ยมากที่สุด")
    bottom = groups.sort_values("lift").head(4)
    cols = st.columns(4)
    for c, (_, r) in zip(cols, bottom.iterrows()):
        with c:
            ui.kpi(f"{C.LABELS.get(r['col'], r['col'])}: {r['group']}",
                   ui.fmt_pct(r["conversion"]),
                   f"{r['lift']:.1f} เท่าของค่าเฉลี่ย · {int(r['contacts']):,} คน", "coral")
    st.caption(f"นับเฉพาะกลุ่มที่มีอย่างน้อย {MIN_CONTACTS} คน เพื่อไม่ให้กลุ่มเล็กมากบิดผล")

# ============================================================
# แท็บ 2: อัตราตอบรับแยกตาม 5 มิติ
# ============================================================
with tab_dim:
    dim = st.segmented_control("มิติ", list(C.DIMENSIONS), default=list(C.DIMENSIONS)[0])
    dim = dim or list(C.DIMENSIONS)[0]
    variables = C.DIMENSIONS[dim]

    if dim.startswith("5"):
        # ตัวแปรเศรษฐกิจเป็นตัวเลขต่อเนื่อง: เทียบการกระจายระหว่างตอบรับ / ไม่ตอบรับ
        called = called_only(df)
        called["ผลการโทร"] = called[C.TARGET_COL].map(C.STATUS_LABELS)
        grid = st.columns(2)
        for i, col in enumerate(variables):
            fig = px.box(called, x="ผลการโทร", y=col, color="ผลการโทร",
                         color_discrete_map=ui.STATUS_COLORS, title=C.LABELS[col],
                         labels={col: ""})
            fig.update_layout(showlegend=False, height=320)
            grid[i % 2].plotly_chart(fig, width="stretch")
        st.caption("ถ้ากล่องของ 'ตอบรับ' กับ 'ไม่ตอบรับ' อยู่คนละระดับ แปลว่าตัวแปรนั้นเกี่ยวข้องกับการตอบรับ")
    else:
        grid = st.columns(2)
        for i, col in enumerate(variables):
            t = conversion_by(df, col)
            fig = px.bar(t, x=col, y="conversion", text_auto=".1%",
                         title=C.LABELS.get(col, col), hover_data={"contacts": ":,"},
                         labels={col: "", "conversion": "อัตราตอบรับ", "contacts": "จำนวนคน"})
            fig.add_hline(y=OVERALL, line_dash="dot", line_color=ui.SLATE)
            colors = [ui.TEAL if v >= OVERALL else ui.PRIMARY for v in t["conversion"]]
            fig.update_traces(marker_color=colors)
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(height=340)
            grid[i % 2].plotly_chart(fig, width="stretch")
        st.caption("แท่งสีเขียว = สูงกว่าค่าเฉลี่ย · แท่งสีน้ำเงิน = ต่ำกว่าค่าเฉลี่ย · "
                   "วางเมาส์บนแท่งเพื่อดูจำนวนคน")

# ============================================================
# แท็บ 3: สถิติเชิงพรรณนา + Chi-square
# ============================================================
with tab_stat:
    num_cols = ["age", "campaign", "previous"] + C.MACRO_COLUMNS
    left, right = st.columns(2)
    with left:
        st.markdown("##### สถิติเชิงพรรณนา")
        st.dataframe(describe_numeric(df, num_cols), width="stretch")
    with right:
        st.markdown("##### ค่าเฉลี่ย: ตอบรับ vs ไม่ตอบรับ")
        st.dataframe(compare_groups(df, num_cols), width="stretch")

    st.markdown("##### Chi-square test of independence")
    st.markdown('<p class="muted">ทดสอบว่าตัวแปรแต่ละตัวเกี่ยวข้องกับผลการโทรอย่างมีนัยสำคัญหรือไม่ '
                "(H₀: ไม่เกี่ยวข้องกัน · ปฏิเสธ H₀ เมื่อ p-value &lt; 0.05)</p>",
                unsafe_allow_html=True)
    summary = chi_square_summary(df, CATEGORICAL)
    st.dataframe(summary, hide_index=True, width="stretch",
                 column_config={"p-value": st.column_config.NumberColumn(format="%.2e")})

    pick = st.selectbox("ดูตารางไขว้ของตัวแปร", CATEGORICAL,
                        format_func=lambda c: C.LABELS.get(c, c))
    r = chi_square(df, pick)
    table = r["table"].rename(columns=C.STATUS_LABELS)
    table["อัตราตอบรับ"] = (table.get("ตอบรับ", 0) / table.sum(axis=1)).map(ui.fmt_pct)
    st.dataframe(table, width="stretch")
    if r["chi2"] is not None:
        verdict = "เกี่ยวข้องอย่างมีนัยสำคัญ" if r["significant"] else "ไม่พบความเกี่ยวข้องอย่างมีนัยสำคัญ"
        st.markdown(f"χ² = {r['chi2']:.2f}, df = {r['dof']}, p-value = {r['p']:.2e} → **{verdict}**")

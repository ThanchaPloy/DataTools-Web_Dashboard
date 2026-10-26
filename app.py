"""
จุดเริ่มต้นของเว็บ: กำหนดเมนู + หน้าแรก (ภาพรวม)
รันด้วยคำสั่ง:  streamlit run app.py
"""
import plotly.express as px
import streamlit as st

from core import config as C
from core import ui
from core.analytics import conversion_by, kpis
from core.data_io import (StorageError, add_derived, build_from_csv, export_excel_bytes,
                          is_initialized, load_data, now_str, refresh, storage_label)

st.set_page_config(page_title="Bank Call Tracker", page_icon=":material/call:", layout="wide")
ui.apply_theme()


# ============================================================
# หน้าแรก: ภาพรวม
# ============================================================
def home():
    ui.page_header("ภาพรวมแคมเปญเสนอขายเงินฝากประจำ",
                   "ติดตามรายชื่อลูกค้า ผลการโทร และอัตราตอบรับในที่เดียว",
                   eyebrow="Bank Call Tracker")

    # เชื่อมต่อแหล่งข้อมูล ถ้าไม่สำเร็จแสดงวิธีแก้
    try:
        ready = is_initialized()
    except StorageError as e:
        st.error(str(e))
        st.caption("ดูวิธีตั้งค่าใน README.md หัวข้อ 'ตั้งค่า Google Sheet'")
        return

    # ยังไม่มีข้อมูล: นำเข้าจาก CSV ต้นฉบับ
    if not ready:
        st.info(f"เชื่อมต่อ {storage_label()} สำเร็จ แต่ยังไม่มีข้อมูลลูกค้า")
        if C.RAW_CSV.exists():
            if st.button("นำเข้าข้อมูลจาก bank-additional.csv", type="primary"):
                with st.spinner("กำลังนำเข้าข้อมูล..."):
                    n = build_from_csv()
                st.success(f"นำเข้าเรียบร้อย {n:,} แถว")
                st.rerun()
        else:
            st.warning(f"วางไฟล์ bank-additional.csv ไว้ที่ {C.RAW_CSV} ก่อน แล้วรีเฟรชหน้านี้")
        return

    customers, log = load_data()
    df = add_derived(customers)
    k = kpis(df)

    # --- การ์ดตัวเลข ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.kpi("ลูกค้าทั้งหมด", ui.fmt_int(k["total"]), "รายชื่อในระบบ", "accent")
    with c2:
        ui.kpi("โทรแล้ว", ui.fmt_int(k["called"]),
               f"{ui.fmt_pct(k['called'] / max(k['total'], 1))} ของรายชื่อ", "accent")
    with c3:
        ui.kpi("อัตราตอบรับ", ui.fmt_pct(k["conversion"]),
               f"ตอบรับ {ui.fmt_int(k['yes'])} คน", "teal")
    with c4:
        ui.kpi("รอโทร", ui.fmt_int(k["pending"]), "ลูกค้าใหม่ที่ยังไม่ได้ติดต่อ", "amber")

    st.write("")

    # --- กราฟ ---
    left, right = st.columns([3, 2])
    with left:
        by_month = conversion_by(df, "month")
        fig = px.bar(by_month, x="month", y="conversion", text_auto=".1%",
                     title="อัตราตอบรับรายเดือน",
                     labels={"month": "เดือน", "conversion": "อัตราตอบรับ"})
        fig.add_hline(y=k["conversion"], line_dash="dot", line_color=ui.SLATE)
        fig.update_yaxes(tickformat=".0%")
        fig.update_traces(marker_color=ui.PRIMARY)
        st.plotly_chart(fig, width="stretch")
        st.caption("เส้นประ = อัตราตอบรับเฉลี่ยทั้งหมด")
    with right:
        status = df["status"].value_counts().reset_index()
        status.columns = ["สถานะ", "จำนวน"]
        fig = px.pie(status, names="สถานะ", values="จำนวน", hole=0.6,
                     title="สถานะลูกค้า", color="สถานะ",
                     color_discrete_map=ui.STATUS_COLORS)
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")

    # --- ทางลัด + การแก้ไขล่าสุด ---
    left, right = st.columns([2, 3])
    with left:
        st.markdown("#### เริ่มงาน")
        st.page_link("views/2_Add_Customer.py", label="เพิ่มลูกค้าใหม่", icon=":material/person_add:")
        st.page_link("views/1_Customer_Records.py", label="บันทึก / แก้ไขผลการโทร", icon=":material/table_edit:")
        st.page_link("views/3_Analytics.py", label="ดูบทวิเคราะห์ 5 มิติ", icon=":material/insights:")
        st.page_link("views/5_Lead_Scoring.py", label="จัดอันดับว่าควรโทรหาใครก่อน", icon=":material/target:")
    with right:
        st.markdown("#### การแก้ไขล่าสุด")
        recent = log.sort_values("timestamp", ascending=False).head(6)
        recent = recent.rename(columns={"timestamp": "เวลา", "action": "การกระทำ",
                                        "customer_id": "รหัสลูกค้า", "details": "รายละเอียด"})
        st.dataframe(recent, hide_index=True, width="stretch")


# ============================================================
# เมนู (ชื่อหน้าและไอคอนภาษาไทย)
# ============================================================
nav = st.navigation({
    "": [st.Page(home, title="ภาพรวม", icon=":material/space_dashboard:", default=True)],
    "จัดการข้อมูล": [
        st.Page("views/1_Customer_Records.py", title="รายชื่อลูกค้า", icon=":material/table_edit:"),
        st.Page("views/2_Add_Customer.py", title="เพิ่มลูกค้าใหม่", icon=":material/person_add:"),
    ],
    "วิเคราะห์": [
        st.Page("views/3_Analytics.py", title="บทวิเคราะห์", icon=":material/insights:"),
        st.Page("views/6_Inferential_Stats.py", title="สถิติเชิงอนุมาน", icon=":material/functions:"),
        st.Page("views/4_Tableau_Dashboard.py", title="Tableau Dashboard", icon=":material/bar_chart:"),
        st.Page("views/5_Lead_Scoring.py", title="จัดอันดับลูกค้า (ML)", icon=":material/target:"),
    ],
    "เกี่ยวกับ": [
        st.Page("views/7_About.py", title="เกี่ยวกับโปรเจค", icon=":material/info:"),
    ],
})

with st.sidebar:
    st.caption(f"แหล่งข้อมูล: {storage_label()}")
    if st.button("โหลดข้อมูลล่าสุด", icon=":material/refresh:", width="stretch",
                 help="ดึงข้อมูลใหม่จากแหล่งข้อมูล เช่น หลังรัน Colab ให้คะแนนลูกค้า"):
        refresh()
        st.rerun()

    try:
        _xlsx = export_excel_bytes()
    except StorageError:
        _xlsx = None
    st.download_button(
        "ดาวน์โหลด bank_data.xlsx", data=_xlsx or b"", disabled=_xlsx is None,
        file_name=f"{C.GROUP_NAME}_bank_data_{now_str().replace(':', '').replace(' ', '_').replace('-', '')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:", width="stretch",
        help="สำรองข้อมูลทั้งหมด (customers, change_log, model_info) เป็นไฟล์เดียว "
             "เปิดดูเอง หรือใช้เป็นแหล่งข้อมูลให้ Tableau บนเครื่องอื่นได้")
    st.caption("ข้อมูล: UCI Bank Marketing")

nav.run()

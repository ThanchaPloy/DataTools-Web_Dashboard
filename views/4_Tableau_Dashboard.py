"""
หน้า 4: ฝัง dashboard จาก Tableau Public
ตั้ง URL ได้ที่ core/config.py (TABLEAU_URL) หรือวางลิงก์ชั่วคราวในหน้านี้
"""
import re

import streamlit as st
import streamlit.components.v1 as components

from core import config as C
from core import ui

ui.page_header("Tableau Dashboard",
               "Dashboard ที่สร้างจากข้อมูลชุดเดียวกับเว็บนี้ (bank_data.xlsx)",
               eyebrow="วิเคราะห์")

url = C.TABLEAU_URL
with st.expander("ตั้งค่าลิงก์ Dashboard", expanded=not url):
    temp = st.text_input("วางลิงก์ Tableau Public (ใช้ชั่วคราวในรอบนี้)", value=url,
                         placeholder="https://public.tableau.com/views/ชื่อWorkbook/ชื่อDashboard")
    st.caption("ใช้ถาวร: แก้ค่า TABLEAU_URL ในไฟล์ core/config.py")
    url = temp.strip()

if not url:
    ui.card("ยังไม่ได้ตั้งค่า Dashboard",
            "1) ต่อ Tableau กับ Google Sheet ชีต customers (Connect → Google Sheets) · "
            "2) สร้าง dashboard แล้ว Save to Tableau Public · "
            "3) คัดลอกลิงก์ของ dashboard มาวางในช่องด้านบน หรือใน core/config.py")
    st.stop()

# Tableau Public ไม่อัปเดตตาม Excel อัตโนมัติ ต้อง publish ใหม่หลังแก้ข้อมูล
st.info("Dashboard แสดงข้อมูล ณ รอบที่ Tableau Public ดึงข้อมูลล่าสุด ถ้าต้องการข้อมูลใหม่ทันที "
        "ให้เปิด Tableau แล้ว Refresh และ Save to Tableau Public ใหม่")

def to_views_url(link: str) -> str:
    # รองรับลิงก์ทุกแบบจาก Tableau Public แล้วแปลงเป็นรูปแบบที่ฝังได้
    # - .../app/profile/<ชื่อผู้ใช้>/viz/<Workbook>/<Dashboard>  (ลิงก์จากแถบที่อยู่)
    # - .../views/<Workbook>/<Dashboard>?:language=...            (ลิงก์จากปุ่ม Share)
    link = link.split("?")[0].split("#")[0].rstrip("/")
    m = re.search(r"/viz/([^/]+)/([^/]+)$", link)
    if m:
        return f"https://public.tableau.com/views/{m.group(1)}/{m.group(2)}"
    return link


base = to_views_url(url)
if "/views/" not in base:
    st.error("ลิงก์ไม่ถูกต้อง ต้องเป็นลิงก์ของ dashboard บน public.tableau.com "
             "เช่น https://public.tableau.com/views/ชื่อWorkbook/ชื่อDashboard")
    st.stop()
embed_url = f"{base}?:embed=y&:showVizHome=no&:toolbar=yes&:display_count=no"
components.iframe(embed_url, height=860, scrolling=True)
st.link_button("เปิดใน Tableau Public", base, icon=":material/open_in_new:")

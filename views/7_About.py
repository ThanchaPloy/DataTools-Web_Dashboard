"""
หน้า 7: เกี่ยวกับโปรเจค
สรุปปัญหา แหล่งข้อมูล และภาพรวมการทำงานของระบบ สั้น ๆ ไว้เปิดตอนเริ่มเดโม
"""
import streamlit as st

from core import config as C
from core import ui

ui.page_header(f"Bank Call Tracker ({C.GROUP_NAME})",
               "ใครควรโทรหาก่อน: ระบบช่วยทีมขายธนาคารจัดลำดับลูกค้าที่น่าจะเปิดบัญชีเงินฝากประจำ",
               eyebrow="เกี่ยวกับโปรเจค")

c1, c2 = st.columns(2)
with c1:
    ui.card("โจทย์ (Problem)",
            "ทีมขายโทรชวนลูกค้าเปิดบัญชีเงินฝากประจำ แต่จำนวนสายที่โทรได้ในแต่ละแคมเปญมีจำกัด "
            "และอัตราตอบรับโดยรวมต่ำ (ราว 11–15%) ถ้าโทรสุ่มทุกคนจะเสียเวลาและต้นทุนไปกับคนที่ "
            "ไม่น่าสนใจข้อเสนอ ระบบนี้จึงต้องตอบ 2 คำถาม: "
            "<b>ควรโทรหาใครก่อน</b> (วิชา ML) และ <b>ลูกค้าแบบไหนตอบรับมากที่สุด</b> (วิชา Data Tool)")
with c2:
    ui.card("แหล่งข้อมูล (Data)",
            "<b>UCI Bank Marketing Dataset</b> ข้อมูลผลการโทรเชิญชวนจริงของธนาคารในโปรตุเกส "
            "ใช้ bank-additional-full.csv (41,188 แถว) เทรนโมเดลใน Colab และ bank-additional.csv "
            "(ราว 4,119 แถว) เป็นข้อมูลลูกค้าในเว็บนี้ แต่ละแถวคือลูกค้า 1 คน มี 20 ตัวแปร "
            "ครอบคลุมข้อมูลประชากร สถานะการเงิน ประวัติการติดต่อ และภาวะเศรษฐกิจ")

st.write("")
st.markdown("#### ระบบทำงานอย่างไร")
st.code(
    "เว็บ Streamlit ──อ่าน/เขียน──► bank_data.xlsx ──อัปโหลด──► Google Colab (เทรนโมเดล ML)\n"
    "     ▲                              │                                 │\n"
    "     └──── นำเข้าคะแนนกลับ (scores_from_colab.xlsx) ◄────────────────┘\n"
    "                                    └──► Tableau Public (dashboard)\n"
    "                                    └──► ไฟล์ Excel วิเคราะห์สถิติ (สูตรจริงทุกค่า)",
    language=None)

c1, c2, c3 = st.columns(3)
with c1:
    ui.card("1. บันทึกข้อมูล (Data Tool)",
            "เว็บนี้เป็นหน้าบ้านให้ทีมขายเพิ่มลูกค้าใหม่ และบันทึกผลการโทร (ตอบรับ/ไม่ตอบรับ) "
            "ข้อมูลทั้งหมดเก็บในไฟล์ Excel ไฟล์เดียว ใช้ร่วมกันทั้งเว็บ, Tableau และโมเดล ML")
with c2:
    ui.card("2. วิเคราะห์สถิติ (Data Tool)",
            "หน้าบทวิเคราะห์และสถิติเชิงอนุมาน คำนวณอัตราตอบรับ 5 มิติ ทดสอบสมมติฐานด้วย T-Test, "
            "ANOVA, Z-Test และหาจำนวนสายที่ควรโทรต่อกลุ่มด้วย Linear Programming (Solver) "
            "ผลตรงกับไฟล์ Excel และ Tableau dashboard ที่ต่อข้อมูลชุดเดียวกัน")
with c3:
    ui.card("3. จัดอันดับด้วย ML (วิชา ML)",
            "ในวิชา ML ใช้ Stacking (Logistic Regression + Random Forest + XGBoost) ทำนายโอกาส "
            "ตอบรับของลูกค้าแต่ละคน ปรับเกณฑ์ตัดสินใจ (threshold) ให้เหมาะกับต้นทุน/กำไรจริง "
            "แล้วส่งคะแนนกลับมาให้เว็บจัดอันดับว่าควรโทรหาใครก่อน")

st.write("")
ui.card("เทคนิคที่ใช้ (สรุปสั้น)",
        "<b>ML:</b> Binary classification, 12 โมเดลเปรียบเทียบกัน, Stacking ensemble, "
        "Platt calibration, threshold tuning ตามกำไร/ต้นทุน, SHAP อธิบายโมเดล, "
        "K-Means แบ่งกลุ่มลูกค้า (persona)<br>"
        "<b>Data Tool:</b> Descriptive statistics, T-Test / ANOVA / Z-Test, Chi-square, "
        "Correlation, Linear Programming (Solver), Tableau dashboard")

st.caption("ข้อมูล UCI Machine Learning Repository: Bank Marketing Data Set "
          "(Moro, Cortez & Rita, 2014) ใช้เพื่อการศึกษาเท่านั้น")

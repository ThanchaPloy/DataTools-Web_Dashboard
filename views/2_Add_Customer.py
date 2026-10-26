"""
หน้า 2: เพิ่มลูกค้าใหม่ผ่านฟอร์ม
ทุกช่องเป็น dropdown หรือช่องตัวเลขที่จำกัดช่วง ข้อมูลจึงสะกดตรงกับที่โมเดลและ Tableau ใช้เสมอ
คะแนนโอกาสตอบรับจะมาหลังรัน Step 19 ใน Colab
"""
from datetime import date

import streamlit as st

from core import config as C
from core import ui
from core.data_io import StorageError, append_customer, require_data, storage_label
from core.validation import validate_record

ui.page_header("เพิ่มลูกค้าใหม่",
               f"กรอกข้อมูลรายชื่อที่จะติดต่อ ระบบจะสร้างรหัสลูกค้าและบันทึกลง {storage_label()} ให้อัตโนมัติ",
               eyebrow="จัดการข้อมูล")

customers, _ = require_data()

# ผลการบันทึกครั้งก่อน
if saved := st.session_state.pop("added_customer", None):
    st.success(f"บันทึกลูกค้า {saved} เรียบร้อยแล้ว")
    st.info("ลูกค้าคนนี้ยังไม่มีคะแนนโอกาสตอบรับ ให้รัน Step 19 ใน Colab "
            "แล้วกด 'โหลดข้อมูลล่าสุด' ที่เมนูด้านซ้าย จะเห็นอันดับในหน้า 'จัดอันดับลูกค้า (ML)'")

# ค่าเริ่มต้นของข้อมูลเศรษฐกิจ = ค่าล่าสุดในไฟล์
latest = customers.iloc[-1]
today = date.today()
default_month = C.ALLOWED["month"][today.month - 1]
default_day = C.ALLOWED["day_of_week"][min(today.weekday(), 4)]


def opt(col):
    return C.ALLOWED[col]


def label(col):
    return C.LABELS[col]


with st.form("add_customer", clear_on_submit=False, border=True):
    st.markdown("#### ข้อมูลส่วนตัว")
    a1, a2, a3, a4 = st.columns(4)
    age = a1.number_input(label("age"), *C.NUMERIC_RANGES["age"], value=35, step=1)
    job = a2.selectbox(label("job"), opt("job"))
    marital = a3.selectbox(label("marital"), opt("marital"))
    education = a4.selectbox(label("education"), opt("education"),
                             index=opt("education").index("university.degree"))

    st.markdown("#### สถานะการเงิน")
    b1, b2, b3 = st.columns(3)
    default = b1.selectbox(label("default"), opt("default"))
    housing = b2.selectbox(label("housing"), opt("housing"))
    loan = b3.selectbox(label("loan"), opt("loan"))

    st.markdown("#### การติดต่อ")
    c1, c2, c3, c4 = st.columns(4)
    contact = c1.selectbox(label("contact"), opt("contact"),
                           help="cellular = มือถือ, telephone = โทรศัพท์บ้าน")
    month = c2.selectbox(label("month"), opt("month"), index=opt("month").index(default_month))
    day = c3.selectbox(label("day_of_week"), opt("day_of_week"),
                       index=opt("day_of_week").index(default_day))
    y = c4.selectbox(label("y"), opt("y"), format_func=lambda v: C.STATUS_LABELS[v],
                     help="ลูกค้าใหม่ที่ยังไม่ได้โทร ให้เลือก 'รอโทร'")

    d1, d2, d3, d4 = st.columns(4)
    campaign = d1.number_input(label("campaign"), *C.NUMERIC_RANGES["campaign"], value=0, step=1,
                               help="จำนวนครั้งที่โทรในแคมเปญนี้ (ยังไม่โทร = 0)")
    duration = d2.number_input(label("duration"), *C.NUMERIC_RANGES["duration"], value=0, step=1,
                               help="ยังไม่โทร = 0")

    st.markdown("#### ประวัติแคมเปญก่อน")
    e1, e2, e3, e4 = st.columns(4)
    contacted = e1.radio("เคยติดต่อในแคมเปญก่อน", ["ไม่เคย", "เคย"], horizontal=True)
    pdays = e2.number_input("ติดต่อครั้งล่าสุดกี่วันก่อน", 0, 998, value=10, step=1,
                            help="ใช้เฉพาะเมื่อเลือก 'เคย'")
    previous = e3.number_input(label("previous"), *C.NUMERIC_RANGES["previous"], value=0, step=1)
    poutcome = e4.selectbox(label("poutcome"), opt("poutcome"))

    with st.expander("ข้อมูลเศรษฐกิจ ณ วันที่ติดต่อ (ค่าเริ่มต้น = ค่าล่าสุดในระบบ)"):
        m = st.columns(5)
        macro = {col: m[i].number_input(label(col), *C.NUMERIC_RANGES[col],
                                         value=float(latest[col]), format="%.3f")
                 for i, col in enumerate(C.MACRO_COLUMNS)}

    submitted = st.form_submit_button("บันทึกลูกค้าใหม่", type="primary", icon=":material/person_add:")

if submitted:
    record = {
        "age": int(age), "job": job, "marital": marital, "education": education,
        "default": default, "housing": housing, "loan": loan,
        "contact": contact, "month": month, "day_of_week": day,
        "duration": int(duration), "campaign": int(campaign),
        "pdays": 999 if contacted == "ไม่เคย" else int(pdays),
        "previous": 0 if contacted == "ไม่เคย" else int(previous),
        "poutcome": "nonexistent" if contacted == "ไม่เคย" else poutcome,
        **macro, "y": y,
    }
    errors = validate_record(record)
    if contacted == "เคย" and record["poutcome"] == "nonexistent":
        errors.append("เลือก 'เคย' ติดต่อ แต่ผลแคมเปญก่อนเป็น nonexistent")
    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    try:
        with st.spinner("กำลังบันทึก..."):
            new_id = append_customer(record)
    except StorageError as e:
        st.error(str(e))
        st.stop()

    st.session_state.added_customer = new_id
    st.rerun()

st.caption("ช่องที่เป็นตัวเลือกใช้ค่าตามชุดข้อมูลต้นฉบับ (ภาษาอังกฤษ) เพื่อให้ตรงกับโมเดลและ Tableau")

"""
หน้า 1: รายชื่อลูกค้า
ค้นหา / กรอง -> แก้ไข เพิ่ม ลบแถวในตาราง -> ตรวจข้อมูล -> บันทึกลงแหล่งข้อมูล + บันทึก log
แถวที่แก้ข้อมูลจะถูกล้างคะแนน เพราะคะแนนเดิมคำนวณจากข้อมูลเก่า (Colab จะให้คะแนนใหม่)
"""
import io

import numpy as np
import pandas as pd
import streamlit as st

from core import config as C
from core import ui
from core.data_io import (StorageError, append_log, next_ids, now_str, require_data,
                          save_customers, storage_label)
from core.validation import coerce_types, validate_frame

ui.page_header("รายชื่อลูกค้า",
               f"ค้นหา แก้ไขผลการโทร เพิ่มหรือลบรายชื่อ แล้วกดบันทึกเพื่อเขียนลง {storage_label()}",
               eyebrow="จัดการข้อมูล")

customers, log = require_data()

# ข้อความผลการบันทึกครั้งก่อน (แสดงหลังหน้ารีเฟรช)
if msg := st.session_state.pop("records_msg", None):
    st.success(msg)
st.session_state.setdefault("editor_version", 0)

# ------------------------------------------------------------
# ตัวกรอง
# ------------------------------------------------------------
with st.container(border=True):
    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.6, 1.6])
    search = f1.text_input("ค้นหารหัสลูกค้า", placeholder="เช่น C0012")
    status = f2.multiselect("ผลการโทร", C.ALLOWED["y"], placeholder="ทั้งหมด",
                            format_func=lambda v: C.STATUS_LABELS[v])
    jobs = f3.multiselect("อาชีพ", C.ALLOWED["job"], placeholder="ทั้งหมด")
    age_min, age_max = int(customers["age"].min()), int(customers["age"].max())
    ages = f4.slider("ช่วงอายุ", age_min, age_max, (age_min, age_max))

mask = customers["age"].between(*ages)
if search:
    mask &= customers[C.ID_COL].str.contains(search.strip(), case=False, na=False)
if status:
    mask &= customers[C.TARGET_COL].isin(status)
if jobs:
    mask &= customers["job"].isin(jobs)
view = customers[mask].reset_index(drop=True)

st.caption(f"แสดง {len(view):,} จาก {len(customers):,} รายชื่อ · แก้ไขในตารางได้โดยตรง · "
           "เพิ่มแถวที่ด้านล่างของตาราง · ลบแถวโดยเลือกแถวแล้วกดไอคอนถังขยะ")

# ------------------------------------------------------------
# ตารางแก้ไขได้
# ------------------------------------------------------------
column_config = {
    C.ID_COL: st.column_config.TextColumn(C.LABELS[C.ID_COL], disabled=True,
                                          help="สร้างอัตโนมัติเมื่อบันทึก"),
    C.UPDATED_COL: st.column_config.TextColumn(C.LABELS[C.UPDATED_COL], disabled=True),
    C.TARGET_COL: st.column_config.SelectboxColumn(
        C.LABELS[C.TARGET_COL], options=C.ALLOWED["y"], required=True,
        help="pending = รอโทร, yes = ตอบรับ, no = ไม่ตอบรับ"),
}
for col in C.ALLOWED:
    if col != C.TARGET_COL:
        column_config[col] = st.column_config.SelectboxColumn(
            C.LABELS[col], options=C.ALLOWED[col], required=True)
for col, (lo, hi) in C.NUMERIC_RANGES.items():
    step = 1 if col in C.INT_COLUMNS else 0.001
    column_config[col] = st.column_config.NumberColumn(
        C.LABELS[col], min_value=lo, max_value=hi, step=step, required=True)

# ไม่แสดงคอลัมน์คะแนนในตารางนี้ (มาจาก Colab แก้ในเว็บไม่ได้ ดูได้ที่หน้า 'จัดอันดับลูกค้า (ML)')
EDIT_COLUMNS = [c for c in C.ALL_COLUMNS if c not in C.SCORE_COLUMNS]

edited = st.data_editor(
    view[EDIT_COLUMNS],
    key=f"editor_{st.session_state.editor_version}_{search}_{status}_{jobs}_{ages}",
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    height=480,
    column_config=column_config,
)


# ------------------------------------------------------------
# หาความเปลี่ยนแปลง: แก้ไข / เพิ่ม / ลบ
# ------------------------------------------------------------
def _same(a: pd.Series, b: pd.Series) -> pd.Series:
    """เปรียบเทียบค่าทีละช่อง ตัวเลขเทียบแบบมีค่าคลาดเคลื่อนเล็กน้อย"""
    na, nb = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
    result = a.astype(str).str.strip() == b.astype(str).str.strip()
    both_num = na.notna() & nb.notna()
    result[both_num] = np.isclose(na[both_num].astype(float), nb[both_num].astype(float))
    result[a.isna() & b.isna()] = True
    return result


def find_changes(original: pd.DataFrame, edited: pd.DataFrame):
    orig_ids = set(original[C.ID_COL])
    has_id = edited[C.ID_COL].notna() & (edited[C.ID_COL].astype(str).str.strip() != "")
    added = edited[~has_id].copy()
    kept = edited[has_id].set_index(C.ID_COL)
    deleted = sorted(orig_ids - set(kept.index))

    o = original.set_index(C.ID_COL).loc[kept.index, C.DATA_COLUMNS]
    e = kept[C.DATA_COLUMNS]
    changed = {}
    for col in C.DATA_COLUMNS:
        diff = ~_same(o[col], e[col])
        for cid in diff[diff].index:
            changed.setdefault(cid, []).append(col)
    return changed, added, deleted, kept


changed, added, deleted, kept = find_changes(view, edited)
n_changes = len(changed) + len(added) + len(deleted)

# ------------------------------------------------------------
# สรุปและบันทึก
# ------------------------------------------------------------
left, c4 = st.columns([3, 1.2])
left.markdown(f'<div class="change-bar">การเปลี่ยนแปลงที่ยังไม่บันทึก: แก้ไข <b>{len(changed)}</b> · '
              f'เพิ่ม <b>{len(added)}</b> · ลบ <b>{len(deleted)}</b> แถว</div>', unsafe_allow_html=True)

with c4:
    save_clicked = st.button("บันทึก", type="primary", disabled=n_changes == 0,
                             icon=":material/save:", width="stretch")
    if n_changes and st.button("ยกเลิกการแก้ไข", icon=":material/undo:", width="stretch"):
        st.session_state.editor_version += 1
        st.rerun()

if deleted:
    st.warning(f"จะลบ {len(deleted)} รายชื่อ: {', '.join(deleted[:10])}"
               f"{' ...' if len(deleted) > 10 else ''}")

if save_clicked:
    to_check = pd.concat([kept.loc[list(changed)].reset_index(), added], ignore_index=True)
    to_check = coerce_types(to_check) if len(to_check) else to_check
    errors = validate_frame(to_check) if len(to_check) else []
    if errors:
        st.error(f"พบข้อมูลไม่ถูกต้อง {len(errors)} จุด กรุณาแก้ก่อนบันทึก")
        st.dataframe(pd.DataFrame({"ข้อผิดพลาด": errors[:50]}), hide_index=True, width="stretch")
        st.stop()

    full = customers.set_index(C.ID_COL)
    stamp = now_str()
    log_rows = []

    # ลบ
    full = full.drop(index=deleted)
    log_rows += [("ลบ", cid, "ลบจากหน้ารายชื่อลูกค้า") for cid in deleted]

    # แก้ไข
    if changed:
        fixed = coerce_types(kept.loc[list(changed)].reset_index()).set_index(C.ID_COL)
        for cid, cols in changed.items():
            full.loc[cid, C.DATA_COLUMNS] = fixed.loc[cid, C.DATA_COLUMNS].values
            full.loc[cid, C.UPDATED_COL] = stamp
            if any(c != C.TARGET_COL for c in cols):     # ข้อมูลลูกค้าเปลี่ยน -> คะแนนเดิมใช้ไม่ได้
                full.loc[cid, C.SCORE_COLUMNS] = pd.NA
            detail = ", ".join(f"{C.LABELS.get(c, c)}: {view.set_index(C.ID_COL).loc[cid, c]} → "
                               f"{fixed.loc[cid, c]}" for c in cols)
            log_rows.append(("แก้ไข", cid, detail))

    # เพิ่ม
    if len(added):
        new = coerce_types(added)
        new[C.ID_COL] = next_ids(customers, len(new))
        new[C.UPDATED_COL] = stamp
        for col in C.SCORE_COLUMNS:
            new[col] = pd.NA
        full = pd.concat([full, new.set_index(C.ID_COL)[full.columns]])
        log_rows += [("เพิ่ม", cid, "เพิ่มจากหน้ารายชื่อลูกค้า") for cid in new[C.ID_COL]]

    try:
        with st.spinner("กำลังบันทึก..."):
            save_customers(full.reset_index())
            append_log(log_rows)
    except StorageError as e:
        st.error(str(e))
        st.stop()

    st.session_state.editor_version += 1
    st.session_state.records_msg = (f"บันทึกเรียบร้อย: แก้ไข {len(changed)} · เพิ่ม {len(added)} · "
                                    f"ลบ {len(deleted)} แถว")
    st.rerun()

# ------------------------------------------------------------
# ดาวน์โหลดข้อมูลตามตัวกรอง
# ------------------------------------------------------------
with st.expander("ดาวน์โหลดข้อมูลที่กรองไว้"):
    buf = io.BytesIO()
    view.to_excel(buf, index=False)
    d1, d2 = st.columns(2)
    d1.download_button("ดาวน์โหลด Excel", buf.getvalue(), "customers_filtered.xlsx",
                       icon=":material/download:", width="stretch")
    d2.download_button("ดาวน์โหลด CSV", view.to_csv(index=False).encode("utf-8-sig"),
                       "customers_filtered.csv", icon=":material/download:", width="stretch")

with st.expander("ประวัติการแก้ไข (change_log)"):
    st.dataframe(log.sort_values("timestamp", ascending=False)
                    .rename(columns={"timestamp": "เวลา", "action": "การกระทำ",
                                     "customer_id": "รหัสลูกค้า", "details": "รายละเอียด"}),
                 hide_index=True, width="stretch", height=300)

"""
สร้างไฟล์ Excel วิเคราะห์เชิงสถิติจากข้อมูลปัจจุบันของเว็บ (ทำแบบเดียวกับปุ่มในหน้าบทวิเคราะห์)

วิธีใช้ (รันจากโฟลเดอร์หลักของโปรเจค):
    python scripts/build_analysis_excel.py
ได้ไฟล์ outputs/<ชื่อกลุ่ม>_statistical_analysis.xlsx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # ให้ import core ได้

import logging                         # noqa: E402
import streamlit                       # noqa: E402,F401
for _name in ("streamlit", "streamlit.runtime.caching.cache_data_api",
              "streamlit.runtime.caching.cache_resource_api",
              "streamlit.runtime.scriptrunner_utils.script_run_context"):   # ซ่อนคำเตือนเมื่อรันนอกเว็บ
    logging.getLogger(_name).setLevel(logging.ERROR)

from core import config as C                                   # noqa: E402
from core.data_io import StorageError, load_data, now_str      # noqa: E402
from core.excel_report import build_analysis_workbook          # noqa: E402


def main():
    try:
        customers, _ = load_data()
    except StorageError as e:
        sys.exit(f"โหลดข้อมูลไม่สำเร็จ: {e}")
    if customers is None:
        sys.exit("ยังไม่มีข้อมูล ให้นำเข้าข้อมูลก่อน (python scripts/prepare_data.py)")
    data = build_analysis_workbook(customers, C.GROUP_NAME, now_str())
    C.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = C.OUTPUT_DIR / f"{C.GROUP_NAME}_statistical_analysis.xlsx"
    out.write_bytes(data)
    print(f"สร้างไฟล์เรียบร้อย: {out}")


if __name__ == "__main__":
    main()

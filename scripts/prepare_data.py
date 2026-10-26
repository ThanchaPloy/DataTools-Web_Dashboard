"""
นำเข้าข้อมูลครั้งแรก: อ่าน data/raw/bank-additional.csv แล้วเขียนลง Google Sheet (หรือ Excel ตาม config.STORAGE)
(ทำแบบเดียวกับปุ่ม "นำเข้าข้อมูล" ในหน้าภาพรวมของเว็บ)

วิธีใช้ (รันจากโฟลเดอร์หลักของโปรเจค):
    python scripts/prepare_data.py            # นำเข้า (ถ้ามีข้อมูลอยู่แล้วจะไม่ทับ)
    python scripts/prepare_data.py --reset    # ล้างแล้วนำเข้าใหม่จากต้นฉบับ (ย้อนได้จาก Version history ของ Google Sheet)
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

from core import config as C          # noqa: E402
from core.data_io import StorageError, build_from_csv   # noqa: E402


def main():
    overwrite = "--reset" in sys.argv
    try:
        n = build_from_csv(overwrite=overwrite)
    except FileExistsError:
        print("มีข้อมูลลูกค้าอยู่แล้ว ถ้าต้องการนำเข้าใหม่ให้ใช้ --reset")
        return
    except (FileNotFoundError, ValueError, StorageError) as e:
        print(f"สร้างไม่สำเร็จ: {e}")
        sys.exit(1)
    print(f"นำเข้าลง {C.STORAGE} เรียบร้อย จำนวน {n:,} แถว")


if __name__ == "__main__":
    main()

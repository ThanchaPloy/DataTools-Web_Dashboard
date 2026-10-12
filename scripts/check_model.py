"""
ตรวจไฟล์โมเดลนอกเว็บ เพื่อหาสาเหตุเมื่อหน้า ML โหลดโมเดลไม่ได้

วิธีใช้ (รันจากโฟลเดอร์หลักของโปรเจค):
    python scripts/check_model.py
"""
import hashlib
import platform
import sys
import traceback
from pathlib import Path

MODEL = Path(__file__).resolve().parent.parent / "models" / "model_bundle.joblib"
EXPECTED_SIZE = 20522561   # ขนาดของไฟล์ที่ทดสอบแล้วว่าโหลดได้
EXPECTED_SHA = "8bc51e9a1c6e3fa92d744bc80581e128110669ef387877626f500c1acb48afb0"

print("Python  :", sys.version.split()[0], platform.system(), platform.machine())
for name in ["numpy", "scipy", "sklearn", "xgboost", "joblib", "pandas"]:
    try:
        mod = __import__(name)
        print(f"{name:8s}:", mod.__version__)
    except Exception as e:
        print(f"{name:8s}: import ไม่ได้ ({e})")

if not MODEL.exists():
    sys.exit(f"\nไม่พบไฟล์ {MODEL}")

data = MODEL.read_bytes()
sha = hashlib.sha256(data).hexdigest()
print("\nไฟล์    :", MODEL)
print("ขนาด    :", f"{len(data):,} ไบต์", "(ตรงกับไฟล์ทดสอบ)" if len(data) == EXPECTED_SIZE else "")
print("SHA-256 :", sha, "(ตรงกับไฟล์ทดสอบ)" if sha == EXPECTED_SHA else "")
print("ต้นไฟล์ :", data[:16])

print("\nกำลังโหลด...")
try:
    import joblib
    bundle = joblib.load(MODEL)
    print("โหลดสำเร็จ:", type(bundle["model"]).__name__, "| features:", bundle["features"])
except Exception:
    print("โหลดไม่สำเร็จ รายละเอียด:")
    traceback.print_exc()
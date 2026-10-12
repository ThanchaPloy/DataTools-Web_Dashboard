"""
ชั้นเก็บข้อมูล (Data Access) รองรับ 2 แบบ เลือกที่ config.STORAGE
- GoogleSheetStorage: อ่าน/เขียน Google Sheet ผ่าน service account (ใช้จริง)
- ExcelStorage: อ่าน/เขียนไฟล์ Excel ในเครื่อง (ทางสำรอง)

ทั้งสองแบบมีฟังก์ชันเหมือนกัน หน้าเว็บจึงไม่ต้องรู้ว่าข้อมูลอยู่ที่ไหน
- has_sheet(name)      มีชีตนี้และมีหัวตารางหรือยัง
- read(name)           คืน DataFrame (ค่าดิบ ยังไม่แปลงชนิดข้อมูล)
- write(name, df)      เขียนทับทั้งชีต
- append(name, df)     ต่อท้ายชีต
"""
import pandas as pd

from core import config as C


class StorageError(Exception):
    """อ่าน/เขียนข้อมูลไม่สำเร็จ (ข้อความเป็นภาษาไทยพร้อมแสดงผู้ใช้)"""


def _to_values(df: pd.DataFrame) -> list:
    """DataFrame -> list ของแถว (หัวตาราง + ข้อมูล) ค่าว่างเป็น "" ตัวเลขเป็นชนิดของ Python"""
    body = df.astype(object).where(df.notna(), "").values.tolist()
    return [list(df.columns)] + body


# ============================================================
# Google Sheet
# ============================================================
class GoogleSheetStorage:
    label = "Google Sheet"

    def __init__(self, client=None):
        if not C.SHEET_ID:
            raise StorageError("ยังไม่ได้ใส่ SHEET_ID ใน core/config.py")
        if client is None:
            if not C.CREDENTIALS_PATH.exists():
                raise StorageError(
                    f"ไม่พบไฟล์ key ของ service account ที่ {C.CREDENTIALS_PATH} "
                    "ให้วางไฟล์ .json ที่ดาวน์โหลดจาก Google Cloud แล้วเปลี่ยนชื่อเป็น service_account.json")
            import gspread
            client = gspread.service_account(filename=str(C.CREDENTIALS_PATH))
        try:
            self.sh = client.open_by_key(C.SHEET_ID)
        except Exception as e:
            raise StorageError(
                "เปิด Google Sheet ไม่ได้ ตรวจว่า SHEET_ID ถูกต้อง และแชร์ Sheet ให้อีเมลของ "
                f"service account เป็น Editor แล้ว ({type(e).__name__}: {e})") from e

    # --- ภายใน ---
    def _ws(self, name, create=False, rows=100, cols=30):
        import gspread
        try:
            return self.sh.worksheet(name)
        except gspread.WorksheetNotFound:
            if not create:
                return None
            sheets = self.sh.worksheets()
            # Sheet ใหม่จะมีแท็บว่าง 1 แท็บ (Sheet1 / แผ่น1) เปลี่ยนชื่อมาใช้แทนการสร้างใหม่
            if len(sheets) == 1 and sheets[0].title not in (C.SHEET_CUSTOMERS, C.SHEET_LOG,
                                                            C.SHEET_MODEL_INFO):
                if not self.sh.values_get(f"'{sheets[0].title}'").get("values"):
                    sheets[0].update_title(name)
                    return sheets[0]
            return self.sh.add_worksheet(title=name, rows=rows, cols=cols)

    def _call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"ติดต่อ Google Sheet ไม่สำเร็จ ลองใหม่อีกครั้ง ({type(e).__name__}: {e})") from e

    # --- ฟังก์ชันหลัก ---
    def has_sheet(self, name) -> bool:
        ws = self._call(self._ws, name)
        if ws is None:
            return False
        head = self._call(self.sh.values_get, f"'{name}'!1:1").get("values")
        return bool(head)

    def read(self, name) -> pd.DataFrame:
        if self._call(self._ws, name) is None:
            return pd.DataFrame()
        # UNFORMATTED_VALUE = ได้ตัวเลขเป็นตัวเลขจริง ไม่ติดรูปแบบการแสดงผลของ Sheet
        res = self._call(self.sh.values_get, f"'{name}'",
                         params={"valueRenderOption": "UNFORMATTED_VALUE"})
        rows = res.get("values", [])
        if not rows:
            return pd.DataFrame()
        header = [str(h) for h in rows[0]]
        body = [r + [""] * (len(header) - len(r)) for r in rows[1:]]   # แถวที่ช่องท้ายว่างจะสั้นกว่า
        return pd.DataFrame([r[:len(header)] for r in body], columns=header)

    def write(self, name, df: pd.DataFrame):
        values = _to_values(df)
        n_rows, n_cols = len(values), len(values[0])

        def _do():
            ws = self._ws(name, create=True, rows=n_rows + 10, cols=n_cols)
            if ws.row_count < n_rows or ws.col_count < n_cols:          # ขยายตารางให้พอ
                ws.resize(rows=max(ws.row_count, n_rows), cols=max(ws.col_count, n_cols))
            self.sh.values_update(f"'{name}'!A1", params={"valueInputOption": "RAW"},
                                  body={"values": values})
            if ws.row_count > n_rows:                                   # ล้างแถวเก่าที่เกิน (กรณีลบแถว)
                self.sh.values_clear(f"'{name}'!A{n_rows + 1}:ZZ{ws.row_count}")
        self._call(_do)

    def append(self, name, df: pd.DataFrame):
        if df.empty:
            return
        if not self.has_sheet(name):
            return self.write(name, df)
        rows = _to_values(df)[1:]
        self._call(lambda: self._ws(name).append_rows(rows, value_input_option="RAW"))


# ============================================================
# Excel (ทางสำรอง)
# ============================================================
class ExcelStorage:
    label = "Excel ในเครื่อง"

    def _sheets(self):
        if not C.EXCEL_PATH.exists():
            return {}
        return pd.read_excel(C.EXCEL_PATH, sheet_name=None, dtype=object)

    def has_sheet(self, name) -> bool:
        sheets = self._sheets()
        return name in sheets and len(sheets[name].columns) > 0

    def read(self, name) -> pd.DataFrame:
        return self._sheets().get(name, pd.DataFrame())

    def write(self, name, df: pd.DataFrame):
        sheets = self._sheets()
        sheets[name] = df
        C.EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with pd.ExcelWriter(C.EXCEL_PATH, engine="openpyxl") as writer:
                for sheet_name, data in sheets.items():
                    data.to_excel(writer, sheet_name=sheet_name, index=False)
        except PermissionError as e:
            raise StorageError("บันทึกไม่ได้ เพราะไฟล์ bank_data.xlsx ถูกเปิดอยู่ในโปรแกรม Excel "
                               "กรุณาปิดไฟล์แล้วลองอีกครั้ง") from e

    def append(self, name, df: pd.DataFrame):
        if df.empty:
            return
        old = self.read(name)
        self.write(name, pd.concat([old, df], ignore_index=True) if len(old) else df)


def make_storage():
    if C.STORAGE == "excel":
        return ExcelStorage()
    if C.STORAGE == "gsheet":
        return GoogleSheetStorage()
    raise StorageError(f"ค่า STORAGE ใน config ต้องเป็น 'gsheet' หรือ 'excel' (ตอนนี้คือ '{C.STORAGE}')")

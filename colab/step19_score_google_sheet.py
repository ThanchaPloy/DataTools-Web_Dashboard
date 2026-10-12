# ============================================================
# STEP 19: ให้คะแนนลูกค้าใน Google Sheet (เชื่อม notebook กับเว็บ)
# - วางบล็อกนี้ต่อท้าย notebook ML (หลัง Step 17)
# - รันหลังเทรนโมเดลเสร็จ และทุกครั้งที่มีลูกค้าใหม่หรือแก้ข้อมูลในเว็บ
# - ใช้ตัวแปรจาก notebook: best_model, calibrate, add_features, FEATURES, kmeans, seg_prep,
#   SEGMENT_NAMES, BEST_THRESHOLD, BEST_NAME, final, PROFIT_PER_YES, COST_PER_CALL
# ============================================================
SHEET_ID = 'วาง Sheet ID ตรงนี้'   # ส่วนของลิงก์ระหว่าง /d/ กับ /edit (ค่าเดียวกับใน core/config.py)

from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from gspread.utils import rowcol_to_a1

# ------------------------------------------------------------
# 19.1 ล็อกอินด้วยบัญชี Google ของคุณ (บัญชีที่เป็นเจ้าของ Sheet) ไม่ต้องใช้ service account
# ------------------------------------------------------------
try:
    from google.colab import auth
    import google.auth
    auth.authenticate_user()
    creds, _ = google.auth.default()
    gc = gspread.authorize(creds)
except ImportError:
    gc = GSPREAD_CLIENT            # ใช้ตอนทดสอบนอก Colab เท่านั้น
sh = gc.open_by_key(SHEET_ID)

# ------------------------------------------------------------
# 19.2 อ่านลูกค้าทั้งหมดจากชีต customers
# ------------------------------------------------------------
rows = sh.values_get("'customers'", params={'valueRenderOption': 'UNFORMATTED_VALUE'})['values']
header = [str(h) for h in rows[0]]
sheet_df = pd.DataFrame([r + [''] * (len(header) - len(r)) for r in rows[1:]], columns=header)
print('อ่านลูกค้า', len(sheet_df), 'คน')

# ------------------------------------------------------------
# 19.3 ให้คะแนนด้วยโมเดลที่เทรนไว้ (ขั้นตอนเดียวกับ Step 16)
# ------------------------------------------------------------
data = sheet_df.replace('', np.nan)
for col in ['age', 'pdays', 'previous', 'campaign']:
    data[col] = pd.to_numeric(data[col], errors='coerce')
feat = add_features(data)
ok = feat[FEATURES + ['pdays']].notna().all(axis=1)          # ให้คะแนนเฉพาะแถวที่ข้อมูลครบ

prob = pd.Series(np.nan, index=feat.index)
prob[ok] = calibrate(best_model.predict_proba(feat.loc[ok, FEATURES])[:, 1])
persona = pd.Series('', index=feat.index, dtype=object)
persona[ok] = [SEGMENT_NAMES.get(int(s), f'Segment {int(s)}')
               for s in kmeans.predict(seg_prep.transform(feat.loc[ok]))]
action = np.where(prob >= BEST_THRESHOLD, 'ควรโทรก่อน', 'ลำดับรอง')
now = datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')

# ------------------------------------------------------------
# 19.4 เขียนคะแนนกลับลง 4 คอลัมน์ท้ายของชีต customers
# ------------------------------------------------------------
SCORE_COLS = ['prob_yes', 'persona', 'action', 'scored_at']
missing = [c for c in SCORE_COLS if c not in header]
assert not missing, f'ชีตไม่มีคอลัมน์ {missing} ให้นำเข้าข้อมูลผ่านเว็บก่อน'
first_col = header.index('prob_yes') + 1
assert header[first_col - 1:first_col + 3] == SCORE_COLS, 'ลำดับคอลัมน์คะแนนในชีตไม่ถูกต้อง'

values = [[round(float(p), 4), str(pe), str(a), now] if pd.notna(p) else ['', '', '', '']
          for p, pe, a in zip(prob, persona, action)]
sh.values_update(f"'customers'!{rowcol_to_a1(2, first_col)}",
                 params={'valueInputOption': 'RAW'}, body={'values': values})

# ------------------------------------------------------------
# 19.5 บันทึกข้อมูลโมเดลลงชีต model_info (หน้า ML ของเว็บใช้แสดง)
# ------------------------------------------------------------
def _test_score(metric):
    try:
        return round(float(final.loc[f'{BEST_NAME} (test)', metric]), 4)
    except Exception:
        return ''

info = [['key', 'value'],
        ['model', BEST_NAME],
        ['threshold', float(BEST_THRESHOLD)],
        ['test_roc_auc', _test_score('ROC-AUC')],
        ['test_recall', _test_score('Recall')],
        ['test_f1', _test_score('F1')],
        ['features', ', '.join(FEATURES)],
        ['profit_per_yes', PROFIT_PER_YES],
        ['cost_per_call', COST_PER_CALL],
        ['n_scored', int(ok.sum())],
        ['scored_at', now]]
try:
    sh.worksheet('model_info')
except gspread.WorksheetNotFound:
    sh.add_worksheet(title='model_info', rows=30, cols=2)
sh.values_clear("'model_info'")
sh.values_update("'model_info'!A1", params={'valueInputOption': 'RAW'}, body={'values': info})

n_call_first = int((prob >= BEST_THRESHOLD).sum())
print(f'ให้คะแนนแล้ว {int(ok.sum())} คน (ข้อมูลไม่ครบ {int((~ok).sum())} คน) | '
      f'ควรโทรก่อน {n_call_first} คน | เวลา {now}')
print("กลับไปที่เว็บแล้วกด 'โหลดข้อมูลล่าสุด' ที่เมนูด้านซ้าย")

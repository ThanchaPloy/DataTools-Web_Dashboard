# ============================================================
# STEP 19 (โหมด Excel): ให้คะแนนลูกค้าจากไฟล์ bank_data.xlsx ของเว็บ
# - วางบล็อกนี้ต่อท้าย notebook ML (หลัง Step 17) แล้วรันหลังเทรนโมเดลเสร็จ
# - รันใหม่ทุกครั้งที่เพิ่มหรือแก้ลูกค้าในเว็บ
# - ใช้ตัวแปรจาก notebook: best_model, calibrate, add_features, FEATURES, kmeans, seg_prep,
#   SEGMENT_NAMES, BEST_THRESHOLD, BEST_NAME, final, PROFIT_PER_YES, COST_PER_CALL
#
# ขั้นตอน
#   1) รันบล็อกนี้ จะมีปุ่มให้เลือกไฟล์ → เลือก data/bank_data.xlsx ในโฟลเดอร์เว็บ
#   2) Colab ดาวน์โหลดไฟล์ scores_from_colab.xlsx ให้
#   3) ในเว็บ หน้า 'จัดอันดับลูกค้า (ML)' → 'นำเข้าคะแนนจาก Colab' → อัปโหลดไฟล์นี้
# ============================================================
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from google.colab import files
    uploaded = files.upload()                       # เลือก bank_data.xlsx
    WEB_FILE = next(iter(uploaded))
except ImportError:
    files = None                                    # ใช้ตอนทดสอบนอก Colab เท่านั้น
    WEB_FILE = WEB_FILE_FOR_TEST

# ------------------------------------------------------------
# 19.1 อ่านลูกค้าทั้งหมดจากชีต customers
# ------------------------------------------------------------
sheet_df = pd.read_excel(WEB_FILE, sheet_name='customers', dtype={'customer_id': str})
print('อ่านลูกค้า', len(sheet_df), 'คน')

# ------------------------------------------------------------
# 19.2 ให้คะแนนด้วยโมเดลที่เทรนไว้ (ขั้นตอนเดียวกับ Step 16)
# ------------------------------------------------------------
data = sheet_df.copy()
for col in ['age', 'pdays', 'previous', 'campaign']:
    data[col] = pd.to_numeric(data[col], errors='coerce')
feat = add_features(data)
ok = feat[FEATURES + ['pdays']].notna().all(axis=1)          # ให้คะแนนเฉพาะแถวที่ข้อมูลครบ

prob = pd.Series(np.nan, index=feat.index)
prob[ok] = calibrate(best_model.predict_proba(feat.loc[ok, FEATURES])[:, 1])
persona = pd.Series('', index=feat.index, dtype=object)
persona[ok] = [SEGMENT_NAMES.get(int(s), f'Segment {int(s)}')
               for s in kmeans.predict(seg_prep.transform(feat.loc[ok]))]
now = datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')

scores = pd.DataFrame({
    'customer_id': sheet_df['customer_id'],
    'prob_yes': prob.round(4),
    'persona': persona.where(ok, ''),
    'action': np.where(ok, np.where(prob >= BEST_THRESHOLD, 'ควรโทรก่อน', 'ลำดับรอง'), ''),
    'scored_at': np.where(ok, now, ''),
})

# ------------------------------------------------------------
# 19.3 ข้อมูลโมเดล (หน้า ML ของเว็บใช้แสดง)
# ------------------------------------------------------------
def _test_score(metric):
    try:
        return round(float(final.loc[f'{BEST_NAME} (test)', metric]), 4)
    except Exception:
        return ''

model_info = pd.DataFrame([
    ['model', BEST_NAME],
    ['threshold', float(BEST_THRESHOLD)],
    ['test_roc_auc', _test_score('ROC-AUC')],
    ['test_recall', _test_score('Recall')],
    ['test_f1', _test_score('F1')],
    ['features', ', '.join(FEATURES)],
    ['profit_per_yes', PROFIT_PER_YES],
    ['cost_per_call', COST_PER_CALL],
    ['n_scored', int(ok.sum())],
    ['scored_at', now],
], columns=['key', 'value'])

# ------------------------------------------------------------
# 19.4 บันทึกและดาวน์โหลดไฟล์คะแนน
# ------------------------------------------------------------
OUT_FILE = 'scores_from_colab.xlsx'
with pd.ExcelWriter(OUT_FILE) as writer:
    scores.to_excel(writer, sheet_name='scores', index=False)
    model_info.to_excel(writer, sheet_name='model_info', index=False)

print(f'ให้คะแนนแล้ว {int(ok.sum())} คน (ข้อมูลไม่ครบ {int((~ok).sum())} คน) | '
      f'ควรโทรก่อน {int((prob >= BEST_THRESHOLD).sum())} คน | เวลา {now}')
if files is not None:
    files.download(OUT_FILE)
    print("นำไฟล์ scores_from_colab.xlsx ไปอัปโหลดในเว็บ หน้า 'จัดอันดับลูกค้า (ML)'")

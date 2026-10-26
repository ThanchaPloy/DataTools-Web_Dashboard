# Tableau Dashboard

## 1. สร้างไฟล์ workbook (รันในเครื่องตัวเอง)

```bash
python scripts/build_tableau.py
```

ได้ไฟล์ `tableau/<ชื่อกลุ่ม>_dashboard.twb` ที่เชื่อมกับ `data/bank_data.xlsx` ในเครื่องแล้ว
(ต้องรันในเครื่องตัวเอง เพราะไฟล์จะจำตำแหน่งของ bank_data.xlsx ในเครื่องนั้น)

## 2. เปิดใน Tableau Public แล้วบันทึกเป็น .twbx

1. เปิด Tableau Public → File → Open → เลือกไฟล์ `.twb`
2. ถ้าขึ้นว่าหาไฟล์ข้อมูลไม่เจอ ให้กด Browse แล้วเลือก `data/bank_data.xlsx`
3. เปิดแท็บ **Dashboard** ปรับขนาด/สีได้ตามชอบ
4. File → **Save to Tableau Public As...** → ตั้งชื่อ `<ชื่อกลุ่ม>_dashboard`
5. ได้ลิงก์ → คัดลอกไปใส่ `TABLEAU_URL` ใน `core/config.py` (หรือวางในหน้า Tableau ของเว็บ)
6. ไฟล์ .twbx สำหรับส่งงาน: ในหน้า Tableau Public ของงานนั้น กด Download → Tableau Workbook
   (ถ้าใช้ Tableau Desktop: File → Save As → Tableau Packaged Workbook (.twbx))

ข้อมูลอัปเดต: แก้ข้อมูลในเว็บแล้ว ใน Tableau กด Data → Refresh แล้ว Save to Tableau Public อีกครั้ง

## ชีตในไฟล์

| ชีต | แสดงอะไร |
|---|---|
| KPI ลูกค้าทั้งหมด / โทรแล้ว / อัตราตอบรับ / รอโทร | ตัวเลขสรุปด้านบน dashboard |
| อัตราตอบรับรายเดือน | กราฟเส้น ช่วงเวลาที่ควรโทร |
| อัตราตอบรับตามอาชีพ | แท่งแนวนอน เรียงจากมากไปน้อย |
| อัตราตอบรับตามกลุ่มอายุ | แท่ง 5 กลุ่มอายุ |
| ช่องทาง x ผลแคมเปญก่อน | heatmap มือถือ/โทรศัพท์บ้าน × ผลแคมเปญก่อน |
| สถานะลูกค้า | ตอบรับ / ไม่ตอบรับ / รอโทร |
| ลูกค้ารอโทรตามคะแนน ML | จำนวนลูกค้ารอโทรแยกตามระดับคะแนนจากโมเดล |

## ถ้าเปิดไฟล์ไม่ได้: สร้างเองใน Tableau (ราว 30 นาที)

Connect → Microsoft Excel → `bank_data.xlsx` → ลากชีต `customers` → ไปที่ Sheet 1
แล้วสร้าง Calculated Field (Analysis → Create Calculated Field) ดังนี้

| ชื่อฟิลด์ | สูตร |
|---|---|
| อัตราตอบรับ | `SUM(IIF([y]='yes',1,0)) / SUM(IIF([y]='yes' OR [y]='no',1,0))` (Format เป็น %) |
| โทรแล้ว (คน) | `IIF([y]='yes' OR [y]='no',1,0)` |
| รอโทร (คน) | `IIF([y]='pending',1,0)` |
| สถานะลูกค้า | `CASE [y] WHEN 'yes' THEN 'ตอบรับ' WHEN 'no' THEN 'ไม่ตอบรับ' ELSE 'รอโทร' END` |
| กลุ่มอายุ | `IF [age] < 30 THEN '17-29' ELSEIF [age] < 40 THEN '30-39' ELSEIF [age] < 50 THEN '40-49' ELSEIF [age] < 60 THEN '50-59' ELSE '60+' END` |
| เดือน (เรียงลำดับ) | `CASE [month] WHEN 'mar' THEN '03 มี.ค.' WHEN 'apr' THEN '04 เม.ย.' ... WHEN 'dec' THEN '12 ธ.ค.' END` |
| ระดับคะแนน ML | `IF ISNULL([prob_yes]) THEN '4 ยังไม่มีคะแนน' ELSEIF [prob_yes] >= 0.5 THEN '1 สูง' ELSEIF [prob_yes] >= 0.2 THEN '2 กลาง' ELSE '3 ต่ำ' END` |

แล้วสร้างแต่ละชีตตามตารางด้านบน: ลากมิติ (เช่น job) ไป Rows, ลาก `อัตราตอบรับ` ไป Columns,
ลาก `อัตราตอบรับ` ไป Label → Sort มากไปน้อย จากนั้น Dashboard → New Dashboard แล้วลากชีตมาวาง

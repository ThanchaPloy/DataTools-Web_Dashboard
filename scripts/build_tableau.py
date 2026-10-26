"""
สร้างไฟล์ Tableau workbook (.twb) ที่เชื่อมกับ data/bank_data.xlsx (ชีต customers)
มี 10 ชีต + Dashboard 1 หน้า เปิดด้วย Tableau Public / Desktop แล้ว Save As เป็น .twbx

    python scripts/build_tableau.py
ได้ไฟล์ tableau/<GROUP_NAME>_dashboard.twb
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import config as C  # noqa: E402

DS = "federated.bank_call_tracker"
OUT_DIR = C.BASE_DIR / "tableau"

# ------------------------------------------------------------
# ฟิลด์จาก Excel
# ------------------------------------------------------------
BASE = {  # ชื่อคอลัมน์: (datatype, role, type)
    "customer_id": ("string", "dimension", "nominal"),
    "age": ("integer", "measure", "quantitative"),
    "job": ("string", "dimension", "nominal"),
    "contact": ("string", "dimension", "nominal"),
    "month": ("string", "dimension", "nominal"),
    "poutcome": ("string", "dimension", "nominal"),
    "y": ("string", "dimension", "nominal"),
    "prob_yes": ("real", "measure", "quantitative"),
}
CAPTIONS = {"job": "อาชีพ", "contact": "ช่องทางติดต่อ", "poutcome": "ผลแคมเปญก่อน",
            "customer_id": "รหัสลูกค้า", "age": "อายุ", "month": "เดือน", "y": "ผลการโทร",
            "prob_yes": "โอกาสตอบรับ (ML)"}

# ------------------------------------------------------------
# Calculated fields: id: (caption, datatype, role, type, formula, format)
# ------------------------------------------------------------
CALC = {
    "Calculation_conv": ("อัตราตอบรับ", "real", "measure", "quantitative",
                         "SUM(IIF([y]='yes',1,0)) / SUM(IIF([y]='yes' OR [y]='no',1,0))", "p0.0%"),
    "Calculation_called": ("โทรแล้ว (คน)", "integer", "measure", "quantitative",
                           "IIF([y]='yes' OR [y]='no',1,0)", "n#,##0"),
    "Calculation_yes": ("ตอบรับ (คน)", "integer", "measure", "quantitative",
                        "IIF([y]='yes',1,0)", "n#,##0"),
    "Calculation_pending": ("รอโทร (คน)", "integer", "measure", "quantitative",
                            "IIF([y]='pending',1,0)", "n#,##0"),
    "Calculation_status": ("สถานะลูกค้า", "string", "dimension", "nominal",
                           "CASE [y] WHEN 'yes' THEN 'ตอบรับ' WHEN 'no' THEN 'ไม่ตอบรับ' "
                           "ELSE 'รอโทร' END", None),
    "Calculation_agegroup": ("กลุ่มอายุ", "string", "dimension", "nominal",
                             "IF [age] < 30 THEN '17-29' ELSEIF [age] < 40 THEN '30-39' "
                             "ELSEIF [age] < 50 THEN '40-49' ELSEIF [age] < 60 THEN '50-59' "
                             "ELSE '60+' END", None),
    "Calculation_month": ("เดือน (เรียงลำดับ)", "string", "dimension", "nominal",
                          "CASE [month] WHEN 'jan' THEN '01 ม.ค.' WHEN 'feb' THEN '02 ก.พ.' "
                          "WHEN 'mar' THEN '03 มี.ค.' WHEN 'apr' THEN '04 เม.ย.' "
                          "WHEN 'may' THEN '05 พ.ค.' WHEN 'jun' THEN '06 มิ.ย.' "
                          "WHEN 'jul' THEN '07 ก.ค.' WHEN 'aug' THEN '08 ส.ค.' "
                          "WHEN 'sep' THEN '09 ก.ย.' WHEN 'oct' THEN '10 ต.ค.' "
                          "WHEN 'nov' THEN '11 พ.ย.' WHEN 'dec' THEN '12 ธ.ค.' END", None),
    "Calculation_score": ("ระดับคะแนน ML", "string", "dimension", "nominal",
                          "IF ISNULL([prob_yes]) THEN '4 ยังไม่มีคะแนน' "
                          "ELSEIF [prob_yes] >= 0.5 THEN '1 สูง (≥ 50%)' "
                          "ELSEIF [prob_yes] >= 0.2 THEN '2 กลาง (20-50%)' "
                          "ELSE '3 ต่ำ (< 20%)' END", None),
}
CALC_DEPS = {"Calculation_conv": ["y"], "Calculation_called": ["y"], "Calculation_yes": ["y"],
             "Calculation_pending": ["y"], "Calculation_status": ["y"],
             "Calculation_agegroup": ["age"], "Calculation_month": ["month"],
             "Calculation_score": ["prob_yes"]}


def col_xml(name, with_calc=True):
    """นิยามคอลัมน์ (ใช้ทั้งใน datasource และ datasource-dependencies)"""
    if name in CALC:
        cap, dt, role, typ, formula, fmt = CALC[name]
        f = f" default-format={quoteattr(fmt)}" if fmt else ""
        calc = f"<calculation class='tableau' formula={quoteattr(formula)} />" if with_calc else ""
        return (f"<column caption={quoteattr(cap)} datatype='{dt}'{f} name='[{name}]' "
                f"role='{role}' type='{typ}'>{calc}</column>")
    dt, role, typ = BASE[name]
    return (f"<column caption={quoteattr(CAPTIONS[name])} datatype='{dt}' name='[{name}]' "
            f"role='{role}' type='{typ}' />")


# ------------------------------------------------------------
# อ้างอิงฟิลด์บนชั้นวาง: (field, derivation)
#   derivation: None = dimension, Sum, Count, User = calc ที่ aggregate ในตัว
# ------------------------------------------------------------
PREFIX = {"None": "none", "Sum": "sum", "Count": "cnt", "User": "usr"}


def inst(field, deriv):
    if deriv == "None":
        typ = "nk"
    else:
        typ = "qk"
    return f"[{PREFIX[deriv]}:{field}:{typ}]"


def ref(field, deriv):
    return f"[{DS}].{inst(field, deriv)}"


def inst_xml(field, deriv):
    typ = "nominal" if deriv == "None" else "quantitative"
    return (f"<column-instance column='[{field}]' derivation='{deriv}' "
            f"name='{inst(field, deriv)}' pivot='key' type='{typ}' />")


def worksheet(name, rows, cols, mark, encodings=(), sort=None, fields=()):
    """
    rows/cols: list ของ (field, deriv)   encodings: list ของ (ช่อง, field, deriv)
    sort: (dimension field, measure field, deriv, 'DESC'/'ASC')
    """
    used = list(rows) + list(cols) + [(f, d) for _, f, d in encodings] + list(fields)
    if sort:
        used.append((sort[1], sort[2]))
    names = []
    for f, _ in used:
        for n in CALC_DEPS.get(f, []) + [f]:
            if n not in names:
                names.append(n)
    insts = []
    for f, d in used:
        if (f, d) not in insts:
            insts.append((f, d))
    deps = "".join(col_xml(n) for n in names) + "".join(inst_xml(f, d) for f, d in insts)
    sort_xml = ""
    if sort:
        sort_xml = (f"<sort class='computed' column='{ref(sort[0], 'None')}' "
                    f"direction='{sort[3]}' using='{ref(sort[1], sort[2])}' />")
    enc = "".join(f"<{ch} column='{ref(f, d)}' />" for ch, f, d in encodings)
    enc_xml = f"<encodings>{enc}</encodings>" if enc else ""
    shelf = lambda items: " / ".join(ref(f, d) for f, d in items)  # noqa: E731
    return f"""
    <worksheet name={quoteattr(name)}>
      <table>
        <view>
          <datasources><datasource caption='ลูกค้า (bank_data)' name='{DS}' /></datasources>
          <datasource-dependencies datasource='{DS}'>{deps}</datasource-dependencies>
          {sort_xml}
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view><breakdown value='auto' /></view>
            <mark class='{mark}' />
            {enc_xml}
          </pane>
        </panes>
        <rows>{shelf(rows)}</rows>
        <cols>{shelf(cols)}</cols>
      </table>
    </worksheet>"""


SHEETS = [
    # (ชื่อ, rows, cols, mark, encodings, sort)
    ("KPI ลูกค้าทั้งหมด", [], [], "Text", [("text", "customer_id", "Count")], None),
    ("KPI โทรแล้ว", [], [], "Text", [("text", "Calculation_called", "Sum")], None),
    ("KPI อัตราตอบรับ", [], [], "Text", [("text", "Calculation_conv", "User")], None),
    ("KPI รอโทร", [], [], "Text", [("text", "Calculation_pending", "Sum")], None),
    ("อัตราตอบรับรายเดือน", [("Calculation_conv", "User")], [("Calculation_month", "None")],
     "Line", [("text", "Calculation_conv", "User")], None),
    ("อัตราตอบรับตามอาชีพ", [("job", "None")], [("Calculation_conv", "User")], "Bar",
     [("text", "Calculation_conv", "User"), ("color", "Calculation_conv", "User")],
     ("job", "Calculation_conv", "User", "DESC")),
    ("อัตราตอบรับตามกลุ่มอายุ", [("Calculation_conv", "User")], [("Calculation_agegroup", "None")],
     "Bar", [("text", "Calculation_conv", "User")], None),
    ("ช่องทาง x ผลแคมเปญก่อน", [("poutcome", "None")], [("contact", "None")], "Square",
     [("color", "Calculation_conv", "User"), ("text", "Calculation_conv", "User")], None),
    ("สถานะลูกค้า", [("Calculation_status", "None")], [("customer_id", "Count")], "Bar",
     [("color", "Calculation_status", "None"), ("text", "customer_id", "Count")], None),
    ("ลูกค้ารอโทรตามคะแนน ML", [("Calculation_score", "None")], [("Calculation_pending", "Sum")],
     "Bar", [("text", "Calculation_pending", "Sum")], None),
]

# ------------------------------------------------------------
# Dashboard 1200 x 900: แถว KPI 4 ช่อง + กราฟ 3 แถว x 2 คอลัมน์
# ------------------------------------------------------------
W, H = 1200, 900
_zid = iter(range(3, 1000))


def zone(name, x, y, w, h):
    sx, sy = 100000 / W, 100000 / H
    return (f"<zone h='{round(h * sy)}' id='{next(_zid)}' name={quoteattr(name)} "
            f"w='{round(w * sx)}' x='{round(x * sx)}' y='{round(y * sy)}' />")


def dashboard_xml():
    kpis = [s[0] for s in SHEETS[:4]]
    charts = [s[0] for s in SHEETS[4:]]
    title_h, kpi_h = 60, 110
    zs = [f"<zone h='{round(title_h / H * 100000)}' id='{next(_zid)}' type-v2='text' w='100000' x='0' y='0'>"
          "<formatted-text><run bold='true' fontsize='18'>"
          + escape(f"Bank Call Tracker: ใครควรโทรหาก่อน ({C.GROUP_NAME})")
          + "</run></formatted-text></zone>"]
    kw = W / 4
    for i, n in enumerate(kpis):
        zs.append(zone(n, i * kw, title_h, kw, kpi_h))
    top = title_h + kpi_h
    ch = (H - top) / 3
    cw = W / 2
    for i, n in enumerate(charts):
        zs.append(zone(n, (i % 2) * cw, top + (i // 2) * ch, cw, ch))
    return f"""
    <dashboard name='Dashboard'>
      <style />
      <size maxheight='{H}' maxwidth='{W}' minheight='{H}' minwidth='{W}' />
      <zones>
        <zone h='100000' id='2' type-v2='layout-basic' w='100000' x='0' y='0'>
          {''.join(zs)}
        </zone>
      </zones>
    </dashboard>"""


def window_xml(name):
    return f"""<window class='worksheet' name={quoteattr(name)}>
      <cards>
        <edge name='left'><strip size='160'><card type='pages' /><card type='filters' /><card type='marks' /></strip></edge>
        <edge name='top'><strip size='2147483647'><card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip><strip size='31'><card type='title' /></strip></edge>
      </cards>
    </window>"""


EMPTY_SHEET = """
    <worksheet name='Sheet 1'>
      <table>
        <view><datasources /><aggregation value='true' /></view>
        <style />
        <panes><pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view><mark class='Automatic' /></pane></panes>
        <rows /><cols />
      </table>
    </worksheet>"""


def workbook_xml(sheets, with_dashboard=True, empty=False):
    excel = C.EXCEL_PATH.resolve()
    ds_cols = "".join(col_xml(n) for n in list(BASE) + list(CALC))
    ws_xml = EMPTY_SHEET if empty else "".join(worksheet(*s) for s in sheets)
    names = ["Sheet 1"] if empty else [s[0] for s in sheets]
    dash = f"<dashboards>{dashboard_xml()}</dashboards>" if with_dashboard else ""
    windows = "".join(window_xml(n) for n in names)
    return f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2023.3.0 (20233.23.1017.0948)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
    <preference name='ui.shelf.height' value='26' />
  </preferences>
  <datasources>
    <datasource caption='ลูกค้า (bank_data)' inline='true' name='{DS}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='bank_data' name='excel-direct.bank_data'>
            <connection class='excel-direct' cleaning='no' compat='no' dataRefreshTime='' filename={quoteattr(str(excel))} interpretationMode='0' password='' server='' validate='no' />
          </named-connection>
        </named-connections>
        <relation connection='excel-direct.bank_data' name='customers' table='[customers$]' type='table' />
      </connection>
      {ds_cols}
    </datasource>
  </datasources>
  <worksheets>{ws_xml}
  </worksheets>
  {dash}
  <windows source-height='30'>
    {windows}
  </windows>
</workbook>
"""


def build() -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    g = C.GROUP_NAME
    files = {
        f"{g}_dashboard.twb": workbook_xml(SHEETS, with_dashboard=True),
        f"test1_{g}_connection.twb": workbook_xml([], with_dashboard=False, empty=True),
        f"test2_{g}_one_sheet.twb": workbook_xml([SHEETS[5]], with_dashboard=False),
        f"test3_{g}_all_sheets.twb": workbook_xml(SHEETS, with_dashboard=False),
    }
    for name, xml in files.items():
        (OUT_DIR / name).write_text(xml, encoding="utf-8")
        print("สร้างไฟล์:", OUT_DIR / name)
    return OUT_DIR / f"{g}_dashboard.twb"


if __name__ == "__main__":
    build()
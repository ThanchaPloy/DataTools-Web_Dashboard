"""
ธีมและส่วนประกอบหน้าตาที่ทุกหน้าใช้ร่วมกัน
- ฟอนต์ IBM Plex Sans Thai, พื้นหลังสว่าง, การ์ดสีขาว
- หัวหน้าเพจ, การ์ดตัวเลข KPI
- รูปแบบกราฟ Plotly ให้เข้ากับธีม
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ------------------------------------------------------------
# สีหลักของเว็บ
# ------------------------------------------------------------
PRIMARY = "#1D4ED8"      # น้ำเงิน: ปุ่ม ลิงก์ ข้อมูลหลัก
NAVY = "#0F1E3D"         # หัวข้อ
TEAL = "#0E9F8E"         # ตอบรับ / ดี
AMBER = "#D97706"        # รอโทร / เตือน
CORAL = "#DC5B3C"        # ไม่ตอบรับ
SLATE = "#64748B"        # ข้อความรอง
GRID = "#E6EAF0"
STATUS_COLORS = {"ตอบรับ": TEAL, "ไม่ตอบรับ": CORAL, "รอโทร": AMBER}

FONT = "IBM Plex Sans Thai, sans-serif"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea, select,
[data-testid="stSidebar"], [data-testid="stMetricValue"] {{
    font-family: {FONT};
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 4.2rem; padding-bottom: 3rem; max-width: 1280px; }}
h1, h2, h3 {{ color: {NAVY}; font-weight: 600; letter-spacing: -0.01em; }}

/* sidebar */
[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {GRID}; }}

/* หัวหน้าเพจ */
.page-header {{ margin-bottom: 1.4rem; }}
.page-header .eyebrow {{ color: {PRIMARY}; font-size: 0.82rem; font-weight: 600; line-height: 1.6;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.2rem; }}
.page-header h1 {{ font-size: 1.85rem; margin: 0; padding: 0; }}
.page-header p {{ color: {SLATE}; margin: 0.35rem 0 0; font-size: 1rem; }}

/* การ์ด KPI */
.kpi {{ background: #FFFFFF; border: 1px solid {GRID}; border-radius: 14px;
    padding: 1.05rem 1.2rem; height: 100%; }}
.kpi .label {{ color: {SLATE}; font-size: 0.86rem; margin-bottom: 0.3rem; }}
.kpi .value {{ color: {NAVY}; font-size: 1.75rem; font-weight: 600; line-height: 1.2; }}
.kpi .sub {{ font-size: 0.82rem; margin-top: 0.3rem; color: {SLATE}; }}
.kpi.accent {{ border-top: 3px solid {PRIMARY}; }}
.kpi.teal {{ border-top: 3px solid {TEAL}; }}
.kpi.amber {{ border-top: 3px solid {AMBER}; }}
.kpi.coral {{ border-top: 3px solid {CORAL}; }}

/* กล่องเนื้อหา */
.card {{ background: #FFFFFF; border: 1px solid {GRID}; border-radius: 14px;
    padding: 1.1rem 1.3rem; margin-bottom: 1rem; }}
.card h4 {{ margin: 0 0 0.4rem; color: {NAVY}; font-weight: 600; font-size: 1.02rem; }}
.card p {{ margin: 0; color: #334155; font-size: 0.93rem; line-height: 1.6; }}
.muted {{ color: {SLATE}; font-size: 0.88rem; }}

/* ป้ายสถานะ */
.badge {{ display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
    font-size: 0.8rem; font-weight: 500; }}
.badge.good {{ background: #E3F5F2; color: #0B6E62; }}
.badge.warn {{ background: #FDF1E1; color: #8A4B06; }}
.badge.bad  {{ background: #FCE8E3; color: #8F3420; }}

/* ปุ่มและแท็บ */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
    border-radius: 10px; font-weight: 500; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; }}
.stTabs [data-baseweb="tab"] {{ padding: 0.5rem 1rem; }}
.change-bar {{ background: #FFFFFF; border: 1px solid {GRID}; border-radius: 12px;
    padding: 0.75rem 1rem; color: #334155; font-size: 0.95rem; }}
.change-bar b {{ color: {NAVY}; }}
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border: 1px solid {GRID}; border-radius: 12px; }}
</style>
"""


def apply_theme():
    """เรียกครั้งเดียวต่อการรัน (ใน app.py)"""
    st.markdown(_CSS, unsafe_allow_html=True)
    _register_plotly_template()


def page_header(title: str, subtitle: str = "", eyebrow: str = ""):
    eyebrow_html = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="page-header">{eyebrow_html}<h1>{title}</h1>{sub_html}</div>',
                unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "", tone: str = "accent"):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="kpi {tone}"><div class="label">{label}</div>'
                f'<div class="value">{value}</div>{sub_html}</div>', unsafe_allow_html=True)


def card(title: str, body: str):
    st.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>',
                unsafe_allow_html=True)


def badge(text: str, kind: str = "good") -> str:
    return f'<span class="badge {kind}">{text}</span>'


def _register_plotly_template():
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family=FONT, size=13, color="#334155"),
        title=dict(font=dict(size=15, color=NAVY), x=0, xanchor="left"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=[PRIMARY, TEAL, AMBER, CORAL, "#7C3AED", SLATE],
        xaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False),
        margin=dict(l=10, r=10, t=50, b=10),
        hoverlabel=dict(font=dict(family=FONT)),
        legend=dict(orientation="h", y=-0.2),
    )
    pio.templates["bank"] = tmpl
    pio.templates.default = "plotly_white+bank"


def fmt_pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def fmt_int(x) -> str:
    return f"{int(x):,}"

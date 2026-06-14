#!/usr/bin/env python3
"""高考志愿推荐方案 PDF 报告生成器。

用法:
  python3 scripts/generate_pdf.py <report.json> [output.pdf]

输入 JSON 格式:
{
  "user": {
    "province": "湖北",
    "score": 580,
    "rank": 28000,
    "subject": "物理"
  },
  "recommendations": [
    {
      "tier": "冲",
      "school": "武汉理工大学",
      "major": "电子信息类",
      "rank": 18500,
      "score": 612,
      "year": 2024,
      "note": "211，工科底子硬，值得一搏"
    }
  ],
  "summary": "分析总结文字...",
  "disclaimer": "本报告由AI生成，仅供参考。最终志愿填报请以省教育考试院官方数据为准。"
}
"""

import json
import sys
import os
from datetime import datetime

# 检查依赖
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("需要安装 reportlab: pip install reportlab --break-system-packages")
    sys.exit(1)

# ── 字体注册 ──────────────────────────────────────────
FONT_PATHS = [
    "/Library/Fonts/Microsoft/SimHei.ttf",       # macOS Microsoft Office
    "/System/Library/Fonts/PingFang.ttc",         # macOS 系统字体
    "/System/Library/Fonts/STHeiti Light.ttc",    # macOS 华文黑体
    "C:/Windows/Fonts/simhei.ttf",                # Windows
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux
]

FONT_NAME = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont('CJK', fp))
            FONT_NAME = 'CJK'
            break
        except Exception:
            continue

if FONT_NAME is None:
    print("警告: 未找到中文字体，将使用默认字体（中文可能不显示）")
    print("尝试过的路径:", FONT_PATHS)
    FONT_NAME = 'Helvetica'

# ── 颜色 ──────────────────────────────────────────────
DARK_BG = HexColor('#0F172A')
DARK_CARD = HexColor('#1E293B')
ACCENT_RED = HexColor('#EF4444')
ACCENT_YELLOW = HexColor('#F59E0B')
ACCENT_GREEN = HexColor('#10B981')
TEXT_PRIMARY = HexColor('#F8FAFC')
TEXT_SECONDARY = HexColor('#94A3B8')
TEXT_DARK = HexColor('#334155')
BORDER_COLOR = HexColor('#CBD5E1')
TABLE_HEADER_BG = HexColor('#1E293B')
ROW_ALT_BG = HexColor('#F1F5F9')

TIER_COLORS = {
    '冲': ACCENT_RED,
    '稳': ACCENT_YELLOW,
    '保': ACCENT_GREEN,
}

# ── 样式 ──────────────────────────────────────────────
cover_title_style = ParagraphStyle(
    'CoverTitle', fontName=FONT_NAME, fontSize=28, leading=38,
    textColor=white, alignment=TA_CENTER, spaceAfter=12
)
cover_subtitle_style = ParagraphStyle(
    'CoverSubtitle', fontName=FONT_NAME, fontSize=14, leading=22,
    textColor=TEXT_SECONDARY, alignment=TA_CENTER
)
section_title_style = ParagraphStyle(
    'SectionTitle', fontName=FONT_NAME, fontSize=16, leading=24,
    textColor=DARK_BG, spaceAfter=10, spaceBefore=6
)
body_style = ParagraphStyle(
    'Body', fontName=FONT_NAME, fontSize=10, leading=18,
    textColor=TEXT_DARK
)
small_style = ParagraphStyle(
    'Small', fontName=FONT_NAME, fontSize=8, leading=12,
    textColor=TEXT_SECONDARY
)
table_cell_style = ParagraphStyle(
    'TableCell', fontName=FONT_NAME, fontSize=9, leading=14,
    textColor=TEXT_DARK
)
table_header_style = ParagraphStyle(
    'TableHeader', fontName=FONT_NAME, fontSize=9, leading=14,
    textColor=white
)
disclaimer_style = ParagraphStyle(
    'Disclaimer', fontName=FONT_NAME, fontSize=8, leading=14,
    textColor=TEXT_SECONDARY, alignment=TA_CENTER
)

# ── 页面构建 ──────────────────────────────────────────
def build_cover(user_info):
    """封面页"""
    elements = []
    elements.append(Spacer(1, 80 * mm))

    elements.append(Paragraph("高考志愿推荐方案", cover_title_style))
    elements.append(Spacer(1, 8 * mm))

    prov = user_info.get('province', '—')
    score = user_info.get('score', '—')
    rank = user_info.get('rank', '—')
    subject = user_info.get('subject', '—')

    elements.append(Paragraph(
        f"{prov} · {subject} · {score}分 · 位次{rank}",
        cover_subtitle_style
    ))
    elements.append(Spacer(1, 20 * mm))
    elements.append(Paragraph(
        f"生成日期：{datetime.now().strftime('%Y年%m月%d日')}",
        ParagraphStyle('CoverDate', fontName=FONT_NAME, fontSize=10,
                       leading=16, textColor=TEXT_SECONDARY, alignment=TA_CENTER)
    ))
    elements.append(Spacer(1, 15 * mm))
    elements.append(Paragraph(
        "AI 高考志愿顾问 · 仅供参考",
        ParagraphStyle('CoverBrand', fontName=FONT_NAME, fontSize=9,
                       leading=14, textColor=TEXT_SECONDARY, alignment=TA_CENTER)
    ))

    elements.append(PageBreak())
    return elements


def build_user_section(user_info):
    """用户信息区"""
    elements = []
    elements.append(Paragraph("考生信息", section_title_style))

    prov = user_info.get('province', '—')
    score = user_info.get('score', '—')
    rank = user_info.get('rank', '—')
    subject = user_info.get('subject', '—')

    info_data = [
        ['省份', prov, '分数', str(score)],
        ['位次', str(rank), '选科', subject],
    ]
    info_table = Table(info_data, colWidths=[50, 110, 50, 110])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_DARK),
        ('BACKGROUND', (0, 0), (0, -1), ROW_ALT_BG),
        ('BACKGROUND', (2, 0), (2, -1), ROW_ALT_BG),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8 * mm))
    return elements


def build_recommendation_table(recommendations):
    """冲稳保推荐表格"""
    elements = []
    elements.append(Paragraph("冲稳保推荐方案", section_title_style))

    headers = ['档次', '学校', '推荐专业', '最低位次', '最低分', '年份', '备注']
    col_widths = [40, 100, 82, 58, 48, 38, 100]

    header_row = [Paragraph(h, table_header_style) for h in headers]
    data = [header_row]

    for r in recommendations:
        tier = r.get('tier', '—')
        tier_color = TIER_COLORS.get(tier, TEXT_DARK)
        tier_style = ParagraphStyle(
            'TierCell', fontName=FONT_NAME, fontSize=9, leading=14,
            textColor=tier_color
        )

        rank_val = r.get('rank')
        score_val = r.get('score')
        year_val = r.get('year', '—')

        row = [
            Paragraph(tier, tier_style),
            Paragraph(r.get('school', '—'), table_cell_style),
            Paragraph(r.get('major', '—'), table_cell_style),
            Paragraph(str(rank_val) if rank_val else '—', table_cell_style),
            Paragraph(str(score_val) if score_val else '—', table_cell_style),
            Paragraph(str(year_val), table_cell_style),
            Paragraph(r.get('note', ''), table_cell_style),
        ]
        data.append(row)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table_style_cmds = [
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (3, 0), (4, 0), 'CENTER'),
        ('ALIGN', (5, 0), (5, 0), 'CENTER'),
    ]
    # 交替行背景
    for i in range(1, len(data)):
        if i % 2 == 0:
            table_style_cmds.append(('BACKGROUND', (0, i), (-1, i), ROW_ALT_BG))

    table.setStyle(TableStyle(table_style_cmds))
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))
    return elements


def build_summary(summary_text):
    """分析总结"""
    elements = []
    elements.append(Paragraph("分析与建议", section_title_style))
    # 清理文本，处理换行
    clean = summary_text.replace('\n', '<br/>')
    elements.append(Paragraph(clean, body_style))
    elements.append(Spacer(1, 8 * mm))
    return elements


def build_footer(disclaimer_text):
    """免责声明"""
    elements = []
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        ParagraphStyle('Line', fontName=FONT_NAME, fontSize=8,
                       textColor=BORDER_COLOR, alignment=TA_CENTER)
    ))
    elements.append(Paragraph(
        disclaimer_text or "本报告由AI生成，仅供参考。最终志愿填报请以省教育考试院官方数据为准。",
        disclaimer_style
    ))
    return elements


# ── 主流程 ────────────────────────────────────────────
def generate_pdf(input_json_path, output_path=None):
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if output_path is None:
        base = os.path.splitext(os.path.basename(input_json_path))[0]
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        output_path = os.path.join(desktop, f'{base}.pdf')

    user_info = data.get('user', {})
    recommendations = data.get('recommendations', [])
    summary = data.get('summary', '')
    disclaimer = data.get('disclaimer', '')

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title='高考志愿推荐方案',
        author='AI 高考志愿顾问',
    )

    # 背景色函数
    def cover_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()

    def normal_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT_NAME, 7)
        canvas.setFillColor(TEXT_SECONDARY)
        canvas.drawCentredString(A4[0] / 2, 12 * mm,
                                 f"高考志愿推荐方案 · 第 {canvas.getPageNumber()} 页")
        canvas.restoreState()

    elements = []
    # 封面
    elements.extend(build_cover(user_info))
    # 正文
    elements.extend(build_user_section(user_info))
    elements.extend(build_recommendation_table(recommendations))
    elements.extend(build_summary(summary))
    elements.extend(build_footer(disclaimer))

    doc.build(elements, onFirstPage=cover_bg, onLaterPages=normal_page)
    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <report.json> [output.pdf]")
        print(f"示例: python3 {sys.argv[0]} report.json ~/Desktop/志愿方案.pdf")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_path):
        print(f"错误: 文件不存在: {input_path}")
        sys.exit(1)

    try:
        result_path = generate_pdf(input_path, output_path)
        print(f"PDF 已生成: {result_path}")
        # 返回文件大小
        size_kb = os.path.getsize(result_path) / 1024
        print(f"文件大小: {size_kb:.0f} KB")
    except Exception as e:
        print(f"生成失败: {e}")
        sys.exit(1)

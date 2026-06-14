#!/usr/bin/env python3
"""真实录取数据模块 — 加载桌面高考志愿填报数据"""

import os, re, sqlite3, xlrd

DATA_DIR = r'E:\桌面\高考志愿填报\26年最新\全国31省市投档分数线（24年）'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'admission_data.db')

# 省份名 → 文件夹名映射
PROVINCE_DIRS = {}

def scan_provinces():
    """扫描所有省份数据目录"""
    global PROVINCE_DIRS
    PROVINCE_DIRS = {}
    if not os.path.exists(DATA_DIR):
        return
    for d in os.listdir(DATA_DIR):
        full = os.path.join(DATA_DIR, d)
        if os.path.isdir(full):
            # 提取省份名
            for p in ['江苏','浙江','广东','湖北','湖南','河南','山东','四川','安徽',
                       '福建','江西','河北','山西','陕西','甘肃','青海','云南','贵州',
                       '海南','辽宁','吉林','黑龙江','北京','天津','上海','重庆',
                       '广西','宁夏','新疆','西藏','内蒙古']:
                if p in d:
                    PROVINCE_DIRS[p] = full
                    break

def parse_xls(filepath):
    """解析 .xls 投档线文件，返回 list of dict"""
    try:
        wb = xlrd.open_workbook(filepath)
        ws = wb.sheet_by_index(0)
        results = []
        in_data = False
        for r in range(ws.nrows):
            row = [str(ws.cell_value(r, c)).strip() if ws.cell_value(r, c) else '' for c in range(min(6, ws.ncols))]
            # 检测数据开始行（院校代号为数字）
            if row[0].isdigit() and len(row[0]) == 4:
                in_data = True
            if not in_data:
                continue
            school_name = row[1] if len(row) > 1 else ''
            score_str = row[2] if len(row) > 2 else ''
            if school_name and score_str:
                try:
                    score = int(float(score_str))
                    # 清理学校名：去掉专业组编号和选科要求
                    clean_name = re.sub(r'\d+专业组.*$', '', school_name)
                    results.append({
                        'school_code': row[0],
                        'school_name': clean_name,
                        'full_entry': school_name,
                        'min_score': score,
                    })
                except ValueError:
                    continue
        return results
    except Exception as e:
        return []

def build_database():
    """构建SQLite数据库"""
    scan_provinces()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS admission")
    conn.execute("""
        CREATE TABLE admission (
            province TEXT,
            school_name TEXT,
            school_code TEXT,
            full_entry TEXT,
            min_score INTEGER,
            subject_type TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_province_school ON admission(province, school_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_province_score ON admission(province, min_score)")

    total = 0
    for prov, dirpath in PROVINCE_DIRS.items():
        for fname in os.listdir(dirpath):
            if not fname.endswith('.xls') and not fname.endswith('.xlsx'):
                continue
            full = os.path.join(dirpath, fname)
            subject = '物理' if '物理' in fname else ('历史' if '历史' in fname else '未知')
            results = parse_xls(full)
            for r in results:
                conn.execute(
                    "INSERT INTO admission VALUES (?,?,?,?,?,?)",
                    (prov, r['school_name'], r['school_code'], r['full_entry'], r['min_score'], subject)
                )
                total += 1

    conn.commit()
    conn.close()
    return total

def query_admission_data(province, school_name=None, max_score=None, min_score=None, subject=None, limit=20):
    """查询录取数据"""
    if not os.path.exists(DB_PATH):
        return None, "数据库未建立，请先运行 build_database()"

    conn = sqlite3.connect(DB_PATH)
    conditions = [f"province = '{province}'"]
    if school_name:
        conditions.append(f"school_name LIKE '%{school_name}%'")
    if max_score:
        conditions.append(f"min_score <= {max_score}")
    if min_score:
        conditions.append(f"min_score >= {min_score}")
    if subject:
        conditions.append(f"subject_type = '{subject}'")

    where = " AND ".join(conditions)
    rows = conn.execute(
        f"SELECT school_name, min_score, subject_type, full_entry FROM admission WHERE {where} ORDER BY min_score DESC LIMIT {limit}"
    ).fetchall()
    conn.close()
    return rows, None

def search_schools(province, keyword, limit=10):
    """模糊搜学校"""
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT DISTINCT school_name, min_score FROM admission WHERE province=? AND school_name LIKE ? ORDER BY min_score DESC LIMIT ?",
        (province, f'%{keyword}%', limit)
    ).fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    print("扫描省份数据...")
    scan_provinces()
    print(f"找到 {len(PROVINCE_DIRS)} 个省份: {list(PROVINCE_DIRS.keys())}")
    print("\n构建数据库...")
    count = build_database()
    print(f"导入 {count} 条录取记录")
    print("\n测试查询: 江苏 南京大学")
    rows, err = query_admission_data('江苏', '南京大学')
    if rows:
        for r in rows[:5]:
            print(f"  {r[0]} | {r[1]}分 | {r[2]}")

"""
三国志战略版 - 战报数据库藤甲兵数据提取脚本
用于从原始战报 JSON 目录中自动解析藤甲兵战法发动事件、战内统率与真实减伤率。
"""

import os
import json
import re
import argparse

def clean_html(raw_html: str) -> str:
    return re.sub(r'<.*?>', '', raw_html)

def extract_teng_jia_from_file(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
            data = json.load(fp)
    except Exception:
        return []

    events = []
    for g in data.get("detail", {}).get("groups", []):
        for ev in g.get("data", {}).get("events", []):
            fd = ev.get("event", {}).get("full_desc") or ""
            events.append(clean_html(fd))

    records = []
    for i, ev in enumerate(events):
        m = re.search(r'\[(.*?)\]发动战法【藤甲兵】', ev)
        if m:
            caster = m.group(1)
            
            # 提取后续生效的兵刃减伤率
            red_val = None
            for j in range(i + 1, min(len(events), i + 15)):
                m2 = re.search(r'受到的兵刃伤害降低了([\d\.]+)%', events[j])
                if m2:
                    red_val = float(m2.group(1))
                    break
            
            # 提取携带者在发动战法前的战内实时统率
            caster_ts = None
            for j in range(i - 1, -1, -1):
                m_ts = re.search(r'\[' + re.escape(caster) + r'\].*?统率.*?\(([\d\.]+)\)', events[j])
                if m_ts:
                    caster_ts = float(m_ts.group(1))
                    break

            # 提取武将基本信息
            hero_lvl = None
            skill_lvl = 10
            for side in ["my", "enemy"]:
                for h in data.get("lineup", {}).get(side, []):
                    if h.get("name") == caster:
                        hero_lvl = h.get("level")
                        skills = h.get("skills", {}).get("entries", [])
                        for s in skills:
                            v = s.get("value", 0)
                            if str(v).startswith("20095"):
                                skill_lvl = v % 100

            if caster and red_val is not None:
                records.append({
                    "report_file": os.path.basename(filepath),
                    "caster": caster,
                    "skill_name": "藤甲兵",
                    "skill_level": skill_lvl,
                    "hero_level": hero_lvl,
                    "battle_tongshuai": caster_ts,
                    "actual_reduction_pct": red_val
                })
    return records

def scan_directory(input_dir: str):
    matched = []
    if not os.path.exists(input_dir):
        print(f"目录不存在: {input_dir}")
        return matched

    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.endswith(".json"):
                p = os.path.join(root, f)
                res = extract_teng_jia_from_file(p)
                matched.extend(res)
    return matched

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取战报中藤甲兵的数据")
    parser.add_argument("--dir", type=str, required=True, help="战报JSON所在目录")
    args = parser.parse_args()

    results = scan_directory(args.dir)
    print(f"成功提取 {len(results)} 条藤甲兵战报记录：")
    print(json.dumps(results, ensure_ascii=False, indent=2))

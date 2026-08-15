#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 C-Eval 中文题翻译为英文(保留答案与学科标签), 生成语言对照基准 ceval_en.jsonl。
用 7B 做翻译, 127.0.0.1 直连(规避 ::1 IPv6 卡死)。
用途: 与原始中文 C-Eval 做"同题异语言"对照, 检验"语言胜任力门控"假说 H。
"""
import json, sys, urllib.request, time

SRC = "D:/方程验证/benchmark/ceval_bandok_clean.jsonl"
DST = "D:/方程验证/benchmark/ceval_en.jsonl"
MODEL = "qwen2.5:7b"
URL = "http://127.0.0.1:11434/api/generate"

def translate(rec):
    sys_p = ("You are a precise translator. Translate the Chinese multiple-choice "
             "question and its four options A-D into fluent English. Preserve meaning "
             "exactly. Output ONLY a JSON object with keys question,A,B,C,D and nothing else.")
    user = (f"question: {rec['question']}\n"
            f"A: {rec['A']}\nB: {rec['B']}\nC: {rec['C']}\nD: {rec['D']}")
    body = json.dumps({"model": MODEL, "prompt": f"<system>{sys_p}</system>\n{user}",
                       "stream": False, "options": {"temperature": 0, "seed": 20260810}})
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL, data=body.encode(),
                                         headers={"Content-Type": "application/json"})
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
            txt = resp.get("response", "").strip()
            # 容忍 ```json 包裹
            if txt.startswith("```"):
                txt = txt.split("```")[1]
                if txt.startswith("json"):
                    txt = txt[4:]
            obj = json.loads(txt)
            return {"question": obj["question"], "A": obj["A"], "B": obj["B"],
                    "C": obj["C"], "D": obj["D"], "answer": rec["answer"],
                    "subject": rec.get("subject", "")}
        except Exception as e:
            print(f"[warn] retry {attempt+1}: {e}", flush=True)
            time.sleep(3)
    # 翻译失败则保留原文并标记
    rec["translated"] = False
    return rec

def main():
    out = []
    with open(SRC, encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    print(f"[info] 翻译 {len(lines)} 题 -> {DST}", flush=True)
    for i, line in enumerate(lines, 1):
        rec = json.loads(line)
        t = translate(rec)
        if "translated" not in t:
            t["translated"] = True
        out.append(t)
        if i % 20 == 0:
            print(f"[info] {i}/{len(lines)} done", flush=True)
    with open(DST, "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    ok = sum(1 for o in out if o.get("translated"))
    print(f"[done] 翻译完成 {ok}/{len(out)} 成功", flush=True)

if __name__ == "__main__":
    main()

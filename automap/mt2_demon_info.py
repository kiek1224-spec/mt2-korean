#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""여신전생 2 — 전투 중 악마 정보 (롬에서 읽는다).

mt2_map_window.py 가 전투 중에 지도 대신 이 정보를 그린다. 브리지(mt2_bridge.lua)는 적 칸의
악마 번호·HP·MP 만 보내고, 이름·종족·능력치·특수기·상성·드롭은 전부 여기서 롬으로 푼다.

    python mt2_demon_info.py [롬] 102 127 141     # 그 번호의 정보를 글로 찍어 본다
    python mt2_demon_info.py [롬] --check         # 공략집 대조로 확인한 값들이 그대로 나오는지

근거 (2026-10-02, 원판 PRG 주소. 한글판은 원판 PRG 가 뒤쪽 절반 +0x40000)
  악마 표   PRG $32DEC (파일 0x32DFC), 번호 x 16바이트
            [0]Lv [1]체 [2]지 [3]힘(공) [4]속 [5]운 [6]방 [7]? [8]? [9..11]특수기(FF 없음)
            [12]? [13]상성 번호 [14]드롭 [15]항체
            dds.opatil.com 2편 악마 데이터 244마리와 대조: Lv·체·지·힘·속·운 98~99%, 방 85%(나머지는 공략집이 1 작다),
            상성 = [13]+1 이 240/244, 항체 = [15] 119/124.
  상성 표   PRG $32CC0 (파일 0x32CD0), 상성 번호 x 6바이트 = 반바이트 12개 중 앞 11개
            순서 총·검·화염·빙결·전격·파마·충격·속박(金縛)·주살(呪殺)·신경·정신
            반바이트 값: 0~8 = 0·12.5·…·100%, 9 150, A 200, B 250, C 300, D -50, E -100(반사), F 흡수(회복)
            공략집 「悪魔の攻撃相性データ」 32종 중 30종 일치. 100% 가 보통, 크면 더 아프다(보조 마법은 성공률),
            음수는 반사(우리가 받는 피해), 흡수는 HP 를 회복시킨다.
  종족      PRG $2D814 (파일 0x2D824) = 종족 1~27 의 첫 악마 번호(01 02 0C 18 …). 이름은 translations/races_ko.tsv
  특수기    0x00~0x3E = 마법(translations/spells_ko.tsv), 0x40~ = 특수 공격. 같은 기술이 위력별로 번호 여러 개를 쓴다
            (공략집 특수 목록과 롬 바이트를 맞대 정함. 공략집은 롬 순서대로 적지 않는다 - 라돈 0x40·0x41 = 화염,
             파프니르 0x44~0x46 = 냉기, 타라카 0x60 = 춤, 바실리스크 0x68 = 에너지 드레인).
  드롭      [14] 위 3비트 = 확률 등급(0 = 안 떨어뜨림), 아래 5비트 + 17 = 무기 번호(삼절곤·쿠치나와의 검 등 15종으로 확인).
            아래 5비트가 0x1E 면 메탈 카드(펑크·메탈).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 한글 이름표: 배포판은 같은 폴더의 names/, 작업 폴더에서는 ../translations/
TR = os.path.join(HERE, "names")
if not os.path.isdir(TR):
    TR = os.path.join(os.path.dirname(HERE), "translations")

DEMON_PRG, RESIST_PRG, RACE_PRG = 0x32DEC, 0x32CC0, 0x2D814
ATTRS = ("총", "검", "화염", "빙결", "전격", "파마", "충격", "속박", "주살", "신경", "정신")
# 반바이트 -> 퍼센트 (None = 흡수)
NIB = {0: 0, 1: 12.5, 2: 25, 3: 37.5, 4: 50, 5: 62.5, 6: 75, 7: 87.5, 8: 100, 9: 150, 10: 200, 11: 250,
       12: 300, 13: -50, 14: -100, 15: None}
SPECIAL = [  # (첫 번호, 끝 번호, 이름)
    (0x40, 0x43, "화염"), (0x44, 0x46, "냉기"), (0x47, 0x4B, "독가스"), (0x4C, 0x4E, "독침"),
    (0x4F, 0x52, "독 물기"), (0x53, 0x54, "노려보기"), (0x55, 0x58, "마비"), (0x59, 0x5A, "노려보기"),
    (0x5B, 0x5F, "석화"), (0x60, 0x61, "춤"), (0x62, 0x65, "포효"), (0x66, 0x67, "노래"),
    (0x68, 0x6C, "에너지 드레인"), (0x6E, 0x6F, "저주"), (0x70, 0x71, "죽음의 저주"), (0x72, 0x75, "데스 터치"),
    (0x76, 0x79, "할퀴기"), (0x7A, 0x7A, "자폭"), (0x7C, 0x7C, "도망"), (0x7D, 0x7D, "지키기"),
    (0x7E, 0x7E, "동료 부르기"),
]
# 번역표에 없는 무기 이름 (게임 속 한글 표기와 대조 전)
EXTRA_ITEMS = {17: "잭나이프", 18: "청동의 검", 21: "시미터", 25: "브로드소드"}
ALIGN = {}
for r in range(2, 14):
    ALIGN[r] = "EVIL"
for r in range(14, 19):
    ALIGN[r] = "NEUTRAL"
for r in range(19, 26):
    ALIGN[r] = "GOOD"


def _tsv(name):
    out = {}
    path = os.path.join(TR, name)
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        t = line.rstrip("\n").split("\t")
        if len(t) >= 2 and t[0].strip().isdigit():
            out[int(t[0])] = t[1]
    return out


class DemonDB:
    def __init__(self, rom_path):
        d = open(rom_path, "rb").read()
        if d[:4] != b"NES\x1a":
            raise ValueError("NES 롬이 아니다: %s" % rom_path)
        prg = d[16:16 + d[4] * 16384]
        off = 0x40000 if len(prg) >= 0x80000 else 0          # 한글판: 원판 PRG 가 뒤쪽 절반
        self.P = prg[off:off + 0x40000]
        self.names = _tsv("demons_ko.tsv")
        self.races = _tsv("races_ko.tsv")
        self.spells = _tsv("spells_ko.tsv")
        self.items = dict(EXTRA_ITEMS)
        for f in ("items_c11_ko.tsv", "items_c12_ko.tsv"):
            self.items.update(_tsv(f))
        self.race_start = list(self.P[RACE_PRG:RACE_PRG + 28])   # 종족 1.. 의 첫 번호
        self.nresist = max(self.P[DEMON_PRG + 16 * i + 13] for i in range(253)) + 1

    def record(self, i):
        return self.P[DEMON_PRG + 16 * i: DEMON_PRG + 16 * i + 16]

    def race_of(self, i):
        r = 0
        for k, s in enumerate(self.race_start):
            if s <= i:
                r = k + 1
            else:
                break
        return r if i > 0 else 0

    def resist(self, n):
        """상성 번호 n -> 11개 퍼센트(None = 흡수)"""
        b = self.P[RESIST_PRG + 6 * n: RESIST_PRG + 6 * n + 6]
        nib = []
        for x in b:
            nib += [x >> 4, x & 15]
        return [NIB[v] for v in nib[:11]]

    def skill_name(self, s):
        if s <= 0x3E:
            return self.spells.get(s, "마법 %02X" % s)
        for a, b, n in SPECIAL:
            if a <= s <= b:
                return n
        return "특수 공격"

    def info(self, i):
        r = self.record(i)
        race = self.race_of(i)
        skills = []
        for s in r[9:12]:
            if s != 0xFF:
                n = self.skill_name(s)
                if n not in skills:
                    skills.append(n)
        drop = None
        if r[14] >> 5:
            low = r[14] & 0x1F
            drop = ("메탈 카드" if low == 0x1E else self.items.get(low + 17, "아이템 %d" % (low + 17)), r[14] >> 5)
        return {
            "id": i, "name": self.names.get(i, "악마 %d" % i), "race": self.races.get(race, ""),
            "align": ALIGN.get(race, ""), "lv": r[0], "vit": r[1], "int": r[2], "str": r[3], "spd": r[4],
            "luck": r[5], "def": r[6], "skills": skills, "resist_no": r[13] + 1, "resist": self.resist(r[13]),
            "drop": drop, "antibody": r[15],
        }


def pct(v):
    if v is None:
        return "흡수"
    return ("%g" % v) + "%"


def main():
    args = sys.argv[1:]
    rom = args.pop(0) if args and args[0].lower().endswith(".nes") else None
    if rom is None:
        sys.path.insert(0, HERE)
        from mt2_map_window import DEFAULT_ROM
        rom = DEFAULT_ROM
    db = DemonDB(rom)
    if args and args[0] == "--check":
        # 공략집(dds.opatil.com) 값으로 손으로 확인한 표본
        want = {141: ("픽시", "요정", 2, (5, 6, 5, 5, 5, 3), ["하피루마", "도망"], 22),
                127: ("그린 슬라임", "외도", 1, (5, 5, 5, 5, 5, 1), ["지키기"], 20),
                102: ("구울", None, None, None, None, None),
                52: ("레오나르드", None, 30, None, None, None),
                70: (None, None, None, None, ["화염"], None),
                66: (None, None, None, None, ["냉기"], None)}
        bad = 0
        for i, (nm, race, lv, st, sk, rn) in want.items():
            f = db.info(i)
            got = (f["name"], f["race"], f["lv"], (f["vit"], f["int"], f["str"], f["spd"], f["luck"], f["def"]),
                   f["skills"], f["resist_no"])
            exp = (nm, race, lv, st, sk, rn)
            for g, e in zip(got, exp):
                if e is not None and g != e:
                    bad += 1
                    print("★%d %s: %r != %r" % (i, f["name"], g, e))
        r3 = db.resist(2)       # 공략집 No.3 邪神系 37.5 100 50 50 100 100 50 0 0 0 0
        if r3 != [37.5, 100, 50, 50, 100, 100, 50, 0, 0, 0, 0]:
            bad += 1
            print("★상성 3:", r3)
        if db.race_start[:4] != [1, 2, 12, 24]:
            bad += 1
            print("★종족 표:", db.race_start[:4])
        print("악마 정보 확인 %s (상성 %d종)" % ("✔" if not bad else "★%d건 다름" % bad, db.nresist))
        sys.exit(1 if bad else 0)
    for a in args:
        f = db.info(int(a, 0))
        print("%(id)3d %(name)s  %(race)s %(align)s  Lv%(lv)d  체%(vit)d 지%(int)d 힘%(str)d 속%(spd)d 운%(luck)d 방%(def)d"
              "  항체%(antibody)d" % f)
        print("     특수: %s   드롭: %s" % (" · ".join(f["skills"]) or "-", "%s(등급 %d)" % f["drop"] if f["drop"] else "-"))
        print("     상성 %d: %s" % (f["resist_no"], "  ".join("%s %s" % (a_, pct(v)) for a_, v in zip(ATTRS, f["resist"]))))


if __name__ == "__main__":
    main()

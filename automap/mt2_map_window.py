#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""여신전생 2 — 별도 창 자동지도.

Mesen 에서 mt2_bridge.lua 를 실행해 두면 이 창이 붙어서 지금 있는 곳의 지도를 크게 그린다.
게임 화면에는 아무것도 겹치지 않는다(화면 겹침판은 mt2_automap.lua).

  던전   지금 층(벽을 따라 이어진 칸)을 크게. 벽·문·계단·엘리베이터·상자·함정·회전·데미지 바닥,
         대화·간판·상점·회복 등 이벤트 표식, 한글 장소 이름(공략집 대조로 붙인 것)
  필드   내 주변 40x32칸. 원판 롬이 있으면 실제 게임 그래픽, 없으면 칸 색. 이벤트 칸·건물 입구와
         입구 이름(그 입구가 들어가는 던전 이름)
  전투   지도 대신 적 정보: 악마 종류별 이름·종족·Lv·마리별 HP·능력치·특수기·드롭·상성 11칸
         (2026-10-02 추가. 값은 롬에서 mt2_demon_info.py 가 푼다)
  V 키   밟은 곳만 <-> 전체  (창 윗줄 「보기」 글자를 눌러도 된다)

    python mt2_map_window.py [롬]                                   # 창 띄우기
    python mt2_map_window.py [롬] --snapshot a.png --state d,6,4,0    # 창 없이 그림만 (던전 x,y,방향)
    python mt2_map_window.py [롬] --snapshot b.png --state f,89,216,2,4  # 필드 x,y,방향,지역종류
        --visited 를 붙이면 밟은 곳만 보기로 그린다

롬은 원판·한글판 아무거나 된다(지도 데이터는 같다). 필드의 실제 그래픽은 원판 롬의 CHR 이 필요해서
한글판을 줄 때는 --jp-rom 으로 원판을 알려 주거나, 작업폴더 롬파일/ 에 원판이 있으면 저절로 찾는다.
지나간 곳은 %TEMP%\\mt2_automap_seen.txt 에 화면 겹침판과 같이 쓴다(창이 켜져 있을 때만 기록).
★Mesen 이 일시정지면 위치가 안 온다 — 창에 「멈춤」으로 표시한다.
★tkinter 는 파이썬 기본 포함. 실제 그래픽과 그림 뽑기는 Pillow 를 쓴다(없으면 칸 색으로 그린다).
"""
import argparse
import json
import os
import queue
import re
import socket
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 9877
SEEN_FILE = os.path.join(os.environ.get("TEMP", HERE), "mt2_automap_seen.txt")


def _find_rom(pattern, folder):
    d = os.path.join(ROOT, folder)
    if not os.path.isdir(d):
        return None
    c = [f for f in os.listdir(d) if re.search(pattern, f) and f.endswith(".nes")]
    if not c:
        return None
    return os.path.join(d, max(c, key=lambda f: os.path.getmtime(os.path.join(d, f))))


DEFAULT_ROM = _find_rom(r"^mt2_c\d+", "작업한 롬파일") or _find_rom(r"\(J\)", "롬파일")
DEFAULT_JP = _find_rom(r"Megami Tensei 2 \(J\)", "롬파일")

# ═════════════════════════════════════════════════════════════════════════════
# 1. 지도 데이터 (롬 + mt2_map_data.json)
# ═════════════════════════════════════════════════════════════════════════════
DW, DH = 128, 56          # 던전 지도 (128x64 중 위 56줄)
FW, FH = 128, 232         # 필드 지도
DXY = ((0, -1), (1, 0), (0, 1), (-1, 0))   # 0북 1동 2남 3서


def field_kind(x, y):
    """필드 칸이 어느 지역 그림(타일셋)을 쓰는지. 던전 출구 표로 정한 지역 경계(world_compose.py 와 같음)."""
    if y >= 156: return 4
    if x < 80 and y < 76: return 1
    if x < 80: return 0
    if y < 124 and not (84 <= x < 104 and 76 <= y < 140): return 2
    return 5


class MapData:
    def __init__(self, rom_path, jp_path=None):
        d = open(rom_path, "rb").read()
        if d[:4] != b"NES\x1a":
            raise ValueError("NES 롬이 아니다: %s" % rom_path)
        prg_size = d[4] * 16384
        prg = d[16:16 + prg_size]
        self.off = 0x40000 if prg_size >= 0x80000 else 0      # 한글판: 원판 PRG 가 뒤쪽 절반
        self.P = prg[self.off:self.off + 0x40000]
        P = self.P
        self.wall = [P[y * 256 + 2 * x] for y in range(DH) for x in range(DW)]
        self.flag = [P[y * 256 + 2 * x + 1] for y in range(DH) for x in range(DW)]
        self.blk = P[0x2D886:0x2D886 + 128]
        self.comp_of, self.comp_info = {}, []
        # 필드: 청크 맵 $8EF8(64/줄) -> 청크 표($8004 타일셋 0·1 / $8404 그 밖) -> 칸 번호
        self.fmeta = {}
        for sel in (0, 1):
            ctab = P[0x8000 + sel * 2] | P[0x8001 + sel * 2] << 8
            self.fmeta[sel] = [P[ctab + P[0x8EF8 + (y >> 1) * 64 + (x >> 1)] * 4 + (y & 1) * 2 + (x & 1)]
                               for y in range(FH) for x in range(FW)]
        # 전투 중 악마 정보 (롬에서 푼다 - mt2_demon_info.py). 못 읽어도 지도는 그대로 돈다.
        try:
            sys.path.insert(0, HERE)
            from mt2_demon_info import DemonDB
            self.db = DemonDB(rom_path)
        except Exception as e:                             # 번역표가 없는 배포본 등
            print("악마 정보를 못 읽었다:", e)
            self.db = None
        data = json.load(open(os.path.join(HERE, "mt2_map_data.json"), encoding="utf-8"))
        self.dev = {(o["x"], o["y"]): o["kind"] for o in data["dungeon_events"]}
        self.fev = {(o["x"], o["y"]): o["kind"] for o in data["field_events"]}
        self.fent = {(o["x"], o["y"]): o["name"] for o in data["field_entrances"]}
        self.names = data["names"]
        self.fcolors = {int(k): ["#%06x" % c for c in v] for k, v in data["field_colors"].items()}
        # 실제 그래픽용 원판 CHR (원판 롬이면 그 안에, 한글판이면 따로 준 원판에서)
        self.jp = None
        for cand in (rom_path, jp_path):
            if cand and os.path.exists(cand):
                r = open(cand, "rb").read()
                if r[:4] == b"NES\x1a" and r[5] > 0 and r[4] * 16384 == 0x40000:
                    self.jp = r
                    break
        self._mt_cache = {}

    # ── 던전 ────────────────────────────────────────────────────────────────
    def side(self, x, y, d):
        """d=0북 1동 2남 3서 -> 0 뚫림 / 1 벽 / 2 문"""
        return (self.wall[y * DW + x] >> (6 - 2 * d)) & 3

    def block(self, x, y):
        return self.blk[(y // 8) * 16 + x // 8]

    def component(self, sx, sy):
        """지금 칸에서 벽을 따라 걸어서 닿는 칸들(같은 층 블록 안). mt2_automap.lua 와 같은 규칙."""
        si = sy * DW + sx
        if si in self.comp_of:
            return self.comp_info[self.comp_of[si]]
        cid, v = len(self.comp_info), self.block(sx, sy)
        cells, stack = set(), [si]
        self.comp_of[si] = cid
        while stack:
            i = stack.pop()
            cells.add(i)
            x, y = i % DW, i // DW
            for d, (dx, dy) in enumerate(DXY):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < DW and 0 <= ny < DH):
                    continue
                j = ny * DW + nx
                if j in self.comp_of or self.block(nx, ny) != v or (self.flag[j] & 0xC0) == 0xC0:
                    continue
                if self.side(x, y, d) == 1 or self.side(nx, ny, (d + 2) % 4) == 1:
                    continue
                self.comp_of[j] = cid
                stack.append(j)
        xs, ys = [i % DW for i in cells], [i // DW for i in cells]
        info = {"cells": cells, "x0": min(xs), "y0": min(ys),
                "w": max(xs) - min(xs) + 1, "h": max(ys) - min(ys) + 1, "v": v}
        self.comp_info.append(info)
        return info

    def place_name(self, x, y, comp):
        for r in self.names:                       # 내 칸을 품은 이름 칸
            if r["x"] <= x < r["x"] + r["w"] and r["y"] <= y < r["y"] + r["h"]:
                return r["name"]
        best, score = None, 0
        for r in self.names:                       # 아니면 이 층과 가장 많이 겹치는 이름 칸
            n = sum(1 for yy in range(r["y"], r["y"] + r["h"]) for xx in range(r["x"], r["x"] + r["w"])
                    if yy * DW + xx in comp["cells"])
            if n > score:
                best, score = r["name"], n
        return best

    def dungeon_mark(self, x, y):
        f = self.flag[y * DW + x]
        if (f & 0xC0) == 0x80: return "up"
        if (f & 0xC0) == 0x40: return "down"
        ev = self.dev.get((x, y))
        if ev in STYLE: return ev
        if f & 0x10: return "chest"
        return {2: "turn", 3: "dmg", 4: "pit", 5: "exit"}.get(f & 0x0F)

    # ── 필드 ────────────────────────────────────────────────────────────────
    def fmeta_at(self, x, y, ts):
        return self.fmeta[0 if ts < 2 else 1][y * FW + x]

    def metatile_img(self, ts, m):
        """원판 CHR 로 16x16 칸 그림 (field_rom.py 와 같은 계산, 하네다 화면 780/780 일치)."""
        key = (ts, m)
        if key in self._mt_cache:
            return self._mt_cache[key]
        from PIL import Image
        J, C = self.jp[16:16 + 0x40000], self.jp[16 + 0x40000:]
        fx = lambda a: J[0x3E000 + a - 0xE000]
        if ("ts", ts) not in self._mt_cache:
            banks = J[0x20265 + ts * 4:0x20269 + ts * 4]
            pat = b"".join(C[b * 1024:(b + 1) * 1024] for b in banks)
            pid = J[0x3D82F + 2 * ts + 1]
            p = 0xE850 + fx(0xE79E + pid * 2) * 4
            sub = [[fx(0xE9C8 + fx(p + k) * 3 + c) for c in range(3)] for k in range(4)]
            mtab = J[0x87EC + 2 * ts] | J[0x87ED + 2 * ts] << 8
            atab = 0x26000 + (J[0x27CB7 + 2 * ts] | J[0x27CB8 + 2 * ts] << 8) - 0xC000
            self._mt_cache[("ts", ts)] = (pat, sub, mtab, atab)
        pat, sub, mtab, atab = self._mt_cache[("ts", ts)]
        a = J[atab + m] & 3
        t = J[mtab + m * 4:mtab + m * 4 + 4]
        im = Image.new("RGB", (16, 16))
        px = im.load()
        for k in range(4):
            base = t[k] * 16
            for yy in range(8):
                lo, hi = pat[base + yy], pat[base + yy + 8]
                for xx in range(8):
                    c = ((lo >> (7 - xx)) & 1) | (((hi >> (7 - xx)) & 1) << 1)
                    px[(k & 1) * 8 + xx, (k >> 1) * 8 + yy] = NES[0x0F if c == 0 else sub[a][c - 1] & 0x3F]
        self._mt_cache[key] = im
        return im


NES = [(84, 84, 84), (0, 30, 116), (8, 16, 144), (48, 0, 136), (68, 0, 100), (92, 0, 48), (84, 4, 0), (60, 24, 0),
       (32, 42, 0), (8, 58, 0), (0, 64, 0), (0, 60, 0), (0, 50, 60), (0, 0, 0), (0, 0, 0), (0, 0, 0),
       (152, 150, 152), (8, 76, 196), (48, 50, 236), (92, 30, 228), (136, 20, 176), (160, 20, 100), (152, 34, 32),
       (120, 60, 0), (84, 90, 0), (40, 114, 0), (8, 124, 0), (0, 118, 40), (0, 102, 120), (0, 0, 0), (0, 0, 0), (0, 0, 0),
       (236, 238, 236), (76, 154, 236), (120, 124, 236), (176, 98, 236), (228, 84, 236), (236, 88, 180), (236, 106, 100),
       (212, 136, 32), (160, 170, 0), (116, 196, 0), (76, 208, 32), (56, 204, 108), (56, 180, 204), (60, 60, 60),
       (0, 0, 0), (0, 0, 0),
       (236, 238, 236), (168, 204, 236), (188, 188, 236), (212, 178, 236), (236, 174, 236), (236, 174, 212),
       (236, 180, 176), (228, 196, 144), (204, 210, 120), (180, 222, 120), (168, 226, 144), (152, 226, 180),
       (160, 214, 228), (160, 162, 160), (0, 0, 0), (0, 0, 0)]


class Seen:
    """지나간 곳. 화면 겹침판과 같은 파일·같은 열쇠(던전 y*128+x, 필드 y*256+x)."""

    def __init__(self, path=SEEN_FILE):
        self.path, self.d, self.f, self.dirty = path, set(), set(), False
        self._load(self.d, self.f)

    def _load(self, d, f):
        try:
            for line in open(self.path, encoding="ascii"):
                t, _, v = line.strip().partition(" ")
                if v.isdigit():
                    (d if t == "d" else f if t == "f" else set()).add(int(v))
        except OSError:
            pass

    def add_dungeon(self, x, y):
        k = y * DW + x
        if k not in self.d:
            self.d.add(k); self.dirty = True

    def add_field_view(self, x, y):
        for yy in range(y - 7, y + 8):              # 게임 화면에 보이는 범위 = 「본 곳」
            for xx in range(x - 8, x + 8):
                if 0 <= xx < FW and 0 <= yy < FH and yy * 256 + xx not in self.f:
                    self.f.add(yy * 256 + xx); self.dirty = True

    def save(self):
        if not self.dirty:
            return
        d, f = set(self.d), set(self.f)
        self._load(d, f)                            # 겹침판이 그사이 쓴 것도 합쳐서 쓴다
        try:
            with open(self.path, "w", encoding="ascii") as fp:
                fp.writelines("d %d\n" % k for k in sorted(d))
                fp.writelines("f %d\n" % k for k in sorted(f))
            self.dirty = False
        except OSError:
            pass


# ═════════════════════════════════════════════════════════════════════════════
# 2. 그리기 (창 tkinter / 그림 파일 Pillow 가 같은 코드를 쓴다)
# ═════════════════════════════════════════════════════════════════════════════
FONT = "Malgun Gothic"
BG, PANEL, EDGE, TXT, SUB = "#10141a", "#06080b", "#2c3440", "#e8ecf2", "#8a96a8"
C_FLOOR, C_DARK, C_LIM, C_WALL, C_DOOR, C_ME = "#26303c", "#3a1848", "#183020", "#e8e8f0", "#40b4ff", "#ff6040"
WIN_W, WIN_H = 680, 790
MAP_X, MAP_Y, MAP_W, MAP_H = 20, 92, 640, 512
FVW, FVH, FC = 40, 32, 16                       # 필드 보기 40x32칸, 칸당 16px

# 종류 -> (색, 모양)  mt2_automap.lua 의 STYLE 과 같은 색
STYLE = {
    "up": ("#ffe040", "up"), "down": ("#4070ff", "down"), "elevator": ("#40e080", "fill"),
    "chest": ("#ff9020", "box"), "pit": ("#e0e0e0", "ring"), "turn": ("#b070ff", "diamond"),
    # ★2026-10-02 사용자 「상점·회복의 샘·출입구 색이 비슷해 헷갈린다」(셋 다 하늘색 꽉 찬 네모였다) ->
    #   상점 = 금색 동그라미, 회복의 샘 = 초록 구급(동그라미+흰 십자), 출입구 = 하늘색 빈 네모(필드 입구와 같은 모양),
    #   카지노·투기장은 새 상점 금색과 겹치지 않게 자홍색으로.
    "dmg": ("#ff3030", "cross"), "exit": ("#40d0ff", "box"), "talk": ("#ff70d0", "dot"),
    "sign": ("#909090", "dot"), "event": ("#ffffff", "plus"), "special": ("#b070ff", "dot"),
    "computer": ("#00ffc0", "fill"), "door": ("#40d0ff", "dot"), "entrance": ("#40d0ff", "box"),
    "bar": ("#ff5080", "fill"), "cult": ("#80ff80", "fill"), "heal": ("#2ecc71", "medkit"),
    "casino": ("#e040ff", "fill"), "arena": ("#e040ff", "fill"), "statue": ("#c0c0c0", "odiamond"),
    "shop_weapon": ("#ffc040", "coin"), "shop_armor": ("#ffc040", "coin"), "shop_item": ("#ffc040", "coin"),
    "shop_jewel": ("#ffc040", "coin"), "locked": ("#906040", "cross"), "empty": ("#505050", "dot"),
    "checkman": ("#ffffff", "fill"),
}
LEGEND_D = [("up", "올라가는 계단"), ("down", "내려가는 계단"), ("elevator", "엘리베이터"), ("chest", "보물상자"),
            ("pit", "함정(구멍)"), ("turn", "회전 바닥"), ("dmg", "데미지 바닥"), ("exit", "출입구"),
            ("talk", "대화"), ("sign", "간판·안내"), ("event", "중요 이벤트"), ("special", "특수 이벤트"),
            ("shop_weapon", "상점"), ("heal", "회복의 샘"), ("bar", "바"), ("cult", "사교의 관"),
            ("casino", "카지노·투기장"), ("computer", "컴퓨터"), ("locked", "잠긴 곳")]
LEGEND_F = [("entrance", "건물·던전 입구"), ("checkman", "체크맨(기록·이동)"), ("heal", "회복의 샘"),
            ("cult", "사교의 관"), ("talk", "대화"), ("event", "중요 이벤트"), ("statue", "동상"),
            ("shop_weapon", "상점"), ("casino", "카지노·투기장"),
            ("bar", "바"), ("door", "문"), ("locked", "잠긴 곳"), ("chest", "보물")]


class TkPainter:
    def __init__(self, canvas):
        self.c, self.keep = canvas, []

    def clear(self, bg):
        self.c.delete("all")
        self.keep = []
        self.c.configure(bg=bg)

    def rect(self, x, y, w, h, fill=None, outline=None, width=1):
        self.c.create_rectangle(x, y, x + w, y + h, fill=fill or "", outline=outline or "",
                                width=width if outline else 0)

    def line(self, x1, y1, x2, y2, col, width=1):
        self.c.create_line(x1, y1, x2, y2, fill=col, width=width, capstyle="projecting")

    def oval(self, x, y, w, h, fill=None, outline=None, width=1):
        self.c.create_oval(x, y, x + w, y + h, fill=fill or "", outline=outline or "", width=width if outline else 0)

    def poly(self, pts, fill):
        self.c.create_polygon(*[v for p in pts for v in p], fill=fill, outline="")

    def text(self, x, y, s, col, px, anchor="nw", bold=False, tag=None):
        self.c.create_text(x, y, text=s, fill=col, anchor=anchor, tags=tag or (),
                           font=(FONT, -px, "bold" if bold else "normal"))

    def image(self, x, y, pil_img):
        from PIL import ImageTk
        ph = ImageTk.PhotoImage(pil_img)
        self.keep.append(ph)
        self.c.create_image(x, y, image=ph, anchor="nw")


class PilPainter:
    ANCHOR = {"nw": "lt", "ne": "rt", "w": "lm", "e": "rm", "center": "mm", "n": "mt", "s": "mb"}

    def __init__(self, w, h):
        from PIL import Image, ImageDraw
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w, h))
        self.d = ImageDraw.Draw(self.img)
        self.fonts = {}

    def _font(self, px, bold):
        from PIL import ImageFont
        key = (px, bold)
        if key not in self.fonts:
            path = r"C:\Windows\Fonts\malgunbd.ttf" if bold else r"C:\Windows\Fonts\malgun.ttf"
            try:
                self.fonts[key] = ImageFont.truetype(path, px)
            except OSError:
                self.fonts[key] = ImageFont.load_default()
        return self.fonts[key]

    def clear(self, bg):
        self.d.rectangle([0, 0, self.w, self.h], fill=bg)

    def rect(self, x, y, w, h, fill=None, outline=None, width=1):
        self.d.rectangle([x, y, x + w, y + h], fill=fill, outline=outline, width=width)

    def line(self, x1, y1, x2, y2, col, width=1):
        self.d.line([x1, y1, x2, y2], fill=col, width=width)

    def oval(self, x, y, w, h, fill=None, outline=None, width=1):
        self.d.ellipse([x, y, x + w, y + h], fill=fill, outline=outline, width=width)

    def poly(self, pts, fill):
        self.d.polygon([tuple(p) for p in pts], fill=fill)

    def text(self, x, y, s, col, px, anchor="nw", bold=False, tag=None):
        self.d.text((x, y), s, fill=col, font=self._font(px, bold), anchor=self.ANCHOR[anchor])

    def image(self, x, y, pil_img):
        self.img.paste(pil_img, (int(x), int(y)))


def draw_mark(p, kind, x, y, cell):
    col, shape = STYLE[kind]
    ins = max(2, int(cell * 0.2))
    s = cell - 2 * ins
    wd = max(1, cell // 12)
    cx, cy = x + cell / 2, y + cell / 2
    if shape == "fill":
        p.rect(x + ins, y + ins, s, s, fill=col)
    elif shape == "box":
        p.rect(x + ins, y + ins, s, s, outline=col, width=max(2, cell // 10))
    elif shape == "dot":
        r = max(2, cell * 0.17)
        p.oval(cx - r, cy - r, 2 * r, 2 * r, fill=col)
    elif shape == "ring":
        r = cell / 2 - ins
        p.oval(cx - r, cy - r, 2 * r, 2 * r, outline=col, width=max(2, cell // 10))
    elif shape == "coin":                             # 상점: 꽉 찬 동그라미
        r = cell / 2 - ins + 1
        p.oval(cx - r, cy - r, 2 * r, 2 * r, fill=col)
    elif shape == "medkit":                           # 회복의 샘: 동그라미 + 흰 십자
        r = cell / 2 - ins + 1
        p.oval(cx - r, cy - r, 2 * r, 2 * r, fill=col)
        a, w = r * 0.6, max(2, cell // 9)
        p.line(cx, cy - a, cx, cy + a, "#ffffff", w)
        p.line(cx - a, cy, cx + a, cy, "#ffffff", w)
    elif shape == "plus":
        p.line(cx, y + ins, cx, y + cell - ins, col, max(2, cell // 8))
        p.line(x + ins, cy, x + cell - ins, cy, col, max(2, cell // 8))
    elif shape == "cross":
        p.line(x + ins, y + ins, x + cell - ins, y + cell - ins, col, max(2, cell // 10))
        p.line(x + cell - ins, y + ins, x + ins, y + cell - ins, col, max(2, cell // 10))
    elif shape in ("up", "down"):
        if shape == "up":
            p.poly([(cx, y + ins), (x + cell - ins, y + cell - ins), (x + ins, y + cell - ins)], fill=col)
        else:
            p.poly([(x + ins, y + ins), (x + cell - ins, y + ins), (cx, y + cell - ins)], fill=col)
    elif shape in ("diamond", "odiamond"):
        r = cell / 2 - ins + 1
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        if shape == "diamond":
            p.poly(pts, fill=col)
        else:
            for a, b in zip(pts, pts[1:] + pts[:1]):
                p.line(a[0], a[1], b[0], b[1], col, max(2, wd))


def draw_player(p, x, y, cell, d):
    cx, cy = x + cell / 2, y + cell / 2
    r = max(4, cell * 0.38)
    p.oval(cx - r, cy - r, 2 * r, 2 * r, fill=C_ME)
    dx, dy = DXY[d & 3]
    t = r * 0.85
    tip = (cx + dx * t, cy + dy * t)
    base = (cx - dx * t * 0.5, cy - dy * t * 0.5)
    px, py = -dy * t * 0.7, dx * t * 0.7
    p.poly([tip, (base[0] + px, base[1] + py), (base[0] - px, base[1] - py)], fill="#ffffff")


def draw_dungeon(p, m, st, visited, seen):
    x, y, d = st["x"], st["y"], st["d"]
    comp = m.component(x, y)
    zw, zh = comp["w"], comp["h"]
    cell = max(6, min(MAP_W // zw, MAP_H // zh, 44))
    ox = MAP_X + (MAP_W - zw * cell) // 2
    oy = MAP_Y + (MAP_H - zh * cell) // 2
    show = [i for i in comp["cells"] if not visited or i in seen.d]
    for i in show:                                    # 바닥
        cx_, cy_ = i % DW, i // DW
        f = m.flag[i]
        bg = C_DARK if f & 0x20 else C_LIM if (f & 0x0F) == 1 else C_FLOOR
        p.rect(ox + (cx_ - comp["x0"]) * cell, oy + (cy_ - comp["y0"]) * cell, cell, cell, fill=bg)
    wd = max(2, cell // 11)
    for i in show:                                    # 벽·문
        cx_, cy_ = i % DW, i // DW
        X, Y = ox + (cx_ - comp["x0"]) * cell, oy + (cy_ - comp["y0"]) * cell
        for s, seg in ((0, (X, Y, X + cell, Y)), (1, (X + cell, Y, X + cell, Y + cell)),
                       (2, (X, Y + cell, X + cell, Y + cell)), (3, (X, Y, X, Y + cell))):
            v = m.side(cx_, cy_, s)
            if v:
                p.line(*seg, C_WALL if v == 1 else C_DOOR, wd)
    for i in show:                                    # 표식
        cx_, cy_ = i % DW, i // DW
        k = m.dungeon_mark(cx_, cy_)
        if k:
            draw_mark(p, k, ox + (cx_ - comp["x0"]) * cell, oy + (cy_ - comp["y0"]) * cell, cell)
    draw_player(p, ox + (x - comp["x0"]) * cell, oy + (y - comp["y0"]) * cell, cell, d)
    name = m.place_name(x, y, comp)
    v = comp["v"]
    title = name or "구역 %X · %d층" % (v >> 4, v & 15)
    return title, "던전 (%d, %d)  %s" % (x, y, "북동남서"[d & 3] + "쪽"), "층 %d×%d칸" % (zw, zh)


def draw_field(p, m, st, visited, seen):
    x, y, d, ts = st["x"], st["y"], st["d"], st["ts"]
    x0, y0 = x - FVW // 2, y - FVH // 2
    real = m.jp is not None
    if real:
        try:
            from PIL import Image
        except ImportError:
            real = False
    if real:
        img = Image.new("RGB", (FVW * FC, FVH * FC), PANEL)
    for j in range(FVH):
        yy = y0 + j
        run_start, run_col = 0, None
        for i in range(FVW + 1):
            col = None
            xx = x0 + i
            if i < FVW and 0 <= xx < FW and 0 <= yy < FH and (not visited or yy * 256 + xx in seen.f):
                k = field_kind(xx, yy)
                if k == 2 and ts == 3:
                    k = 3
                mt = m.fmeta_at(xx, yy, k)
                if real:
                    img.paste(m.metatile_img(k, mt), (i * FC, j * FC))
                else:
                    cols = m.fcolors.get(k, m.fcolors[4])
                    col = cols[mt] if mt < len(cols) else "#000000"
            if not real and col != run_col:           # 같은 색이 이어지면 한 번에 그린다
                if run_col:
                    p.rect(MAP_X + run_start * FC, MAP_Y + j * FC, (i - run_start) * FC - 1, FC - 1, fill=run_col)
                run_start, run_col = i, col
    if real:
        p.image(MAP_X, MAP_Y, img)
    labels = []
    for j in range(FVH):                              # 이벤트·입구 표식
        for i in range(FVW):
            xx, yy = x0 + i, y0 + j
            if visited and yy * 256 + xx not in seen.f:
                continue
            X, Y = MAP_X + i * FC, MAP_Y + j * FC
            k = m.fev.get((xx, yy))
            if (xx, yy) in m.fent and k is None:
                k = "entrance"
            if k in STYLE:
                p.rect(X, Y, FC - 1, FC - 1, outline="#000000", width=3)
                p.rect(X, Y, FC - 1, FC - 1, outline=STYLE[k][0], width=2)
                if STYLE[k][1] != "box":
                    draw_mark(p, k, X, Y, FC)
            nm = m.fent.get((xx, yy))
            if nm:
                labels.append((X + FC / 2, Y - 2, nm))
    for lx, ly, nm in labels:                         # 입구 이름 (어디로 들어가는지)
        w = 13 * len(nm) + 8
        lx = min(max(lx, MAP_X + w / 2), MAP_X + MAP_W - w / 2)
        p.rect(lx - w / 2, ly - 19, w, 18, fill="#000000", outline=STYLE["entrance"][0])
        p.text(lx, ly - 10, nm, TXT, 13, "center")
    draw_player(p, MAP_X + (x - x0) * FC - 4, MAP_Y + (y - y0) * FC - 4, FC + 8, d)
    area = {0: "도쿄 (바깥 세계)", 1: "마계", 2: "데빌 버스터", 3: "데빌 버스터", 4: "도쿄 마을", 5: "마계 마을"}
    return area.get(ts, "필드"), "필드 (%d, %d)  %s" % (x, y, "북동남서"[d & 3] + "쪽"), \
        "실제 그래픽" if real else "칸 색 (원판 롬이 있으면 실제 그래픽)"


ATTRS_SHORT = ("총", "검", "화염", "빙결", "전격", "파마", "충격", "속박", "주살", "신경", "정신")
AFF = {  # 상성 칸 색: (바탕, 글자)
    "weak": ("#b8322a", "#ffffff"), "normal": ("#26303c", "#c8d0dc"), "resist": ("#1f4e79", "#e0ecff"),
    "null": ("#3a3a3a", "#9a9a9a"), "reflect": ("#6c3483", "#ffffff"), "absorb": ("#1e8449", "#ffffff"),
}
AFF_LEGEND = [("weak", "약점 (100 초과)"), ("normal", "보통 (100)"), ("resist", "내성 (100 미만)"),
              ("null", "무효 (0)"), ("reflect", "반사 (음수)"), ("absorb", "흡수")]


def aff_kind(v):
    if v is None:
        return "absorb"
    if v < 0:
        return "reflect"
    if v == 0:
        return "null"
    return "weak" if v > 100 else "normal" if v == 100 else "resist"


def draw_battle(p, m, enemies):
    """전투 중: 적을 악마 종류별 카드로. enemies = [[번호, HP, 최대HP, MP, 최대MP], ...] (브리지 순서)"""
    groups = []
    for e in enemies:
        for g in groups:
            if g[0] == e[0]:
                g[1].append(e)
                break
        else:
            groups.append((e[0], [e]))
    if not groups:
        p.text(MAP_X + MAP_W / 2, MAP_Y + MAP_H / 2, "전투 중 (남은 적 없음)", SUB, 16, "center")
        return "전투", "적 0", ""
    n = len(groups)
    cols = 1 if n <= 3 else 2
    rows = (n + cols - 1) // cols
    gap = 8
    cw = (MAP_W - gap * (cols - 1)) // cols
    ch = min(166 if cols == 1 else 252, (MAP_H - gap * (rows - 1)) // rows)
    for k, (did, members) in enumerate(groups):
        x0 = MAP_X + (k % cols) * (cw + gap)
        y0 = MAP_Y + (k // cols) * (ch + gap)
        p.rect(x0, y0, cw, ch, fill="#141b24", outline=EDGE)
        f = m.db.info(did) if m.db else None
        name = f["name"] if f else "악마 %d" % did
        p.text(x0 + 10, y0 + 8, name + ("  ×%d" % len(members) if len(members) > 1 else ""), TXT, 19, "nw", bold=True)
        if f:
            p.text(x0 + cw - 10, y0 + 11, "Lv %d · %s · %s" % (f["lv"], f["race"] or "-", f["align"] or "-"),
                   "#ffd36a", 14, "ne")
        # 마리별 HP 막대
        by = y0 + 38
        bw = min(150, (cw - 20 - 6 * (len(members) - 1)) // len(members))
        for j, e in enumerate(members):
            bx = x0 + 10 + j * (bw + 6)
            hp, mx = e[1], max(1, e[2])
            r = max(0.0, min(1.0, hp / mx))
            col = "#4ade80" if r > 0.5 else "#f0c040" if r > 0.25 else "#ef5350"
            p.rect(bx, by, bw, 16, fill="#0a0e13", outline="#3a4656")
            if hp > 0:
                p.rect(bx + 1, by + 1, max(1, int((bw - 2) * r)), 14, fill=col)
            p.text(bx + bw / 2, by + 8, "%d/%d" % (hp, e[2]), "#ffffff", 11, "center", bold=True)
        if f:
            mp = members[0]
            stats = "체 %d  지 %d  힘 %d  속 %d  운 %d  방 %d" % (f["vit"], f["int"], f["str"], f["spd"], f["luck"], f["def"])
            mpt = "MP %d/%d  항체 %d" % (mp[3], mp[4], f["antibody"])
            skills = "특수  " + (" · ".join(f["skills"]) or "-")
            drop = "드롭  %s (등급 %d)" % f["drop"] if f["drop"] else "드롭  -"
            if cols == 1:                             # 넓은 카드: 두 줄에 왼쪽·오른쪽으로
                p.text(x0 + 10, y0 + 62, stats, TXT, 13, "nw")
                p.text(x0 + cw - 10, y0 + 62, mpt, SUB, 12, "ne")
                p.text(x0 + 10, y0 + 84, skills, "#ffb0e0", 13, "nw")
                p.text(x0 + cw - 10, y0 + 84, drop, SUB, 12, "ne")
                cy = y0 + 108
            elif ch >= 230:                           # 좁은 카드(종류 4개 이상): 한 줄에 하나씩
                p.text(x0 + 10, y0 + 62, stats, TXT, 13, "nw")
                p.text(x0 + 10, y0 + 82, mpt, SUB, 12, "nw")
                p.text(x0 + 10, y0 + 102, skills, "#ffb0e0", 13, "nw")
                p.text(x0 + 10, y0 + 122, drop, SUB, 12, "nw")
                cy = y0 + 146
            elif ch >= 150:                           # 종류 5~6개: 능력치·특수만
                p.text(x0 + 10, y0 + 60, stats, TXT, 12, "nw")
                p.text(x0 + 10, y0 + 78, skills, "#ffb0e0", 12, "nw")
                cy = y0 + 100
            else:                                     # 종류 7~8개: 상성만
                cy = y0 + 60
            # 상성 11칸
            chh = min(48, y0 + ch - 8 - cy)
            cwid = (cw - 20 - 2 * 10) / 11
            for a, (lab, v) in enumerate(zip(ATTRS_SHORT, f["resist"])):
                cx_ = x0 + 10 + a * (cwid + 2)
                bg, fg = AFF[aff_kind(v)]
                p.rect(cx_, cy, cwid, chh, fill=bg)
                p.text(cx_ + cwid / 2, cy + chh * 0.3, lab, fg, 11, "center")
                p.text(cx_ + cwid / 2, cy + chh * 0.72, "흡수" if v is None else "%g" % v, fg, 12, "center", bold=True)
    total = sum(len(g[1]) for g in groups)
    return "전투", "적 %d마리 · %d종" % (total, n), "숫자 = 그 공격이 들어가는 비율(%)"


def render(p, m, st, status, visited, seen):
    p.clear(BG)
    p.text(MAP_X, 12, "여신전생2 자동지도", SUB, 14, "nw")
    status_txt = {"live": ("● Mesen 연결됨", "#4ade80"),
                  "stale": ("● Mesen 멈춤 — 일시정지 중이면 풀어 주세요", "#f0a63c"),
                  "wait": ("○ Mesen 연결 대기 중 — Script Window 에서 mt2_bridge.lua 실행", "#8fb0c6")}[status]
    p.text(MAP_X, 36, status_txt[0], status_txt[1], 12, "nw")
    p.text(MAP_X, 60, "보기: %s   (V 키 또는 여기를 눌러 바꾸기)" % ("밟은 곳만" if visited else "전체"),
           "#ffd36a" if visited else TXT, 13, "nw", tag="mode")
    if st is not None and "m" in st:                 # 소지금·MAG 상시 표시 (브리지 2026-10-02 판부터)
        p.text(WIN_W - MAP_X, 58, "마카 {:,}    MAG {:,}".format(st["m"], st.get("g", 0)), "#ffd36a", 16, "ne", bold=True)
    p.rect(MAP_X - 1, MAP_Y - 1, MAP_W + 2, MAP_H + 2, fill=PANEL, outline=EDGE)

    legend = LEGEND_D
    if st is None:
        p.text(MAP_X + MAP_W / 2, MAP_Y + MAP_H / 2, "위치 정보를 기다리는 중", SUB, 16, "center")
    elif st.get("b") is not None:                     # 전투 중 -> 지도 대신 적 정보
        legend = None
        title, pos, extra = draw_battle(p, m, st["b"])
    elif st["f"]:
        legend = LEGEND_F
        title, pos, extra = draw_field(p, m, st, visited, seen)
    elif st["x"] < DW and st["y"] < DH:
        title, pos, extra = draw_dungeon(p, m, st, visited, seen)
    else:
        st = None
        p.text(MAP_X + MAP_W / 2, MAP_Y + MAP_H / 2, "지도 밖 (이벤트·이동 중)", SUB, 16, "center")
    if st is not None:
        p.text(WIN_W - MAP_X, 10, title, TXT, 24, "ne", bold=True)
        p.text(MAP_X, MAP_Y + MAP_H + 10, pos, TXT, 14, "nw")
        p.text(WIN_W - MAP_X, MAP_Y + MAP_H + 10, extra, SUB, 13, "ne")

    ly = MAP_Y + MAP_H + 44                           # 범례 (4열)
    if legend is None:                                # 전투: 상성 색 범례
        for n, (kind, label) in enumerate(AFF_LEGEND):
            cx_, cy_ = MAP_X + (n % 3) * 214, ly + (n // 3) * 28
            p.rect(cx_, cy_, 34, 20, fill=AFF[kind][0])
            p.text(cx_ + 42, cy_ + 10, label, TXT, 13, "w")
        p.text(MAP_X, ly + 66, "100 이 보통 · 클수록 더 아프다 · 보조 마법(속박·신경·정신 등)은 성공률 · "
               "반사는 우리가 받는 피해", SUB, 12, "nw")
        p.text(MAP_X, ly + 86, "롬의 악마 표·상성 표를 공략집(dds.opatil.com) 데이터와 대조해 푼 값", SUB, 12, "nw")
        return
    for n, (kind, label) in enumerate(legend):
        cx_, cy_ = MAP_X + (n % 4) * 160, ly + (n // 4) * 26
        p.rect(cx_, cy_, 20, 20, fill=C_FLOOR)
        draw_mark(p, kind, cx_, cy_, 20)
        p.text(cx_ + 27, cy_ + 10, label, TXT, 13, "w")
    if legend is LEGEND_D:
        n = len(legend)
        cx_, cy_ = MAP_X + (n % 4) * 160, ly + (n // 4) * 26 + 10
        p.line(cx_, cy_, cx_ + 20, cy_, C_WALL, 3)
        p.text(cx_ + 26, cy_, "벽", SUB, 12, "w")
        p.line(cx_ + 50, cy_, cx_ + 70, cy_, C_DOOR, 3)
        p.text(cx_ + 76, cy_, "문", SUB, 12, "w")
        p.rect(cx_ + 100, cy_ - 9, 18, 18, fill=C_DARK)
        p.text(cx_ + 124, cy_, "다크존", SUB, 12, "w")


# ═════════════════════════════════════════════════════════════════════════════
# 3. Mesen 연결과 창
# ═════════════════════════════════════════════════════════════════════════════
def net_loop(port, q, stop):
    """접속 -> 줄 단위 JSON 을 큐로. 끊기면 1초 뒤 다시 붙는다."""
    while not stop.is_set():
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1.0)
        except OSError:
            q.put(("link", False))
            time.sleep(1.0)
            continue
        q.put(("link", True))
        s.settimeout(1.0)
        buf = b""
        try:
            while not stop.is_set():
                try:
                    chunk = s.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        q.put(("state", json.loads(line)))
                    except ValueError:
                        pass
        except OSError:
            pass
        finally:
            s.close()
        q.put(("link", False))


def run_window(m, port, visited):
    import tkinter as tk
    root = tk.Tk()
    root.title("여신전생2 자동지도")
    root.configure(bg=BG)
    root.resizable(False, False)
    canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=BG, highlightthickness=0)
    canvas.pack()
    painter = TkPainter(canvas)
    seen = Seen()

    q, stop = queue.Queue(), threading.Event()
    threading.Thread(target=net_loop, args=(port, q, stop), daemon=True).start()
    st = {"link": False, "state": None, "rx": 0.0, "sig": None, "visited": visited, "saved": time.time()}

    def toggle(_=None):
        st["visited"] = not st["visited"]
        st["sig"] = None

    root.bind("<KeyPress-v>", toggle)
    root.bind("<KeyPress-V>", toggle)
    canvas.tag_bind("mode", "<Button-1>", toggle)

    def poll():
        while True:
            try:
                kind, val = q.get_nowait()
            except queue.Empty:
                break
            if kind == "link":
                st["link"] = val
            else:
                st["state"], st["rx"] = val, time.time()
                if val["f"]:
                    seen.add_field_view(val["x"], val["y"])
                elif val["x"] < DW and val["y"] < DH:
                    seen.add_dungeon(val["x"], val["y"])
        if not st["link"]:
            status = "wait"
        elif time.time() - st["rx"] > 2.5:            # 브리지는 60프레임마다 한 번은 보낸다
            status = "stale"
        else:
            status = "live"
        s = st["state"]
        key = None if s is None else (s["f"], s["x"], s["y"], s["d"], s["ts"], json.dumps(s.get("b")),
                                      s.get("m"), s.get("g"))
        sig = (status, key, st["visited"], len(seen.d) + len(seen.f) if st["visited"] else 0)
        if sig != st["sig"]:                          # 바뀔 때만 다시 그린다
            render(painter, m, s, status, st["visited"], seen)
            st["sig"] = sig
        if time.time() - st["saved"] > 5:
            seen.save()
            st["saved"] = time.time()
        root.after(33, poll)

    def on_close():
        stop.set()
        seen.save()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    poll()
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="여신전생 2 별도 창 자동지도")
    ap.add_argument("rom", nargs="?", default=DEFAULT_ROM, help="여신전생2 롬 (원판·한글판)")
    ap.add_argument("--jp-rom", default=DEFAULT_JP, help="필드 실제 그래픽용 원판 롬 (한글판을 줄 때)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--visited", action="store_true", help="밟은 곳만 보기로 시작")
    ap.add_argument("--snapshot", help="창 대신 이 PNG 로 한 장 그리고 끝낸다")
    ap.add_argument("--state", help="그림 뽑기용 위치: d,x,y[,방향] 또는 f,x,y[,방향,지역종류]")
    ap.add_argument("--status", default="live", choices=("live", "stale", "wait"))
    ap.add_argument("--battle", help="그림 뽑기용 전투: 번호:HP/최대[:MP/최대],... (예 102:15/15,102:9/15)")
    ap.add_argument("--cash", help="그림 뽑기용 소지금·MAG: 마카,MAG (예 18661,6379)")
    a = ap.parse_args()
    if not a.rom or not os.path.exists(a.rom):
        raise SystemExit("롬을 찾을 수 없다: %s\n-> python mt2_map_window.py <롬 경로>" % a.rom)
    m = MapData(a.rom, a.jp_rom)

    if a.snapshot:
        state = None
        if a.state:
            t = a.state.split(",")
            v = [int(n) for n in t[1:]] + [0, 0, 0]
            state = {"f": 1 if t[0] == "f" else 0, "x": v[0], "y": v[1], "d": v[2], "ts": v[3]}
        if a.battle:
            state = state or {"f": 0, "x": 0, "y": 0, "d": 0, "ts": 0}
            b = []
            for e in a.battle.split(","):
                q = e.split(":") + ["0/0"]
                hp, mx = (int(v) for v in q[1].split("/"))
                mp, mmp = (int(v) for v in q[2].split("/"))
                b.append([int(q[0], 0), hp, mx, mp, mmp])
            state["b"] = b
        if a.cash:
            state = state or {"f": 0, "x": 0, "y": 0, "d": 0, "ts": 0}
            state["m"], state["g"] = (int(v) for v in a.cash.split(","))
        p = PilPainter(WIN_W, WIN_H)
        render(p, m, state, a.status, a.visited, Seen())
        p.img.save(a.snapshot)
        print("그림:", a.snapshot)
        return
    run_window(m, a.port, a.visited)


if __name__ == "__main__":
    main()

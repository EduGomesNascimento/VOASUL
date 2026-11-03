#!/usr/bin/env python3
"""Desenha geometria.json + rotas.json num PNG (conferencia rapida, sem KiCad).
   python3 ver_rotas.py geometria.json rotas.json saida.png"""
import json
import math
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon

geo = json.load(open(sys.argv[1]))
rot = json.load(open(sys.argv[2])) if len(sys.argv) > 3 else {'trilhas': [], 'jumpers': [], 'falhas': []}
saida = sys.argv[-1]
cores = {}
pal = plt.get_cmap('tab20')


def cor(r):
    if r == 'GND':
        return '#555555'
    if r == 'VBAT':
        return '#d62728'
    if r not in cores:
        cores[r] = pal(len(cores) % 20)
    return cores[r]


fig, ax = plt.subplots(figsize=(12, 12))
ax.add_patch(Circle((0, 0), geo['raio'], fill=False, lw=1))
for t in geo.get('fixas', []) + rot['trilhas']:
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], lw=t['w'] * 72 / 25.4 * 12 / 105 * 1.9,
            color=cor(t['rede']), solid_capstyle='round', alpha=0.85)
for p in geo['pads']:
    c, s = math.cos(math.radians(p['rot'])), math.sin(math.radians(p['rot']))
    w, h = p['w'], p['h']
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    pts = [(p['x'] + x * c - y * s, p['y'] + x * s + y * c) for x, y in pts]
    ax.add_patch(Polygon(pts, closed=True, color=cor(p['rede']) if p['rede'] else '#bbbbbb', alpha=0.9))
    ax.text(p['x'], p['y'], p['num'], fontsize=4, ha='center', va='center', color='w')
refs = {}
for p in geo['pads']:
    refs.setdefault(p['ref'], []).append((p['x'], p['y']))
for r, pts in refs.items():
    x = sum(a for a, _ in pts) / len(pts)
    y = sum(b for _, b in pts) / len(pts)
    ax.text(x, y + 2.2, r, fontsize=7, ha='center', color='k', weight='bold')
for j in rot['jumpers']:
    ax.plot([j['x1'], j['x2']], [j['y1'], j['y2']], '--', color='m', lw=1.5)
    for x, y in ((j['x1'], j['y1']), (j['x2'], j['y2'])):
        ax.add_patch(Circle((x, y), 1.2, color='m'))
for k in geo['sem_cobre']:
    ax.add_patch(FancyBboxPatch((k['x'] - k['w'] / 2, k['y'] - k['h'] / 2), k['w'], k['h'],
                                boxstyle='square', fill=False, ec='orange', ls=':'))
ax.set_xlim(-50, 50)
ax.set_ylim(-50, 50)
ax.set_aspect('equal')
ax.set_title(f"{len(rot['trilhas'])} trilhas, {len(rot['jumpers'])} jumpers, falhas: {rot['falhas']}", fontsize=9)
fig.savefig(saida, dpi=110, bbox_inches='tight')

#!/usr/bin/env python3
"""
Roteador proprio para PLACA DE FACE UNICA com trilhas grossas.

  entrada: geometria.json (gerado por etapas.py exportar)
  saida:   rotas.json     (trilhas em B.Cu + jumpers por cima)

Como funciona
  * grade de 0,2 mm so na face de baixo (B.Cu);
  * cada rede tem largura propria (projeto.CLASSES) e folga FOLGA de qualquer
    cobre de outra rede; perto dos proprios pinos a trilha pode afinar ate
    LARG_PESCOCO (pino de passo 2,54 nao deixa passar 2,5 mm);
  * busca A* (8 direcoes) de cada pino ate a arvore ja ligada da rede;
  * se nao der, tenta de novo permitindo JUMPER: fio reto por cima da placa,
    entre dois furos, pago caro (vale 30 mm de trilha) -> o minimo de jumpers;
  * redes que falharem vao para o comeco da fila e tudo e refeito.
So usa numpy.
"""
import heapq
import json
import math
import sys
import time

import numpy as np

RES = 0.2
MARGEM = 0.15          # folga extra por causa da grade
CUSTO_JUMPER = 30.0    # mm equivalentes
JUMPER_COMPR = (5.0, 8.0, 11.0, 15.0, 20.0)
JUMPER_DIRS = 16


# ---------------------------------------------------------------- geometria
def dist_forma(X, Y, f):
    """distancia (mm) de cada ponto ate a forma f (0 dentro)"""
    t = f['tipo']
    if t == 'seg':                                   # capsula: segmento + meia largura
        x1, y1, x2, y2 = f['x1'], f['y1'], f['x2'], f['y2']
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            d = np.hypot(X - x1, Y - y1)
        else:
            u = np.clip(((X - x1) * dx + (Y - y1) * dy) / L2, 0, 1)
            d = np.hypot(X - (x1 + u * dx), Y - (y1 + u * dy))
        return np.maximum(d - f['w'] / 2, 0)
    # pad: centro, tamanho, rotacao
    c, s = math.cos(math.radians(-f['rot'])), math.sin(math.radians(-f['rot']))
    lx = (X - f['x']) * c - (Y - f['y']) * s
    ly = (X - f['x']) * s + (Y - f['y']) * c
    w, h = f['w'], f['h']
    if t == 'circ':
        return np.maximum(np.hypot(lx, ly) - w / 2, 0)
    if t == 'oval':
        if w >= h:
            r, L = h / 2, (w - h) / 2
            return np.maximum(np.hypot(np.maximum(np.abs(lx) - L, 0), ly) - r, 0)
        r, L = w / 2, (h - w) / 2
        return np.maximum(np.hypot(lx, np.maximum(np.abs(ly) - L, 0)) - r, 0)
    # retangulo (e roundrect)
    ex = np.maximum(np.abs(lx) - w / 2, 0)
    ey = np.maximum(np.abs(ly) - h / 2, 0)
    return np.hypot(ex, ey)


def raio_forma(f):
    if f['tipo'] == 'seg':
        return math.hypot(f['x2'] - f['x1'], f['y2'] - f['y1']) / 2 + f['w'] / 2
    return math.hypot(f['w'], f['h']) / 2


def centro_forma(f):
    if f['tipo'] == 'seg':
        return (f['x1'] + f['x2']) / 2, (f['y1'] + f['y2']) / 2
    return f['x'], f['y']


class Grade:
    def __init__(self, raio):
        self.raio = raio
        self.n = int(math.ceil(2 * (raio + 1) / RES)) + 1
        self.o = -(self.n - 1) * RES / 2
        v = self.o + np.arange(self.n) * RES
        self.X, self.Y = np.meshgrid(v, v)          # [linha=y, coluna=x]

    def ij(self, x, y):
        return int(round((y - self.o) / RES)), int(round((x - self.o) / RES))

    def xy(self, i, j):
        return self.o + j * RES, self.o + i * RES

    def janela(self, f, alcance):
        cx, cy = centro_forma(f)
        r = raio_forma(f) + alcance + RES
        i0, j0 = self.ij(cx - r, cy - r)
        i1, j1 = self.ij(cx + r, cy + r)
        i0, j0 = max(i0, 0), max(j0, 0)
        i1, j1 = min(i1 + 1, self.n), min(j1 + 1, self.n)
        return slice(i0, i1), slice(j0, j1)

    def marcar(self, mask, f, alcance):
        """mask |= (distancia ate f <= alcance)"""
        si, sj = self.janela(f, alcance)
        if si.start >= si.stop or sj.start >= sj.stop:
            return
        d = dist_forma(self.X[si, sj], self.Y[si, sj], f)
        mask[si, sj] |= d <= alcance


# ---------------------------------------------------------------- roteador
class Roteador:
    def __init__(self, geo):
        self.geo = geo
        self.g = Grade(geo['raio'])
        self.folga = geo['folga'] + MARGEM
        self.pescoco = geo['pescoco']
        self.larg = geo['larguras']                 # rede -> largura
        self.pads = geo['pads']                     # todos (com rede ou nao)
        n = self.g.n
        X, Y = self.g.X, self.g.Y
        r = np.hypot(X, Y)
        self.borda = r                              # distancia ao centro
        self.proibido = np.zeros((n, n), bool)      # area sem cobre (antena)
        for k in geo['sem_cobre']:
            f = dict(k, tipo='ret', rot=0)
            self.g.marcar(self.proibido, f, 0.0)
        self.sem_jumper = np.zeros((n, n), bool)    # corpo encostado na placa
        for k in geo['sem_jumper']:
            f = dict(k, tipo='ret', rot=k.get('rot', 0))
            self.g.marcar(self.sem_jumper, f, 0.6)
        self.objs = []                               # cobre: (rede, forma)
        for p in self.pads:
            self.objs.append((p['rede'], p))
        self.jumpers = []                            # (rede, x1, y1, x2, y2)
        self.trilhas = []                            # (rede, x1, y1, x2, y2, w)

    # --- mascaras para a rede atual
    def mascaras(self, rede, w):
        g = self.g
        n = g.n
        larga = np.zeros((n, n), bool)
        fina = np.zeros((n, n), bool)
        furo_ok = np.zeros((n, n), bool)
        aw = w / 2 + self.folga
        an = self.pescoco / 2 + self.folga
        aj = self.geo['jumper_ilha'] / 2 + self.folga
        for (r, f) in self.objs:
            if r == rede:
                if f['tipo'] != 'seg':          # pino/ponta de jumper da propria rede: furo nao encosta em furo
                    g.marcar(furo_ok, f, self.geo['jumper_ilha'] / 2 + 0.5)
                continue
            g.marcar(larga, f, aw)
            g.marcar(fina, f, an)
            g.marcar(furo_ok, f, aj)
        # jumpers de outras redes: as ilhas sao cobre embaixo
        lim = self.g.raio - self.geo['folga_borda']
        larga |= self.borda > lim - w / 2
        fina |= self.borda > lim - self.pescoco / 2
        furo_ok |= self.borda > lim - self.geo['jumper_ilha'] / 2
        larga |= self.proibido_dil(aw - self.folga + RES)
        fina |= self.proibido_dil(an - self.folga + RES)
        furo_ok |= self.proibido_dil(aj - self.folga) | self.sem_jumper
        # perto dos pinos da propria rede pode afinar
        perto = np.zeros((n, n), bool)
        for p in self.pads:
            if p['rede'] == rede:
                g.marcar(perto, p, 3.0)
        livre = ~larga | (~fina & perto)
        # o fio do jumper (na placa profissional: trilha de cima de 0,8 mm) nao passa
        # por cima de ilha de outra rede
        self.pad_cima = np.zeros((n, n), bool)
        for p in self.pads:
            if p['rede'] != rede:
                g.marcar(self.pad_cima, p, 0.4 + self.folga)
        return livre, ~larga, ~fina, ~furo_ok

    def proibido_dil(self, a):
        if not self.proibido.any():
            return self.proibido
        m = np.zeros_like(self.proibido)
        for k in self.geo['sem_cobre']:
            self.g.marcar(m, dict(k, tipo='ret', rot=0), max(a, 0))
        return m

    # --- busca
    def astar(self, livre, origem, alvo, alvo_xy, furo, permitir_jumper, jumper_livre):
        n = self.g.n
        INF = 1e18
        custo = {}
        pai = {}
        heap = []
        ax, ay = alvo_xy
        o = self.g.o

        def h(i, j):
            return math.hypot(o + j * RES - ax, o + i * RES - ay) * 1.15

        for (i, j) in origem:
            k = i * n + j
            custo[k] = 0.0
            pai[k] = None
            heapq.heappush(heap, (h(i, j), 0.0, i, j))
        viz = [(-1, 0, RES), (1, 0, RES), (0, -1, RES), (0, 1, RES),
               (-1, -1, RES * 1.4142), (-1, 1, RES * 1.4142), (1, -1, RES * 1.4142), (1, 1, RES * 1.4142)]
        saltos = []
        if permitir_jumper:
            for a in range(JUMPER_DIRS):
                ang = 2 * math.pi * a / JUMPER_DIRS
                for L in JUMPER_COMPR:
                    di, dj = int(round(L * math.sin(ang) / RES)), int(round(L * math.cos(ang) / RES))
                    saltos.append((di, dj, math.hypot(di, dj) * RES))
        exp = 0
        while heap:
            f, c, i, j = heapq.heappop(heap)
            k = i * n + j
            if c > custo.get(k, INF) + 1e-9:
                continue
            if alvo[i, j]:
                caminho = []
                while k is not None:
                    caminho.append(k)
                    k = pai[k]
                return caminho[::-1], c
            exp += 1
            if exp > (700000 if permitir_jumper else 250000):
                return None, None
            for di, dj, dc in viz:
                ii, jj = i + di, j + dj
                if 0 <= ii < n and 0 <= jj < n and livre[ii, jj]:
                    nk = ii * n + jj
                    nc = c + dc
                    if nc < custo.get(nk, INF) - 1e-9:
                        custo[nk] = nc
                        pai[nk] = k
                        heapq.heappush(heap, (nc + h(ii, jj), nc, ii, jj))
            if permitir_jumper and furo[i, j]:
                for di, dj, L in saltos:
                    ii, jj = i + di, j + dj
                    if not (0 <= ii < n and 0 <= jj < n) or not furo[ii, jj]:
                        continue
                    if not jumper_livre(i, j, ii, jj):
                        continue
                    nk = ii * n + jj
                    nc = c + CUSTO_JUMPER + L
                    if nc < custo.get(nk, INF) - 1e-9:
                        custo[nk] = nc
                        pai[nk] = k
                        heapq.heappush(heap, (nc + h(ii, jj), nc, ii, jj))
        return None, None

    def jumper_livre_fn(self):
        """o fio do jumper nao pode cruzar outro jumper nem passar por cima de
        corpo encostado (eletrolitico, conector, resistor em pe)"""
        js = self.jumpers
        sem = self.sem_jumper | self.pad_cima | self.proibido_dil(0.4 + self.folga)
        o = self.g.o

        def ok(i, j, ii, jj):
            x1, y1 = o + j * RES, o + i * RES
            x2, y2 = o + jj * RES, o + ii * RES
            nst = max(abs(ii - i), abs(jj - j))
            for t in np.linspace(0.0, 1.0, max(nst, 3)):
                a, b = int(round(i + (ii - i) * t)), int(round(j + (jj - j) * t))
                if sem[a, b]:
                    return False
            for (_, a1, b1, a2, b2) in js:
                if seg_cruza(x1, y1, x2, y2, a1, b1, a2, b2, 2.8):
                    return False
            return True
        return ok

    # --- rede inteira
    def rotear_rede(self, rede, com_jumper, so_potencia=False):
        """liga os pinos da rede. GND tem duas fases:
          1) GND de POTENCIA (bateria, capacitor, fonte dos MOSFETs, entrada do MT3608 e um
             pino GND do ESP32): so cobre da placa -- a corrente dos motores passa aqui;
          2) o resto do GND (logica): pode chegar em QUALQUER pino de um grupo ligado por
             dentro do modulo (os 3 GND do ESP32, IN-/OUT- do MT3608)."""
        g = self.g
        w = self.larg.get(rede, self.geo['larg_padrao'])
        livre, ok_larga, ok_fina, furo = self.mascaras(rede, w)
        pads = [p for p in self.pads if p['rede'] == rede]
        nome = lambda p: p['ref'] + '.' + p['num']
        potencia = set(self.geo.get('gnd_potencia', [])) if rede == 'GND' else set()
        grupos = [set(gr) for gr in self.geo.get('grupos_internos', [])] if rede == 'GND' else []
        arvore = np.zeros((g.n, g.n), bool)
        for (r, f) in self.objs:
            if r == rede and f['tipo'] == 'seg':
                g.marcar(arvore, dict(f, w=0.0), RES * 0.8)
        faltam = list(range(len(pads)))
        ligados = set()
        if so_potencia:
            faltam = [k for k in faltam if nome(pads[k]) in potencia]
        # pino que ja encosta no cobre da rede (fase anterior) conta como ligado
        for k in list(faltam):
            m = np.zeros((g.n, g.n), bool)
            g.marcar(m, pads[k], 0.0)
            if (m & arvore).any():
                faltam.remove(k)
                ligados.add(nome(pads[k]))
        if ligados and not so_potencia:
            fase_potencia_feita = True
        if not arvore.any():
            base = [k for k in faltam if nome(pads[k]) in potencia] or faltam
            cx = np.mean([pads[k]['x'] for k in base]); cy = np.mean([pads[k]['y'] for k in base])
            k0 = min(base, key=lambda k: math.hypot(pads[k]['x'] - cx, pads[k]['y'] - cy))
            g.marcar(arvore, pads[k0], 0.0)
            faltam.remove(k0)
            ligados.add(nome(pads[k0]))
        novas, novos_j, falhas = [], [], []
        jl = self.jumper_livre_fn()
        fase_potencia = bool(potencia) and not (ligados & potencia == potencia & {nome(p) for p in pads})

        def atalho_grupos():
            # pino de grupo interno ligado -> o grupo todo esta ligado (por dentro do modulo)
            for gr in grupos:
                if gr & ligados:
                    for k in list(faltam):
                        if nome(pads[k]) in gr:
                            g.marcar(arvore, pads[k], 0.0)
                            faltam.remove(k)
                            ligados.add(nome(pads[k]))
        if not fase_potencia:
            atalho_grupos()
        while faltam:
            cand = faltam
            if fase_potencia:
                cand = [k for k in faltam if nome(pads[k]) in potencia]
                if not cand:
                    fase_potencia = False
                    atalho_grupos()
                    continue
            ai, aj_ = np.nonzero(arvore)
            axs, ays = g.o + aj_ * RES, g.o + ai * RES

            def dmin(k):
                return float(np.min(np.hypot(axs - pads[k]['x'], ays - pads[k]['y'])))
            k = min(cand, key=dmin)
            p = pads[k]
            alvo = np.zeros((g.n, g.n), bool)
            g.marcar(alvo, p, 0.0)
            alvo &= livre
            if not alvo.any():                       # pino menor que a grade
                i, j = g.ij(p['x'], p['y'])
                alvo[i, j] = True
                livre = livre.copy()
                livre[i, j] = True
            orig = list(zip(*np.nonzero(arvore & livre)))
            if not orig:
                orig = list(zip(*np.nonzero(arvore)))
            cam, c = self.astar(livre, orig, alvo, (p['x'], p['y']), furo, False, jl)
            if cam is None and com_jumper:
                cam, c = self.astar(livre, orig, alvo, (p['x'], p['y']), furo, True, jl)
            faltam.remove(k)
            if cam is None:
                falhas.append(nome(p))               # segue com os outros pinos
                continue
            segs, jumps = self.caminho_para_segmentos(cam, ok_larga, ok_fina, w)
            for s in segs:
                f = dict(tipo='seg', x1=s[0], y1=s[1], x2=s[2], y2=s[3], w=s[4])
                self.objs.append((rede, f))
                self.trilhas.append((rede,) + tuple(s))
                novas.append(s)
                g.marcar(arvore, dict(f, w=0.0), s[4] / 2 * 0.5)
            for jp in jumps:
                self.jumpers.append((rede,) + tuple(jp))
                ilha = self.geo['jumper_ilha']
                for (x, y) in ((jp[0], jp[1]), (jp[2], jp[3])):
                    f = dict(tipo='circ', x=x, y=y, w=ilha, h=ilha, rot=0)
                    self.objs.append((rede, f))
                    g.marcar(arvore, f, 0.0)
                novos_j.append(jp)
            g.marcar(arvore, p, 0.0)
            ligados.add(nome(p))
            if not fase_potencia:
                atalho_grupos()
        return (not falhas), novas, novos_j, falhas

    def caminho_para_segmentos(self, cam, ok_larga, ok_fina, w):
        """celulas -> segmentos retos (puxa o fio) + jumpers"""
        n = self.g.n
        pts = [(k // n, k % n) for k in cam]
        # quebra nos jumpers (passo maior que 1 celula)
        trechos, atual, jumps = [], [pts[0]], []
        for a, b in zip(pts, pts[1:]):
            if max(abs(a[0] - b[0]), abs(a[1] - b[1])) > 1:
                trechos.append(atual)
                xa, ya = self.g.xy(*a)
                xb, yb = self.g.xy(*b)
                jumps.append((xa, ya, xb, yb))
                atual = [b]
            else:
                atual.append(b)
        trechos.append(atual)
        segs = []
        for tr in trechos:
            # classe de cada celula: larga ou so fina
            cls = [bool(ok_larga[i, j]) for (i, j) in tr]
            k = 0
            while k < len(tr):
                m = k
                while m + 1 < len(tr) and cls[m + 1] == cls[k]:
                    m += 1
                larg = w if cls[k] else self.pescoco
                mask = ok_larga if cls[k] else ok_fina
                if k > 0:                           # emenda com o pedaco anterior: sempre fina
                    xa, ya = self.g.xy(*tr[k - 1])
                    xb, yb = self.g.xy(*tr[k])
                    segs.append((xa, ya, xb, yb, self.pescoco))
                bloco = tr[k:m + 1]
                for (a, b) in self.puxar(bloco, mask):
                    xa, ya = self.g.xy(*a)
                    xb, yb = self.g.xy(*b)
                    if (xa, ya) != (xb, yb):
                        segs.append((xa, ya, xb, yb, larg))
                k = m + 1
            if len(tr) == 1:
                x, y = self.g.xy(*tr[0])
                segs.append((x, y, x, y, w if cls[0] else self.pescoco))
        return segs, jumps

    def puxar(self, tr, mask):
        """menor numero de segmentos retos que continuam dentro de mask"""
        out = []
        a = 0
        while a < len(tr) - 1:
            b = len(tr) - 1
            while b > a + 1 and not linha_ok(tr[a], tr[b], mask):
                b -= 1
            out.append((tr[a], tr[b]))
            a = b
        return out


def linha_ok(a, b, mask):
    (i0, j0), (i1, j1) = a, b
    nst = max(abs(i1 - i0), abs(j1 - j0)) * 2
    if nst == 0:
        return True
    ii = np.rint(np.linspace(i0, i1, nst + 1)).astype(int)
    jj = np.rint(np.linspace(j0, j1, nst + 1)).astype(int)
    return bool(mask[ii, jj].all())


def seg_cruza(x1, y1, x2, y2, a1, b1, a2, b2, folga):
    """dois segmentos passam a menos de 'folga' um do outro?"""
    def dps(px, py, qx, qy, rx, ry):
        dx, dy = rx - qx, ry - qy
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((px - qx) * dx + (py - qy) * dy) / L2))
        return math.hypot(px - (qx + u * dx), py - (qy + u * dy))

    def ccw(ax, ay, bx, by, cx, cy):
        return (cy - ay) * (bx - ax) - (by - ay) * (cx - ax)
    d1 = ccw(x1, y1, x2, y2, a1, b1)
    d2 = ccw(x1, y1, x2, y2, a2, b2)
    d3 = ccw(a1, b1, a2, b2, x1, y1)
    d4 = ccw(a1, b1, a2, b2, x2, y2)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return True
    return min(dps(x1, y1, a1, b1, a2, b2), dps(x2, y2, a1, b1, a2, b2),
               dps(a1, b1, x1, y1, x2, y2), dps(a2, b2, x1, y1, x2, y2)) < folga


def rodar(geo, ordem, com_jumper=True):
    rt = Roteador(geo)
    for t in geo.get('fixas', []):                    # anel de VBAT
        f = dict(tipo='seg', **{k: t[k] for k in ('x1', 'y1', 'x2', 'y2', 'w')})
        rt.objs.append((t['rede'], f))
    falhas = []
    for rede in ordem:
        t0 = time.time()
        so_pot = rede.endswith(':potencia')
        ok, _, _, fal = rt.rotear_rede(rede.split(':')[0], com_jumper, so_potencia=so_pot)
        print(f'   {rede:10s} {"ok" if ok else "FALHOU " + str(fal)} ({time.time() - t0:.0f} s, jumpers ate agora: {len(rt.jumpers)})', flush=True)
        for f in fal:
            falhas.append((rede, f))
    return rt, falhas


def main():
    geo = json.load(open(sys.argv[1]))
    saida = sys.argv[2]
    ordem = geo['ordem']
    melhor = None
    n_tent = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    for tentativa in range(n_tent):
        t0 = time.time()
        rt, falhas = rodar(geo, ordem)
        nj = len(rt.jumpers)
        print(f'tentativa {tentativa + 1}: {len(falhas)} falhas, {nj} jumpers '
              f'({time.time() - t0:.0f} s) {falhas}', flush=True)
        nota = (len(falhas), nj)
        json.dump(dict(trilhas=[dict(rede=t[0], x1=t[1], y1=t[2], x2=t[3], y2=t[4], w=t[5]) for t in rt.trilhas],
                       jumpers=[dict(rede=j[0], x1=j[1], y1=j[2], x2=j[3], y2=j[4]) for j in rt.jumpers],
                       falhas=falhas, ordem=list(ordem)),
                  open(saida.replace('.json', f'_t{tentativa + 1}.json'), 'w'))
        if melhor is None or nota < melhor[0]:
            melhor = (nota, rt, falhas, list(ordem))
        if not falhas and nj == 0:
            break
        # quem falhou (ou ganhou jumper) vai para a frente da fila
        prior = [r for r, _ in falhas] + [j[0] for j in rt.jumpers]
        vistos = []
        for r in prior:
            if r not in vistos:
                vistos.append(r)
        if not vistos:
            break
        ordem = vistos + [r for r in ordem if r not in vistos]
        if tentativa >= 3 and not falhas:
            break
    (nf, nj), rt, falhas, ordem = melhor
    json.dump(dict(trilhas=[dict(rede=t[0], x1=t[1], y1=t[2], x2=t[3], y2=t[4], w=t[5])
                            for t in rt.trilhas],
                   jumpers=[dict(rede=j[0], x1=j[1], y1=j[2], x2=j[3], y2=j[4]) for j in rt.jumpers],
                   falhas=falhas, ordem=ordem),
              open(saida, 'w'), indent=1)
    print(f'MELHOR: {nf} falhas, {nj} jumpers -> {saida}')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Suaviza a curva de um .ses para o solver convergir, sem mudar o ensaio.

O problema tipico: a tabela vem do ensaio com passos de deformacao desiguais
(0,01 aqui, 0,09 ali) e a tensao arredondada em 2 casas. O modulo tangente de
cada trecho -- que e o que o solver usa para montar a rigidez -- vira um
serrilhado: 11, 28, 11, 5,8, 8,8, 7, 2, 6,6 MPa em pontos vizinhos. O Newton
sobe e desce a cada iteracao e a analise para antes do fim.

O ajuste tem tres partes:

1. **Ajuste suave.** Modela E(eps) = exp(g(eps)), linear por celula numa malha
   uniforme, e integra a partir da origem -- entao sigma(0)=0 e E>0 sao exatos
   por construcao. Ajusta g por Gauss-Newton minimizando o residuo ponderado
   contra os pontos do ensaio mais lambda vezes a curvatura de g. Penalizar a
   curvatura de log E, e nao a de sigma, e adimensional: pesa igual o ramo de
   compressao (E ~ 270 MPa) e o de tracao (E ~ 4 MPa).

2. **Reamostragem por variacao de modulo.** Escolhe as deformacoes de modo que
   log E ande um tanto fixo por segmento, limitado a [passo-min, passo-max].
   Da passo curto onde a curva encurva e passo longo onde ela e reta -- e o
   criterio que deixa o degrau de rigidez homogeneo, que e o que o solver
   sente. Amostrar uniforme em deformacao nao faz isso.

3. **Arredondamento dirigido.** Com 2 casas decimais, +-0,005 MPa num degrau de
   0,3 MPa ja move o modulo do trecho em 3%. Em vez de arredondar cada tensao
   isolada, uma programacao dinamica escolhe entre os tres valores possiveis
   (piso, arredondado, teto) a combinacao cujos modulos ficam mais perto dos da
   curva suave.

Uso:

    python3 suavizar_ses.py --entrada HN1008-17_150C_original.ses \
        --saida HN1008-17_150C.ses
"""

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csv_to_ses import fmt, montar_bloco, validar   # formato .ses ja validado


# --------------------------------------------------------------------------
# leitura
# --------------------------------------------------------------------------

def ler_ses(caminho):
    """Devolve (pontos, grupo, temperatura) de um .ses com um bloco de MPC."""
    bruto = open(caminho, newline="", encoding="utf-8", errors="replace").read()
    fisicas = [l for l in bruto.replace("\r\n", "\n").split("\n") if l]
    logicas, buf = [], ""
    for l in fisicas:
        if l.endswith("&"):
            buf += l[:-1]
        else:
            logicas.append(buf + l)
            buf = ""
    pts, grupo, temp = [], None, None
    for L in logicas:
        p = L.split(",")
        if p[0] != "MPC":
            sys.exit("ERRO: linha que nao comeca com MPC em %s" % caminho)
        if temp is None:
            grupo, temp = p[1], p[2]
        elif p[2] != temp:
            sys.exit("ERRO: %s tem mais de uma temperatura; separe antes de suavizar"
                     % caminho)
        v = [float(x) for x in p[4:]]
        pts += list(zip(v[0::2], v[1::2]))
    if len(pts) < 4:
        sys.exit("ERRO: menos de 4 pontos em %s" % caminho)
    return pts, grupo, temp


# --------------------------------------------------------------------------
# 1. ajuste suave  --  E(eps) = exp(g), sigma = integral de E a partir de 0
# --------------------------------------------------------------------------

def integra(g, h, k0):
    E = [math.exp(v) for v in g]
    C = [0.0] * len(g)
    for k in range(k0 + 1, len(g)):
        C[k] = C[k - 1] + h * (E[k - 1] + E[k]) / 2
    for k in range(k0 - 1, -1, -1):
        C[k] = C[k + 1] - h * (E[k] + E[k + 1]) / 2
    return C, E


def _celula(x, xs, h):
    k = int(math.floor((x - xs[0]) / h + 1e-9))
    k = max(0, min(len(xs) - 2, k))
    return k, (x - xs[k]) / h


def sigma_em(x, xs, h, C, E):
    """Tensao no ponto x: integral exata dentro da celula (E linear nela)."""
    k, s = _celula(x, xs, h)
    return C[k] + h * (E[k] * s + (E[k + 1] - E[k]) * s * s / 2)


def modulo_em(x, xs, h, E):
    k, s = _celula(x, xs, h)
    return E[k] + (E[k + 1] - E[k]) * s


def jacobiana(x, xs, h, E, k0):
    """d sigma(x) / d g_m, com g_m = log E_m."""
    n = len(E)
    J = [0.0] * n
    k, s = _celula(x, xs, h)
    passo = range(k0, k) if k >= k0 else range(k, k0)
    sinal = 1.0 if k >= k0 else -1.0
    for j in passo:
        J[j] += sinal * h / 2 * E[j]
        J[j + 1] += sinal * h / 2 * E[j + 1]
    J[k] += h * (E[k] * s - E[k] * s * s / 2)
    J[k + 1] += h * (E[k + 1] * s * s / 2)
    return J


def resolve(A, b):
    """Eliminacao de Gauss com pivotamento parcial; o sistema tem ~100 incognitas."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        if abs(M[c][c]) < 1e-14:
            M[c][c] = 1e-14
        for r in range(c + 1, n):
            f = M[r][c] / M[c][c]
            if f:
                for cc in range(c, n + 1):
                    M[r][cc] -= f * M[c][cc]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))) / M[r][r]
    return x


def ajustar(pts, h, lam, s0, peso_extremos=8.0, iteracoes=14):
    e0, e1 = pts[0][0], pts[-1][0]
    n_cel = int(round((e1 - e0) / h))
    xs = [e0 + i * h for i in range(n_cel + 1)]
    n = len(xs)
    k0 = int(round(-e0 / h))
    if not 0 < k0 < n - 1 or abs(xs[k0]) > 1e-9:
        sys.exit("ERRO: a malha precisa conter eps=0; ajuste --passo-malha")

    # peso relativo amortecido: sem isso o ramo de compressao, que tem tensao
    # dez vezes maior, domina o ajuste e o pe da curva fica solto.
    W = [1.0 / (abs(y) + s0) ** 2 for _, y in pts]
    W[0] *= peso_extremos
    W[-1] *= peso_extremos

    g = [math.log(max(1e-3, abs(pts[-1][1] / pts[-1][0])))] * n
    for _ in range(iteracoes):
        C, E = integra(g, h, k0)
        A = [[0.0] * n for _ in range(n)]
        b = [0.0] * n
        for (e, y), w in zip(pts, W):
            r = sigma_em(e, xs, h, C, E) - y
            J = jacobiana(e, xs, h, E, k0)
            nz = [m for m in range(n) if J[m]]
            for m in nz:
                b[m] -= w * J[m] * r
                for q in nz:
                    A[m][q] += w * J[m] * J[q]
        for k in range(1, n - 1):        # penaliza a segunda diferenca de g
            idx, coef = (k - 1, k, k + 1), (1.0, -2.0, 1.0)
            d = sum(c * g[i] for c, i in zip(coef, idx))
            for a, ia in zip(coef, idx):
                b[ia] -= lam * a * d
                for c, ic in zip(coef, idx):
                    A[ia][ic] += lam * a * c
        for m in range(n):
            A[m][m] += 1e-8              # regularizacao numerica
        dg = resolve(A, b)
        maior = max(abs(v) for v in dg)
        passo = min(1.0, 0.5 / maior) if maior else 1.0
        g = [gi + passo * d for gi, d in zip(g, dg)]
    C, E = integra(g, h, k0)
    return xs, C, E


# --------------------------------------------------------------------------
# 2. reamostragem: passo tal que log E ande `dlog` por segmento
# --------------------------------------------------------------------------

def escolher_deformacoes(xs, h, E, dlog, passo_min, passo_max, dec=2):
    e0, e1 = xs[0], xs[-1]
    eps, x = [e0], e0
    while x < e1 - 1e-9:
        lo, hi = passo_min, passo_max
        for _ in range(40):             # maior passo que respeita dlog
            m = (lo + hi) / 2
            if abs(math.log(modulo_em(min(x + m, e1), xs, h, E))
                   - math.log(modulo_em(x, xs, h, E))) > dlog:
                hi = m
            else:
                lo = m
        nx = round(x + max(passo_min, min(passo_max, round(lo, dec))), dec)
        if x < -1e-9 and nx > 1e-9:
            nx = 0.0                    # a origem e ponto obrigatorio da tabela
        if nx > e1 - 1e-9:
            nx = e1
        eps.append(round(nx, dec))
        x = nx
    if len(eps) > 2:                    # nao deixar um toco no fim
        if (eps[-1] - eps[-2]) < 0.6 * (eps[-2] - eps[-3]):
            del eps[-2]
    return eps


# --------------------------------------------------------------------------
# 3. arredondamento dirigido pelo modulo (programacao dinamica)
# --------------------------------------------------------------------------

def arredondar(eps, y_suave, extremos, dec=2, gap=0.1):
    """Escolhe as tensoes de 2 casas cujos modulos ficam mais perto dos suaves."""
    q = 10.0 ** -dec
    cand = []
    for i, y in enumerate(y_suave):
        if i in extremos:
            cand.append([round(extremos[i], dec)])
        else:
            base = round(y, dec)
            cand.append(sorted({round(base + k * q, dec) for k in (-1, 0, 1)}))
    alvo = [None] + [math.log((y_suave[i] - y_suave[i - 1]) / (eps[i] - eps[i - 1]))
                     for i in range(1, len(eps))]

    INF = float("inf")
    dp = [[0.0] * len(cand[0])]
    de = [[None] * len(cand[0])]
    for i in range(1, len(eps)):
        linha, volta = [], []
        for ci, s in enumerate(cand[i]):
            melhor, arg = INF, None
            for cj, sp in enumerate(cand[i - 1]):
                if dp[i - 1][cj] == INF or s - sp < gap - 1e-9:
                    continue
                custo = dp[i - 1][cj] + (math.log((s - sp) / (eps[i] - eps[i - 1]))
                                         - alvo[i]) ** 2
                if custo < melhor:
                    melhor, arg = custo, cj
            linha.append(melhor)
            volta.append(arg)
        if all(v == INF for v in linha):
            sys.exit("ERRO: degrau de tensao de %.2f MPa impossivel em eps=%.2f; "
                     "aumente --passo-max ou reduza --gap-stress" % (gap, eps[i]))
        dp.append(linha)
        de.append(volta)

    ci = min(range(len(cand[-1])), key=lambda c: dp[-1][c])
    escolha = [0] * len(eps)
    for i in range(len(eps) - 1, 0, -1):
        escolha[i] = ci
        ci = de[i][ci]
    escolha[0] = ci
    return [cand[i][c] for i, c in enumerate(escolha)]


# --------------------------------------------------------------------------
# relatorio
# --------------------------------------------------------------------------

def razoes(curva):
    E = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(curva, curva[1:])]
    return E, [b / a for a, b in zip(E, E[1:])]


def interp(curva, x):
    for a, b in zip(curva, curva[1:]):
        if a[0] - 1e-9 <= x <= b[0] + 1e-9:
            t = (x - a[0]) / (b[0] - a[0])
            return a[1] + t * (b[1] - a[1])
    return curva[0][1] if x < curva[0][0] else curva[-1][1]


def main():
    ap = argparse.ArgumentParser(
        description="Suaviza a curva de um .ses para a simulacao convergir.")
    ap.add_argument("--entrada", required=True, help=".ses do ensaio")
    ap.add_argument("--saida", required=True, help=".ses suavizado")
    ap.add_argument("--dlog", type=float, default=0.12,
                    help="variacao de log E por segmento (padrao 0.12 = ~12%%)")
    ap.add_argument("--passo-min", type=float, default=0.02,
                    help="menor passo de deformacao (padrao 0.02)")
    ap.add_argument("--passo-max", type=float, default=0.15,
                    help="maior passo de deformacao (padrao 0.15)")
    ap.add_argument("--lam", type=float, default=10.0,
                    help="peso da suavizacao de log E (padrao 10)")
    ap.add_argument("--s0", type=float, default=0.5,
                    help="amortecimento do peso relativo, em MPa (padrao 0.5)")
    ap.add_argument("--passo-malha", type=float, default=0.025,
                    help="passo da malha interna do ajuste (padrao 0.025)")
    ap.add_argument("--gap-stress", type=float, default=0.1,
                    help="degrau minimo de tensao entre pontos (padrao 0.1)")
    ap.add_argument("--largura", type=int, default=70,
                    help="caracteres de dado por linha, antes do & (padrao 70)")
    ap.add_argument("--decimais", type=int, default=2, help="casas decimais (padrao 2)")
    args = ap.parse_args()

    pts, grupo, temp = ler_ses(args.entrada)
    h = args.passo_malha
    xs, C, E = ajustar(pts, h, args.lam, args.s0)
    eps = escolher_deformacoes(xs, h, E, args.dlog, args.passo_min,
                               args.passo_max, args.decimais)
    y = [sigma_em(e, xs, h, C, E) for e in eps]
    extremos = {0: pts[0][1], len(eps) - 1: pts[-1][1]}   # extremos do ensaio intactos
    s = arredondar(eps, y, extremos, args.decimais, args.gap_stress)
    curva = list(zip(eps, s))

    linhas = montar_bloco(curva, grupo, temp, args.largura,
                          args.decimais, args.decimais)
    with open(args.saida, "w", newline="", encoding="utf-8") as f:
        f.write("\r\n".join(linhas) + "\r\n")

    E_ori, r_ori = razoes(pts)
    E_new, r_new = razoes(curva)
    print("  eps    sigma   d_eps   d_sig       E    E_i/E_i-1")
    for i, (e, sv) in enumerate(curva):
        if i == 0:
            print("%7.2f %8.2f" % (e, sv))
            continue
        print("%7.2f %8.2f %7.2f %7.2f %8.2f %9.3f"
              % (e, sv, e - curva[i - 1][0], sv - curva[i - 1][1], E_new[i - 1],
                 r_new[i - 2] if i > 1 else float("nan")))

    desv = [(e, interp(curva, e) - yy) for e, yy in pts]
    pior = max(desv, key=lambda d: abs(d[1]))
    print("\n%-28s %s -> %s" % ("pontos da tabela", len(pts), len(curva)))
    print("%-28s [%.2f .. %.2f] -> [%.2f .. %.2f]"
          % ("razao de modulo vizinha", min(r_ori), max(r_ori),
             min(r_new), max(r_new)))
    print("%-28s %.2f -> %.2f MPa"
          % ("menor degrau de tensao",
             min(b[1] - a[1] for a, b in zip(pts, pts[1:])),
             min(b[1] - a[1] for a, b in zip(curva, curva[1:]))))
    print("%-28s %.2f -> %.2f" % ("menor/maior modulo", min(E_new), max(E_new)))
    print("%-28s %.2f MPa em eps=%.2f" % ("maior desvio do ensaio", pior[1], pior[0]))
    print("%-28s %.2f MPa" % ("desvio medio absoluto",
                              sum(abs(d) for _, d in desv) / len(desv)))
    print()
    validar(args.saida, args.largura)
    json.dump([{"strain": e, "stress": sv} for e, sv in curva],
              open(os.path.splitext(args.saida)[0] + "_pontos.json", "w"), indent=1)


if __name__ == "__main__":
    main()

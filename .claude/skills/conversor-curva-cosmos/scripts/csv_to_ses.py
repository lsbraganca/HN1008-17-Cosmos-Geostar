#!/usr/bin/env python3
"""Converte CSVs de ensaio tensao-deformacao em arquivo .ses (registros MPC).

Uso tipico (dois ramos, 35 pontos em cada):

    python3 csv_to_ses.py --compressao comp.csv --tracao trac.csv \
        --temperatura 23 --pontos 35 --saida HN1008-17_23C.ses

Um ramo so, ou pontos no total em vez de por ramo:

    python3 csv_to_ses.py --csv trac.csv --temperatura 23 --pontos 40 --saida x.ses
    python3 csv_to_ses.py --compressao c.csv --tracao t.csv --pontos-total 35 ...

Conferir um .ses ja existente (formato + monotonicidade):

    python3 csv_to_ses.py --validar arquivo.ses
"""

import argparse
import csv
import json
import math
import os
import sys


# --------------------------------------------------------------------------
# leitura dos CSVs
# --------------------------------------------------------------------------

def ler_csv(caminho, escala):
    """Le pares (deformacao, tensao) ignorando cabecalhos e linhas nao numericas.

    `escala` divide a deformacao: 100 quando o CSV esta em % (o caso normal
    das maquinas de ensaio) ou 1 quando ja esta adimensional.
    """
    pts = []
    with open(caminho, newline="", encoding="utf-8-sig", errors="replace") as f:
        amostra = f.read(4096)
        f.seek(0)
        try:
            sep = csv.Sniffer().sniff(amostra, delimiters=",;\t").delimiter
        except csv.Error:
            sep = ","
        for linha in csv.reader(f, delimiter=sep):
            if len(linha) < 2:
                continue
            try:
                e = float(linha[0].strip().replace(",", "."))
                s = float(linha[1].strip().replace(",", "."))
            except ValueError:
                continue          # cabecalho, linha em branco, texto
            pts.append((e / escala, s))
    if not pts:
        sys.exit("ERRO: nenhum par numerico encontrado em %s" % caminho)
    return pts


def limpar_ramo(pts, sinal):
    """Mantem so o trecho de carregamento, com deformacao estritamente monotonica.

    Descarta o retorno/descarga do ensaio (deformacao que volta atras) porque a
    tabela do solver exige deformacao monotonica crescente. Tambem forca o ramo
    a comecar na origem, que e o ponto comum aos dois ensaios.
    """
    out = []
    for e, s in pts:
        if sinal * e < -1e-12:
            continue                       # ponto do lado errado do zero
        if not out:
            out.append((0.0, 0.0))         # origem: extremo comum aos dois ramos
            if abs(e) < 1e-12:
                continue
        if sinal * e <= sinal * out[-1][0] + 1e-12:
            continue                       # nao avancou: descarga ou repeticao
        out.append((e, s))
    if len(out) < 2:
        sys.exit("ERRO: ramo com menos de 2 pontos apos limpeza")
    return out


def detectar_ramo(pts):
    """+1 se o ensaio e de tracao, -1 se e de compressao."""
    return -1 if sum(1 for e, _ in pts if e < 0) > len(pts) / 2 else 1


# --------------------------------------------------------------------------
# selecao dos pontos
# --------------------------------------------------------------------------

def selecionar(pts, n):
    """Escolhe n pontos preservando o formato da curva.

    Comeca pelos dois extremos e vai inserindo, uma a uma, a amostra que mais
    se afasta da poligonal atual (distancia perpendicular em eixos
    normalizados). O efeito e concentrar pontos onde a curva encurva e espacar
    onde ela e reta -- que e exatamente "espacar os pontos mantendo a curva".
    """
    if n >= len(pts):
        return list(pts)
    if n < 2:
        sys.exit("ERRO: sao necessarios pelo menos 2 pontos por ramo")
    ex = max(abs(p[0]) for p in pts) or 1.0
    sy = max(abs(p[1]) for p in pts) or 1.0
    P = [(p[0] / ex, p[1] / sy) for p in pts]
    idx = [0, len(pts) - 1]
    while len(idx) < n:
        melhor_d, melhor_i = -1.0, None
        for a, b in zip(idx, idx[1:]):
            x1, y1 = P[a]
            x2, y2 = P[b]
            dx, dy = x2 - x1, y2 - y1
            L = math.hypot(dx, dy) or 1e-12
            for i in range(a + 1, b):
                x0, y0 = P[i]
                d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / L
                if d > melhor_d:
                    melhor_d, melhor_i = d, i
        if melhor_i is None:
            break
        idx.append(melhor_i)
        idx.sort()
    return [pts[i] for i in idx]


def erro_interpolacao(completo, escolhidos):
    """Maior desvio, em MPa e em % do pico, da curva reconstruida por retas."""
    sel = sorted(escolhidos)
    xs = [p[0] for p in sel]
    ys = [p[1] for p in sel]
    pico = max(abs(p[1]) for p in completo) or 1.0
    pior = 0.0
    for e, s in completo:
        for j in range(len(xs) - 1):
            if xs[j] <= e <= xs[j + 1]:
                span = xs[j + 1] - xs[j]
                t = (e - xs[j]) / span if span else 0.0
                pior = max(pior, abs(ys[j] + t * (ys[j + 1] - ys[j]) - s))
                break
    return pior, pior / pico * 100.0


# --------------------------------------------------------------------------
# escrita no formato MPC
# --------------------------------------------------------------------------

def aplicar_regras(sel, dec_e, dec_s, gap):
    """Arredonda os pontos e descarta os que o Cosmos nao digere.

    Duas regras do solver, e as duas sao eliminatorias:

    * no maximo 2 casas decimais -- e o que o arquivo modelo usa;
    * degrau minimo de tensao entre pontos consecutivos (`gap`, tipicamente
      0,1 MPa). Pontos praticamente empatados em tensao fazem o Cosmos se
      perder na interpolacao, entao e melhor um ponto a menos do que dois
      colados.

    A deformacao tambem precisa continuar estritamente crescente depois do
    arredondamento -- dois pontos no mesmo degrau invalidariam a tabela.
    """
    sel = sorted(sel)          # o ramo de compressao chega em ordem decrescente
    out = []
    for e, s_ in sel:
        er, sr = round(e, dec_e), round(s_, dec_s)
        if out:
            if er <= out[-1][0]:
                continue
            if abs(sr - out[-1][1]) < gap - 1e-9:
                continue
        out.append((er, sr))
    # o extremo da curva nao pode sumir: se caiu, troca pelo ultimo aceito
    ue, us = round(sel[-1][0], dec_e), round(sel[-1][1], dec_s)
    if out and out[-1][0] != ue:
        if len(out) > 1 and ue > out[-2][0] and abs(us - out[-2][1]) >= gap - 1e-9:
            out[-1] = (ue, us)
    return out


def selecionar_com_regras(pts, alvo, dec_e, dec_s, gap):
    """Escolhe pontos ate sobrarem `alvo` DEPOIS de aplicadas as regras.

    Arredondamento e degrau minimo derrubam parte do que foi escolhido, entao
    pede-se mais do que o alvo e repete-se ate fechar a conta.
    """
    pedido, melhor = alvo, []
    while pedido <= len(pts):
        final = aplicar_regras(selecionar(pts, pedido), dec_e, dec_s, gap)
        if len(final) > len(melhor):
            melhor = final
        if len(final) >= alvo:
            break
        pedido += max(1, alvo - len(final))
    if len(melhor) > alvo:
        reduzido = aplicar_regras(selecionar(melhor, alvo), dec_e, dec_s, gap)
        if len(reduzido) >= alvo - 1:
            melhor = reduzido
    return melhor


def fmt(v, dec):
    """Numero no estilo do arquivo modelo: -0.55 vira -.55, zeros a direita caem."""
    s = "%.*f" % (dec, v)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("", "-", "-0", "0"):
        return "0"
    if s.startswith("-0."):
        return "-" + s[2:]
    if s.startswith("0."):
        return s[1:]
    return s


def quebrar(linha, largura):
    """Corta a linha logica em pedacos de `largura` caracteres, com & de continuacao.

    O corte e por contagem de caracteres e nao por virgula: o formato aceita
    (e o arquivo modelo faz) partir um numero no meio, com o resto na linha
    seguinte.
    """
    saida = []
    while len(linha) > largura:
        saida.append(linha[:largura] + "&")
        linha = linha[largura:]
    saida.append(linha)
    return saida


def montar_bloco(curva, grupo, temperatura, largura, dec_strain, dec_stress):
    linhas = []
    for ini in range(0, len(curva), 10):
        vals = []
        for e, s in curva[ini:ini + 10]:
            vals.append(fmt(e, dec_strain))
            vals.append(fmt(s, dec_stress))
        cabecalho = "MPC,%s,%s,%d," % (grupo, temperatura, ini + 1)
        linhas.extend(quebrar(cabecalho + ",".join(vals), largura))
    return linhas


# --------------------------------------------------------------------------
# validacao
# --------------------------------------------------------------------------

def validar(caminho, largura=70):
    bruto = open(caminho, newline="", encoding="utf-8", errors="replace").read()
    problemas = []
    if "\r\n" not in bruto:
        problemas.append("arquivo nao usa terminadores CRLF")
    fisicas = [l for l in bruto.replace("\r\n", "\n").split("\n") if l]
    excesso = [i + 1 for i, l in enumerate(fisicas) if len(l) > largura + 1]
    if excesso:
        problemas.append("linhas acima de %d caracteres: %s" % (largura + 1, excesso))

    logicas, buf = [], ""
    for l in fisicas:
        if l.endswith("&"):
            buf += l[:-1]
        else:
            logicas.append(buf + l)
            buf = ""
    if buf:
        problemas.append("ultima linha termina em & sem continuacao")

    total, anterior, temp_atual, geral = 0, None, None, 0
    for L in logicas:
        p = L.split(",")
        if len(p) > 3 and p[2] != temp_atual:
            temp_atual, total, anterior = p[2], 0, None   # novo bloco de temperatura
        if p[0] != "MPC":
            problemas.append("linha nao comeca com MPC: %r" % L[:40])
            continue
        try:
            vals = [float(x) for x in p[4:]]
        except ValueError:
            problemas.append("valor nao numerico em %r" % L[:40])
            continue
        if len(vals) % 2:
            problemas.append("grupo %s tem numero impar de valores" % p[3])
        esperado = str(total + 1)
        if p[3] != esperado:
            problemas.append("grupo de linha %s deveria ser %s" % (p[3], esperado))
        for e in vals[0::2]:
            if anterior is not None and e <= anterior:
                problemas.append("deformacao nao crescente em %g (apos %g)" % (e, anterior))
            anterior = e
        total += len(vals) // 2
        geral += len(vals) // 2

    print("%s: %d registros MPC, %d pontos, maior linha %d caracteres"
          % (os.path.basename(caminho), len(logicas), geral,
             max((len(l) for l in fisicas), default=0)))
    for p in problemas:
        print("  PROBLEMA: %s" % p)
    if not problemas:
        print("  formato OK")
    return not problemas


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Converte CSVs de ensaio em arquivo .ses (registros MPC).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--compressao", help="CSV do ensaio de compressao")
    ap.add_argument("--tracao", help="CSV do ensaio de tracao")
    ap.add_argument("--csv", help="CSV unico; o ramo e detectado pelo sinal")
    ap.add_argument("--saida", help="arquivo .ses de saida")
    ap.add_argument("--temperatura", default="23", help="temperatura em C (padrao 23)")
    ap.add_argument("--grupo", default="1", help="grupo de elementos (padrao 1)")
    ap.add_argument("--pontos", type=int, default=35,
                    help="pontos POR RAMO, incluindo a origem (padrao 35)")
    ap.add_argument("--pontos-total", type=int,
                    help="em vez de por ramo, total na curva inteira")
    ap.add_argument("--strain-em", choices=["percent", "absoluto"], default="percent",
                    help="unidade da deformacao no CSV (padrao percent)")
    ap.add_argument("--largura", type=int, default=70,
                    help="caracteres de dado por linha, antes do & (padrao 70)")
    ap.add_argument("--decimais", type=int, default=2,
                    help="casas decimais; o Cosmos aceita no maximo 2 (padrao)")
    ap.add_argument("--gap-stress", type=float, default=0.1,
                    help="degrau minimo de tensao entre pontos (padrao 0.1)")
    ap.add_argument("--anexar", action="store_true",
                    help="acrescenta o bloco a um .ses existente (outra temperatura)")
    ap.add_argument("--validar", help="so confere um .ses existente e sai")
    args = ap.parse_args()

    if args.validar:
        sys.exit(0 if validar(args.validar, args.largura) else 1)
    if not args.saida:
        ap.error("--saida e obrigatorio")

    escala = 100.0 if args.strain_em == "percent" else 1.0
    ramos = {}
    for flag, caminho in (("compressao", args.compressao), ("tracao", args.tracao)):
        if caminho:
            sinal = -1 if flag == "compressao" else 1
            pts = ler_csv(caminho, escala)
            if detectar_ramo(pts) != sinal:
                print("AVISO: %s tem deformacao com sinal oposto ao esperado" % caminho)
            ramos[sinal] = (caminho, limpar_ramo(pts, sinal))
    if args.csv:
        pts = ler_csv(args.csv, escala)
        sinal = detectar_ramo(pts)
        ramos[sinal] = (args.csv, limpar_ramo(pts, sinal))
    if not ramos:
        ap.error("informe --compressao/--tracao ou --csv")

    # quantos pontos cada ramo recebe
    if args.pontos_total:
        if len(ramos) == 2:
            # a origem e comum: N total -> (N+1)/2 por ramo, contando a origem
            por_ramo = {s: (args.pontos_total + 1) // 2 for s in ramos}
            maior = max(ramos)
            por_ramo[maior] = args.pontos_total + 1 - por_ramo[min(ramos)]
        else:
            por_ramo = {s: args.pontos_total for s in ramos}
    else:
        por_ramo = {s: args.pontos for s in ramos}

    dec = args.decimais
    escolhidos, relatorio = {}, []
    for sinal, (caminho, pts) in sorted(ramos.items()):
        sel = selecionar_com_regras(pts, por_ramo[sinal], dec, dec, args.gap_stress)
        if len(sel) < 2:
            sys.exit(
                "ERRO: com %d casas decimais a curva de %s colapsa em %d ponto(s).\n"
                "      A deformacao vai ate %.6f, ou seja, cabe em menos de um\n"
                "      degrau de 0,%s. Reveja a unidade da deformacao ou use\n"
                "      --decimais com mais casas."
                % (dec, os.path.basename(caminho), len(sel),
                   max(abs(e) for e, _ in pts), "0" * (dec - 1) + "1"))
        escolhidos[sinal] = sel
        mpa, pct = erro_interpolacao(pts, sel)
        relatorio.append((("compressao" if sinal < 0 else "tracao"),
                          os.path.basename(caminho), len(pts), len(sel), mpa, pct))

    curva = aplicar_regras(sorted({p for sel in escolhidos.values() for p in sel}),
                           dec, dec, args.gap_stress)
    linhas = montar_bloco(curva, args.grupo, args.temperatura, args.largura, dec, dec)

    modo = "a" if args.anexar and os.path.exists(args.saida) else "w"
    with open(args.saida, modo, newline="") as f:
        f.write("\r\n".join(linhas) + "\r\n")

    print("ramo         arquivo                       lidos  usados   erro max")
    for nome, arq, n_in, n_out, mpa, pct in relatorio:
        print("%-12s %-28s %6d  %6d   %6.3f MPa (%.2f%% do pico)"
              % (nome, arq[:28], n_in, n_out, mpa, pct))
    print("\n%s: %d pontos na tabela, %d registros MPC, deformacao de %.*f a %.*f"
          % (os.path.basename(args.saida), len(curva), (len(curva) + 9) // 10,
             dec, curva[0][0], dec, curva[-1][0]))
    menor = min((abs(b[1] - a[1]) for a, b in zip(curva, curva[1:])), default=0.0)
    print("%d casas decimais | menor degrau de tensao: %.2f MPa (minimo %.2f)"
          % (dec, menor, args.gap_stress))
    print()
    validar(args.saida, args.largura)

    resumo = os.path.splitext(args.saida)[0] + "_pontos.json"
    json.dump([{"strain": e, "stress": s} for e, s in curva],
              open(resumo, "w"), indent=1)
    print("pontos escolhidos salvos em %s" % os.path.basename(resumo))


if __name__ == "__main__":
    main()

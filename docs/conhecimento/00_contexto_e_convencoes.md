# Contexto e convenções do projeto (confirmado pelo usuário)

Fonte: conversa de análise do modelo `76028_AA_Max_23.ses` + `76028_AA_Max.DXF`.

## Objetivo
Dado **um desenho (DXF)** + **uma curva de material (CSV de ensaio)**, devolver o `.ses` do COSMOS/M
(Geostar V2.60 / NSTAR) pronto para rodar. Produto: juntas e retentores (borracha + aço).

## Convenções confirmadas
- **Juntas = sempre deformação plana (2D), nunca axissimétrico.**
- Nome do caso: `<peça>_<corte>_<condição>_<temperatura>`. Ex.: `76028_AA_Max_23`
  - `AA` = corte A; `Max` = máxima compressão (borracha na condição mais alta, carcaça na mais baixa); `23` = 23 °C.
- Unidades: mm e MPa (DXF com INSUNITS=4; curva em MPa).
- Curva do material vem de **ensaio de laboratório com a própria peça**; é reduzida pela skill
  `conversor-curva-cosmos` (35 pts por ramo → 69 pts: 34 compressão + origem + 34 tração).
  Assimetria de rigidez compressão/tração é dado real do ensaio.
- Comportamento da borracha: **elástico não linear** (curva σ×ε via `MPC`), ν = 0,49.
- Aço: só precisa ser rígido. E = 2E9 foi valor arbitrário (pode usar valor real sem problema).
- Análise atual: **pequenos deslocamentos** (não aparece `A_NONLINEAR` no .ses). Tema a rediscutir.
- Contato: elementos `GAP` tipo `PT` (63 nós) em quase todo o perfil livre da borracha, com folga
  proposital (nós a mais, para não faltar contato). Alvo = curvas 26 e 27 (faces das placas).
- `SFEXTR` serve para criar superfície e obter malha regular/simétrica no aço.
- O `R_NONLINEAR` fica como comentário no .ses (o solver é disparado pela interface).

## Estrutura do modelo 76028_AA_Max_23 (resumo)
1. Geometria: `CRACSE` (arcos, nºs ímpares 1..11) e `CRLCORD` (linhas 13..27) = DXF 1:1 (erro < 1e-6).
2. Borracha: `CT`/`RG`/`EGROUP,1,PLANE2D`/`MPROP NUXY 0.49`/`MPC`/`RCONST`/`MA_QUAD` (tamanho 0,1 mm).
3. Bloco de aço (x=3,0..5,35): `EGROUP,2`, `MPROP EX`, malha 0,1 mm; face x=5,35 engastada (`DCR,24,AU,0`).
4. Placas: `SFEXTR,26,26,..Y,1` e `SFEXTR,27,27,..Y,-1`; `M_SF ... 10,2`.
5. `NMERGE` cola borracha ao aço; `CURDEF TIME` 0→100; `TIMES,0,100,1`.
6. `DCR,28,UY,-1` e `DCR,31,UY,+1` (placas andam 1 mm cada); `DCR,30/33,UX,0`.
7. `EGROUP,3,GAP` + 63 `EL,...,PT` + `NL_GSAUTO,...,26,27`.
8. Contagens: 868 elementos + 63 contato = 931; 986 nós antes do `NMERGE`.

## Pontos frágeis para automação (DXF + curva → .ses)
- Nº das curvas depende da ordem do DXF (CT, DCR, NL_GSAUTO, SFEXTR).
- Os 63 nós de contato devem ser escolhidos **por coordenada** (perfil livre da borracha, exceto a face colada x=3,0),
  não por número.
- `NMERGE,1,N` e `EMERGE,1,N` dependem do tamanho final da malha.
- Deslocamento das placas (1 mm) é o que muda entre condições Min/Nom/Max.

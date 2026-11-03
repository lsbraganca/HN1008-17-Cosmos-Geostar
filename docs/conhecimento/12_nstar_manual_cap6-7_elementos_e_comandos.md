# Manual NSTAR — notas dos capítulos 6 e 7 (Biblioteca de elementos; Comandos e exemplos)

Fonte: PDFs `Nstar_81-160` e `Nstar_161-240` (págs. 6-1 a 7-33 do manual).

## Cap. 6 — Biblioteca de elementos
- **PLANE2D**: 4 a 8 nós, 2 GDL/nó, tensão plana / deformação plana / axissimétrico. Modelos de material disponíveis
  (Tab. 6-2): elástico linear isotrópico/ortotrópico/viscoelástico, **elástico não linear por curva ("Elastic Curved Description")**,
  fluência, Mooney-Rivlin, Ogden, Blatz-Ko, von Mises (iso/cinemático), Drucker-Prager, concreto, membrana (tensão plana), definido pelo usuário.
- **Constantes reais do PLANE2D (Tab. 6-3, p. 6-7)**: `RC1 = espessura (SÓ para a opção de tensão plana)`; `RC2 = ângulo do material (só ortotrópico linear)`.
  → Em deformação plana a espessura não é usada. (No .ses de referência a borracha tem RC1=5 e o aço RC1=0.)
- **GAP (Tab. 6-3, p. 6-8)** — constantes reais (tabela é do gap nó-a-nó; no gap de 1 nó valem as mesmas posições, atrito = RC2):
  | RC | Significado |
  |---|---|
  | RC1 | deslocamento relativo permitido (folga) |
  | **RC2** | **coeficiente de atrito** |
  | RC3 | rigidez da mola |
  | RC4 | pré-carga no gap |
  | RC5 | distância máxima além da qual o gap responde como perfeitamente rígido |
  | RC6, RC7 | constantes de amortecedor |
  | RC8–RC10 | rigidez do *source* em X, Y, Z (soft springs) |
  | RC11–RC13 | rigidez do *target* em X, Y, Z (soft springs) |
  No .ses de referência: `RCONST,3,3,1,10, 0,0.4,0,0,1E+008,0,1,0,0,0` → RC1=0, **RC2=0,4 (atrito)**, RC3=0, RC4=0, **RC5=1E8**, RC6=0, RC7=1, RC8–10=0.
  (RC5=1E8 = limite de distância praticamente infinito; contato tratado como rígido pela técnica híbrida.)

## Cap. 7 — Comandos
### Opções do `EGROUP,n,PLANE2D,OP1,...,OP8` (p. 7-18 e exemplos)
Ordem das opções (painel Geostar): **OP1 S/F flag (Solid) · OP2 tipo de integração (QM6 etc.) · OP3 Type (tensão plana / deformação plana / axissimétrico)
· OP4 direção da tensão (global cartesiana) · OP5 modelo de material · OP6 deslocamento (0 pequeno / 1 Lagrangiano atualizado / 2 Lagrangiano total)
· OP7 fluência (0 não / 1 sim) · OP8 plasticidade (pequena/grande deformação)**.
Exemplos do manual (valores numéricos):
- Mooney-Rivlin: `EGROUP,1,PLANE2D,0,2,0,0,3,2,0` → **OP5=3 (M-R), OP6=2 (T.L.)**.
- Ogden: `EGROUP,1,PLANE2D,0,2,0,0,6,2,0` → **OP5=6 (Ogden), OP6=2**.
- Viscoelástico: `EGROUP,1,PLANE2D,0,2,1,0,8,0,0` → **OP5=8**, OP3=1.
- von Mises: OP5=1/2 (iso/cinemático) e 5/11 aparecem em NL_AUTO como elastoplásticos; Op5=10 = membrana enrugada; Op7=1 fluência.
- Opção 5 = 4 no .ses de referência = modelo **elástico por curva** (a confirmar no OCR dos capítulos seguintes).
- **Ponto a verificar**: no .ses de referência, a **borracha tem OP3=0 e o aço OP3=2**. Se 0 = tensão plana e 2 = axissimétrico
  (codificação a confirmar), o modelo não estaria em deformação plana como o usuário afirma. Ver nota em 00_contexto.

### Sequência típica de uma análise estática não linear (p. 7-2 a 7-15)
`EGROUP` (op 5 material, op 6 geometria) → `MPROP` → `MPCTYP`/`MPC` (curva) → `TIMES` → `CURDEF` (curva de tempo) → `ACTSET,TC,n` → cargas/deslocamentos
(`DCR` etc.) → `ACTSET,TC,0` → `A_NONLINEAR` → `NL_CONTROL` → `NL_AUTO` → `NL_NRESP`/`NL_PLOT`/`NL_PRINT` → `R_NONLINEAR`.
`A_NONLINEAR`, `NL_CONTROL`, `NL_AUTO` podem ser omitidos se os defaults servirem (é o caso do .ses de referência).
- `A_NONLINEAR` (exemplo p. 7-29): opção S (estático), passos entre reforma da rigidez = 1, passos entre iterações de equilíbrio, máx. de iterações de equilíbrio = 20.
- `TIMES`: início, fim e incremento de tempo. `CURDEF,TIME,n,...`: curva de tempo (pseudo-tempo, valor 0→1 etc.).
- Controle por deslocamento usa a curva de tempo 1 para o GDL controlado; cargas com curva > 1 são "não paramétricas".
- Boa prática: **desativar a curva de tempo logo após usar** (`ACTSET,TC,0`).
- `NL_NRESP`: nós para resposta X-Y; `NL_PLOT`: passos salvos para pós-processamento (ini, fim, incremento); `NL_PRINT`: saída no arquivo .OUT;
  `PRINT_NDSET`: faixa de nós a imprimir.
- Pós-processamento: `DEFPLOT`, `ANIMATE`, `STRPLOT` (VON, etc.), `DISPLOT`, `LSECPLOT`, `ACTXYPOST`/`XYPLOT` (histórico de tempo).

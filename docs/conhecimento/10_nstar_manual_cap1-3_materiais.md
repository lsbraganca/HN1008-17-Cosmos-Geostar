# Manual NSTAR (COSMOS/M) — notas dos capítulos 1 a 3 (páginas do livro 1-1 a 3-34)

Fonte: PDF `Nstar_1-80` (escaneado). Referências de página = numeração do próprio manual.

## Cap. 1 — Introdução (p. 1-1 a 1-10)
- Três fontes de não linearidade: geométrica (grandes deslocamentos), material, e **contato (fronteira)**.
- Contato é avaliado com elementos **GAP** entre nós das fronteiras adjacentes (p. 1-4).
- Carga é aplicada em passos pelo conceito de **curva de tempo**: "tempo" é pseudo-variável que dá a
  intensidade da carga no passo (estático). Passo de tempo depende do nível de não linearidade; o
  programa tem **auto-stepping adaptativo** (p. 1-6).
- Capacidades: grandes deslocamentos (Lagrangiano total e atualizado); **grandes deformações para borracha
  (Total Lagrangian)**; hiperelasticidade (Mooney-Rivlin, Ogden, Blatz-Ko); elasticidade não linear por **curva
  σ×ε definida pelo usuário**; plasticidade; fluência; viscoelasticidade; contato com atrito generalizado.
- Controle de solução: força, **deslocamento**, arc-length (Riks). Iteração: Newton-Raphson, NR modificado, BFGS.
  Line search; tolerâncias e intervalo de equilíbrio controlados pelo usuário; restart; auto-stepping.
- Cargas: deslocamentos prescritos ≠ 0 associados a curvas de tempo; cálculo de reações.
- Pós: tensões, deformações, forças de gap, deformada por passo, gráficos X-Y de reação × tempo.

## Cap. 2 — Não linearidade geométrica (p. 2-1 a 2-4)
- **Grande deformação (finite strain)**: deformações locais grandes, rigidez muda com a forma do elemento;
  "o exemplo típico é a deformação de materiais tipo borracha" (p. 2-2).
- **Grande deflexão**: rotações finitas com deformações pequenas.
- Duas formulações para elementos contínuos (PLANE2D, TRIANG, SOLID, TETRA): Total Lagrangian (T.L.) e Updated Lagrangian (U.L.).
- Comando de controle de solução: `NL_CONTROL` (Analysis > NONLINEAR > Solution Control).

## Cap. 3 — Modelos de material (p. 3-1 a 3-34)

### Elástico não linear por curva (É O MODELO DA BORRACHA NO NOSSO .ses) — p. 3-5 a 3-8
- Relação σ = D^s ε com **módulo secante** E^s e ν (NUXY).
- Para incorporar: definir **NUXY** (MPROP), definir **`MPCTYPE` com a opção elástica**, e a curva σ×ε com **`MPC`**.
  (No .ses de referência não há `MPCTYPE` explícito → verificar onde isso é ativado: provável opção do `EGROUP`.)
- O vetor de deformação total gera a **deformação efetiva** ε̄, usada para ler o módulo secante na curva.
- A curva vale do **3º quadrante (compressão) ao 1º (tração)** para elementos 2D e 3D. Usa-se interpolação
  entre ramo de compressão e de tração por uma razão **R** (função da deformação volumétrica, ε̄ e ν):
  - R = +1 → tração uniaxial; R = −1 → compressão. Fora desse intervalo o programa "empurra de volta ao limite".
  - E^{s,t} = [E(c)+E(t)]/2 + R·[E(t)−E(c)]/2.
- Se o 3º quadrante não for informado, o programa assume comportamento **simétrico** (tração = compressão).
- Pode ser usado com: TRUSS2D/3D, BEAM2D/3D, **PLANE2D 4/8 nós (tensão plana, deformação plana, axissimétrico)**,
  TRIANG, SOLID, TETRA, SHELL3T/4T, SPRING.
- Implicação: a curva do ensaio (compressão + tração) é usada de fato nos dois ramos; a rigidez em estados
  mistos (cisalhamento, compressão confinada) é uma **interpolação**, não uma lei hiperelástica calibrada.
  Para compressão confinada de junta, isso é aproximação — comparar com Mooney-Rivlin/Ogden quando houver dados.

### Hiperelástico (borracha incompressível) — p. 3-8 a 3-15
- Penalidade (deslocamento, integração cheia ou reduzida) ou misto **u/p (deslocamento-pressão)**.
  u/p disponível para PLANE2D 4–8 nós (deformação plana e axissimétrico) e SOLID 8 nós.
  PLANE2D 4 nós: 1 grau de pressão; 5–8 nós: 3.
- Locking: para pressões hidrostáticas localizadas significativas, **recomenda-se u/p** (p. 3-11).
- **Mooney-Rivlin**: constantes `MOONEY_A..F` via MPROP; (A+B) > 0. Bom até ~150% de deformação (stretch 2,5).
- **Ogden**: `MU1..4`, `ALPH1..4`, até 4 termos. Bom até 500–600%. Ogden de 2 termos com α1=2, α2=−2,
  μ1=2A, μ2=−2B equivale a Mooney-Rivlin.
- **Blatz-Ko**: espuma de poliuretano compressível, só módulo E (ν=0,25 fixo).
- Notas operacionais importantes (p. 3-11 a 3-12):
  1. **Sempre Total Lagrangian** para PLANE2D/TRIANG/SOLID/TETRA hiperelásticos.
  2. Usar **Newton-Raphson**.
  3. Se há pressão, usar carga dependente do deslocamento.
  4. Com u/p ν recomendado **0,499 a 0,4999**; sem u/p, **0,48 a < 0,5** é aceitável (0,49–0,499 no deslocamento).
  5. Borracha deforma rápido em cargas baixas → **carregamento inicial lento**.
  6. Aumento brusco de carga gera termos negativos na diagonal ou divergência → usar **restart** ou **auto-stepping adaptativo**.
  7. **Controle por deslocamento (ou arc-length)** costuma ser mais efetivo que por força quando aparecem termos diagonais negativos.
  8. Elementos de ordem superior dão mais estabilidade numérica que os de ordem baixa.
  9. Tensão plana: incompressibilidade perfeita, NUXY ignorado, sem u/p.
- ν muito próximo de 0,5 → pode terminar por termos diagonais negativos / falta de convergência.

### Plasticidade (aço, se necessário) — p. 3-17 a 3-22
- von Mises (bilinear: `SIGYLD`, `ETAN`; multilinear: `MPCTYPE` com opção plasticidade + `MPC`). Recomenda-se NR.
- Em multilinear de grande deformação usar **tensão de Cauchy e deformação logarítmica**.
- Drucker-Prager (solo), Tresca: não relevantes aqui.

### Outros (não usados no projeto por ora)
- Fluência (Bailey-Norton / exponencial), viscoelasticidade linear (Maxwell generalizado + WLF: `G1..G8`, `TAUG1..`, `K1..`, `REFTEMP`, `VC1`, `VC2`),
  membrana enrugada, concreto, compósitos/Tsai-Wu. Úteis só se houver relaxação/fluência da borracha.

## A verificar nos próximos capítulos
- Opções do `EGROUP,PLANE2D` (posição 4 = 1 é deformação plana? posição 7 = 4?).
- `A_NONLINEAR` (grandes deslocamentos, formulação) e o que o .ses assume por padrão.
- `NL_CONTROL`, `NL_GSAUTO`, elemento `GAP` e constantes reais, `MPCTYPE`/`MPC` (campo "23").

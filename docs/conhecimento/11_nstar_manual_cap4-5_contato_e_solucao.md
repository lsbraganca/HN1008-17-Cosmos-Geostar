# Manual NSTAR — notas dos capítulos 4 e 5 (Gap/Contato e Procedimentos numéricos)

Fonte: PDF `Nstar_81-160` (págs. 4-1 a 5-21 do manual). Numeração = a do manual.

## Cap. 4 — Gap / Contato

### Técnica do NSTAR
- Usa técnica **híbrida** (força nos gaps, deslocamento no resto): **não precisa de valor de penalidade** e não muda
  o tamanho/banda da matriz (p. 4-1/4-2). O contato é tratado como **rígido**; "a única constante real necessária é o
  **coeficiente de atrito** (rigidez do gap também é considerada)" (p. 4-11).
- Gaps de 2 nós (nó-a-nó): direção do contato conhecida de antemão e fixa. Só aqui há opção de flexibilidade (3ª constante real).
- **Gaps de 1 nó (nó-a-linha em 2D / nó-a-superfície em 3D)** = o que o .ses de referência usa (p. 4-8):
  - Nós **contactor** recebem `EL,n,PT,0,1,<nó>` (elemento de 1 nó).
  - O **target** é uma linha (2D) ou superfície (3D) formada por sub-linhas/sub-superfícies de 2 ou 3 nós (linha) ou 4 ou 9 nós (superfície).
  - Vantagens: não precisa saber o ponto de contato a priori, direção do contato calculada pela forma deformada,
    **malhas não precisam coincidir**, resolve "shrink fit".
  - `EGROUP,n,GAP,...`: **opção 4 = dimensão (1 = 2D, 2 = 3D)**; **opção 5 = nº de nós do target (2 ou 3 para linha; 4 ou 9 para superfície)**.
    No exemplo do manual 2D automático: `EGROUP,2,GAP,1,0,0,1,3,0,0` (op4=1, op5=3).
    No nosso .ses: `EGROUP,3,GAP,1,1,0,1,2,1,0,0` → op4=1 (2D) e op5=2 (sub-linhas de 2 nós = arestas dos elementos de 4 nós). OK.
  - **Opção 7 do EGROUP (GAP) = 1 mata o grupo de gap** (estratégia para interferência inicial; reativar com restart e op7=0). No nosso .ses op7=0 (ativo).
- Regras do target (p. 4-6, 4-11): cada linha/superfície tem lado **positivo** e **negativo**, pela conectividade dos nós; o
  lado negativo é onde os gaps estão **proibidos de entrar**. A normal de cada sub-linha deve apontar para o lado positivo;
  sub-superfícies de um mesmo grupo devem formar uma superfície contínua.
- Soft springs automáticas: constantes reais **r8 a r13** (3 para source, 3 para target) estabilizam partes que ficariam instáveis se o contato fosse ignorado. Usar conjunto de constantes reais **diferente por grupo de gap**.

### Comandos
- `NL_GS` (manual): define sub-linhas/superfícies target nó a nó. Exemplo: `NL_GS,1,1,6,7,2`.
- **`NL_GSAUTO` (Contact Surface by Geometry)**: gera automaticamente os gaps de 1 nó nos contactors e as sub-linhas nos targets;
  **todas as entidades (contactor e target) precisam estar malhadas antes** (p. 4-12). Exemplo do manual:
  `EGROUP,2,GAP,1,0,0,1,3,0,0` → `ACTSET,EG,2` → `NL_GSAUTO,0,1,0,14,14,1,1` e `NL_GSAUTO,0,2,0,11,11,1,1` → `EMERGE`.
  Padrão dos argumentos (inferido do exemplo): `NL_GSAUTO,0,<n° contactor>,0,<target ini>,<target fim>,<inc>,1`.
  No nosso .ses: `NL_GSAUTO,0,1,0,26,27,1,1` → targets = curvas 26 e 27 (faces das placas voltadas para a borracha) — confirmado.
  (O segundo argumento "1" parece indexar o contactor/grupo; no nosso caso os nós de contato foram criados antes com `EL,...,PT`.)
- Exemplo manual com `RCONST,3,3,,2,1,0.3`: duas constantes → **R2 = coeficiente de atrito (0,3)**. No nosso .ses a 2ª constante é 0,4 → **μ = 0,4**.

### Solução de problemas (p. 4-16/4-18) — guardar para depurar
1. "Stop, the diagonal term ... is zero or negative" no 1º passo → modelo (ou parte) **instável por falta de apoio**; gaps não somam rigidez. Corrigir restrições; usar soft trusses.
2. Pós-processamento mostra gaps além da superfície de contato → plotar em **escala 1,0** (`DEFPLOT` com fator 1). Se persistir: orientação (lado positivo) do target errada, ou deslocamento imposto grande demais.
3. "Stop, wrong definition for the contact surfaces" → conectividade/direção do target; sub-superfícies precisam ser contínuas.
4. Dinâmico instável após fechar gaps → introduzir flexibilidade no gap (3ª constante real, gap de 2 nós).
5. Termina depois de fechar alguns gaps com "diagonal ... zero or negative", "convergence not achieved for gap elements",
   "not achieved in 200 iterations" ou "100 contact iterations" → rigidez deteriorada ou incremento grande: **reduzir o incremento de carga**.
- **Atrito torna a análise não conservativa (depende da história)**: aplicar cargas em incrementos que lembrem a história real.
- Contato com grandes deflexões exige **refino de malha** onde o contato é esperado.

## Cap. 5 — Procedimentos numéricos (resumo útil)
- Técnicas de controle: **força**, **deslocamento** (um GDL controlado via curva de tempo) e **arc-length** (Riks). Força e deslocamento falham em pontos de retorno (snap-through/snap-back).
- Iteração: **Newton-Raphson** (rigidez tangente a cada iteração; convergência quadrática), **NR modificado** (reforma no início do passo ou
  no intervalo definido pelo usuário), **quase-Newton BFGS** (com line search, TOL 0,5 recomendado).
- Critérios de convergência: **deslocamento**, **força (resíduo)** e **energia**; também critérios de divergência.
- Comandos de controle: **`NL_CONTROL`** (Solution Control), **`A_NONLINEAR`** (opções de análise: grandes deslocamentos, etc.), `NL_INTGR` (dinâmico).
  Não aparecem no .ses de referência → valem os **defaults** do programa (listados no Command Reference, que não está neste manual).
- Dinâmico: só controle por força; MNR e NR; sem line search. Amortecimento Rayleigh `NL_RDAMP`.
- **Auto-stepping adaptativo (`NL_AUTO`)**: aumenta passo onde é linear e reduz onde há não linearidade forte; DTMIN/DTMAX opcionais
  (recomendados em problemas complexos). Protege contra: iterações excedidas, divergência de resíduo/energia, **não convergência de gap/contato**,
  termos negativos na diagonal. Reduz o passo se rotação incremental > 10°, ou incremento de deformação plástica/fluência > CETOL (padrão 0,01).
- Integral J (mecânica da fratura): fora do escopo atual.

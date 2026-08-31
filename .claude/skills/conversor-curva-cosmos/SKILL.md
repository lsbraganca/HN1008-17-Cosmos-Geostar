---
name: conversor-curva-cosmos
description: Converte curvas tensão-deformação de ensaios mecânicos (CSVs de compressão e tração) em arquivo .ses com registros MPC para Patran/Nastran/Cosmos, reduzindo milhares de amostras a um número escolhido de pontos sem alterar a curva. Use sempre que o usuário mencionar arquivo .ses, registros MPC, curva tensão-deformação, stress-strain, ensaio de tração ou compressão, dados de material hiperelástico/elastômero para FEA, ou pedir para "espaçar", "reduzir" ou "escolher N pontos" de um CSV de ensaio — mesmo que não cite ".ses" ou "MPC" explicitamente. Também use para conferir o formato de um .ses existente.
---

# Conversor de curva para .ses (Cosmos/Patran)

Máquinas de ensaio cospem CSVs com centenas ou milhares de amostras. O solver
quer uma tabela enxuta — tipicamente algumas dezenas de pontos por ramo. O
trabalho é escolher **quais** pontos manter para que a curva reconstruída por
retas seja indistinguível da original, e depois escrever isso no formato de
sessão, que é rígido quanto a colunas e continuação de linha.

O script `scripts/csv_to_ses.py` faz as duas coisas e já valida o resultado.
Use-o em vez de escrever código novo — ele existe justamente porque a lógica
de seleção e as regras de coluna são chatas de acertar do zero.

## Fluxo

1. **Leia os CSVs e o modelo .ses**, se o usuário anexou um. O modelo manda no
   formato: confira `grupo de elementos`, largura de linha e estilo de número
   antes de assumir os padrões abaixo.
2. **Confirme os parâmetros** que mudam o resultado (veja "Decisões" adiante).
3. **Rode o script.**
4. **Relate** o erro de interpolação e qualquer anomalia que você notou nos
   dados brutos. O engenheiro precisa saber se a tabela é fiel ao ensaio.

```bash
python3 scripts/csv_to_ses.py \
  --compressao HN1008-17_compressao_23C.csv \
  --tracao     HN1008-17_tracao_23C.csv \
  --temperatura 23 --pontos 35 \
  --saida HN1008-17_23C.ses
```

Outras chamadas úteis:

| Situação | Flag |
|---|---|
| Um ensaio só (o ramo é detectado pelo sinal) | `--csv arquivo.csv` |
| N pontos na curva inteira, não por ramo | `--pontos-total 35` |
| Deformação já adimensional no CSV | `--strain-em absoluto` |
| Outro degrau mínimo de tensão | `--gap-stress 0.2` |
| Outra temperatura no mesmo arquivo | `--temperatura 120 --anexar` |
| Só conferir um .ses existente | `--validar arquivo.ses` |

O script imprime uma tabela com pontos lidos/usados e o erro máximo por ramo,
roda a validação de formato no que acabou de escrever, e salva os pontos
escolhidos em `<saida>_pontos.json` para conferência ou plotagem.

## O formato .ses (registros MPC)

Cada linha lógica é:

```
MPC,<grupo de elementos>,<temperatura>,<grupo de linha>,<strain>,<stress>,... (10 pares)
```

- **Grupo de elementos**: `1` como padrão, salvo instrução em contrário.
- **Temperatura** em °C, sem unidade — `23`, `120`.
- **Grupo de linha**: índice do primeiro ponto do registro, de 10 em 10 —
  `1`, `11`, `21`, `31`... Reinicia em `1` a cada temperatura. O último
  registro pode ter menos de 10 pares.
- **Quebra de linha**: 70 caracteres de dado + `&` = 71 colunas, terminador
  **CRLF**. O corte é por contagem de caracteres, **não** por vírgula — parte
  um número no meio e o resto vai para a linha seguinte, exatamente como o
  arquivo modelo faz. Uma linha lógica pode gerar três ou mais linhas físicas
  quando os números são longos; isso é normal.
- **Números**: **no máximo 2 casas decimais** — o Cosmos não aceita mais que
  isso. Zero à esquerda suprimido (`-.55`, não `-0.55`), zeros à direita
  cortados, zero puro escrito `0`.
- **Degrau mínimo de tensão**: pontos consecutivos precisam diferir em pelo
  menos **0,1 MPa**. Dois pontos praticamente empatados em tensão fazem o
  solver se perder na interpolação — é melhor um ponto a menos do que dois
  colados. O script descarta os que violam a regra e pede pontos extras na
  seleção para fechar a contagem pedida.

Exemplo real de saída:

```
MPC,1,23,1,-.66,-28.22,-.65,-25.74,-.64,-23.72,-.63,-22.15,-.62,-21.01&
,-.6,-18.76,-.59,-17.09,-.58,-15.9,-.57,-14.89,-.55,-13.54
```

## Curva que não converge — `scripts/suavizar_ses.py`

Um `.ses` fiel ao ensaio pode ser ruim de solver. O sintoma é sempre o mesmo:
**degrau de rigidez entre pontos vizinhos**. Passos de deformação desiguais
(0,01 aqui, 0,09 ali) mais a tensão em 2 casas fazem o módulo tangente de cada
trecho serrilhar — no HN1008-17 a 150 °C ele ia 11 → 28 → 11 → 5,8 → 8,8 → 7 →
2 → 6,6 MPa em pontos consecutivos ao redor do zero. O Newton monta a rigidez
com esse número; se ele triplica e cai pela metade de um trecho para o outro, a
análise oscila e para antes do fim.

`suavizar_ses.py` reamostra a curva mantendo o ensaio:

```bash
python3 scripts/suavizar_ses.py \
  --entrada HN1008-17_150C_original.ses --saida HN1008-17_150C.ses
```

Três etapas, todas no espaço do **módulo**, que é o que o solver enxerga:

1. Ajusta `E(eps) = exp(g(eps))` por Gauss-Newton contra os pontos do ensaio,
   penalizando a curvatura de `g`. Como a tensão sai da integral de `E` a partir
   da origem, `sigma(0)=0` e `E>0` valem por construção — não há como o ajuste
   devolver rigidez negativa. Penalizar `log E`, e não `sigma`, é adimensional e
   pesa igual a compressão (E ~ 270 MPa) e a tração (E ~ 4 MPa).
2. Escolhe as deformações de modo que `log E` ande um tanto fixo por segmento
   (`--dlog`, 12 % por padrão), limitado a `[--passo-min, --passo-max]`. Passo
   curto onde a curva encurva, longo onde ela é reta. **Amostrar uniforme em
   deformação não resolve**: no pé da curva de compressão o módulo cai 15 % a
   cada 0,02 de deformação, e num trecho reto 0,15 não perde nada.
3. Arredonda para 2 casas com programação dinâmica: entre piso, arredondado e
   teto de cada tensão, escolhe a combinação cujos módulos ficam mais perto dos
   da curva suave. Num degrau de 0,3 MPa, ±0,005 já move o módulo do trecho em
   3 % — arredondar cada ponto isolado joga essa folga fora.

O relatório mostra a **razão de módulo entre segmentos vizinhos**, antes e
depois. É o número que decide convergência: `[0,29 .. 3,30]` é curva que trava,
`[0,86 .. 1,11]` é curva que roda.

### O piso de 2 casas decimais vale aqui também

Perto do zero a tensão é pequena e o arredondamento é grosseiro: em `eps = -0,11`
um desvio de 0,11 MPa é 25 % da tensão, e é só **um passo de arredondamento**.
Relate o desvio em MPa junto com o percentual, senão o engenheiro lê 25 % e
pensa que a curva mudou de material.

Onde os dois efeitos brigam — módulo variando rápido *e* tensão baixa — existe
um passo ótimo, `h ~ sqrt(0,02 / (E * dlogE/deps))`, e mesmo nele a razão fica
em torno de 0,85. Não gaste pontos tentando passar disso; o limite é do formato.

## Decisões que mudam o resultado — confirme antes de gerar

**Unidade da deformação — e o limite que ela esbarra.** CSVs de máquina de
ensaio quase sempre trazem `Deformation(%)`; a tabela do solver usa deformação
adimensional, então o script divide por 100 por padrão. Um elastômero que
chega a 268% vira `2.68` e cabe folgado em 2 casas decimais.

**Metal não cabe.** Um ensaio de alumínio ou aço termina perto de 1% de
deformação: adimensional isso é `0.0077`, que com 2 casas vira `0.01` — a
curva inteira colapsa em dois degraus. O script detecta e aborta com essa
mensagem em vez de gerar lixo. Quando acontecer, **não force mais casas
decimais por conta própria**: leve o caso ao usuário, porque só ele sabe se o
Cosmos espera a deformação em % para esse material ou se a coluna do ensaio
está fora de escala. `--strain-em absoluto` mantém a coluna como veio (0 a
0,77), que é a saída provisória enquanto ele não responde.

**N por ramo ou N no total.** "35 pontos" costuma significar **35 em cada
ramo** — 35 na compressão e 35 na tração. Esse é o padrão do script. Se o
pedido for ambíguo e a diferença importar, pergunte; é uma pergunta de dez
segundos que evita refazer.

**A origem entra uma vez só.** `(0,0)` é o extremo comum aos dois ensaios.
Repeti-la quebraria a monotonicidade da deformação e invalidaria a tabela. Com
35 pontos por ramo, a tabela final tem 69 pontos: 34 negativos + a origem + 34
positivos. Diga isso ao usuário para a contagem não parecer erro.

**Descarga do ensaio.** A última linha do CSV às vezes repete a deformação com
tensão menor — é o início do retorno. O script descarta tudo que não avança,
porque a deformação precisa ser estritamente crescente ao longo da tabela.

## Como os pontos são escolhidos

Começa pelos dois extremos do ramo e insere, um a um, o ponto que mais se
afasta da poligonal atual (distância perpendicular, com os eixos normalizados
para que MPa e adimensional pesem igual). O resultado concentra pontos onde a
curva encurva e espaça onde ela é reta — que é literalmente "espaçar os pontos
mantendo a curva".

Amostragem uniforme em deformação é tentadora e ruim: gasta pontos no trecho
linear e perde o joelho, que é justamente onde o solver precisa de resolução.

O erro que importa é o **desvio máximo em MPa entre a curva original e a
poligonal dos pontos escolhidos**, que o script calcula e imprime — já contando
o arredondamento para 2 casas.

Antes de propor mais pontos, veja se o erro está **saturando**. As 2 casas
decimais criam um piso: num trecho onde a tensão anda rápido com pouca
deformação, mexer a deformação em ±0,005 já desloca vários MPa, e nenhum
número de pontos conserta isso. Rode com 35, 45 e 60 e compare — se o erro
mal se move (o HN1008-17 fica em ~2,5% na compressão nos três), o piso é do
formato e 35 pontos bastam; dizer isso ao usuário vale mais do que entregar
uma tabela três vezes maior sem ganho. Se o erro cai de verdade, aí sim
proponha o número maior.

## Anomalias nos dados — sinalize, não conserte sozinho

Ensaios reais trazem artefatos, e o "pé" da curva é o suspeito de sempre:
tensão subindo com deformação ainda praticamente nula, o que produz um módulo
inicial absurdo e um joelho falso na origem. Isso aparece como uma
assimetria gritante entre os ramos — por exemplo ~190 MPa de rigidez inicial na
tração contra ~9 MPa na compressão.

Mantenha fiel ao ensaio por padrão: o usuário pediu a curva dele, não uma
curva idealizada. Mas **diga o que viu**, com os números, e ofereça remover o
ponto. Descartar dado sem avisar é pior do que entregar uma curva estranha.

## Entrega

Mostre o conteúdo do .ses gerado na resposta (é curto e o engenheiro quer
conferir de olho), informe a contagem de pontos por ramo, o erro máximo de
interpolação e a faixa de deformação coberta. Se houver repositório em jogo,
faça commit; se houver ferramenta de envio de arquivo, mande o .ses junto.

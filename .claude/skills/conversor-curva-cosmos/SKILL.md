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
- **Números**: zero à esquerda suprimido (`-.55`, não `-0.55`), zeros à
  direita cortados, zero puro escrito `0`.

Exemplo real de saída:

```
MPC,1,23,1,-.66177,-28.222,-.64789,-25.738,-.63557,-23.717,-.62548,-22&
.154,-.61751,-21.008,-.60042,-18.757,-.58676,-17.093,-.57562,-15.898,-&
.56548,-14.886,-.55091,-13.535
```

## Decisões que mudam o resultado — confirme antes de gerar

**Unidade da deformação.** CSVs de máquina de ensaio quase sempre trazem
`Deformation(%)`; a tabela do solver usa deformação adimensional. O script
divide por 100 por padrão. Um ensaio que chega a 268% vira `2.6786`. Se os
números do CSV já estiverem na mesma faixa do modelo .ses, use
`--strain-em absoluto`.

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
poligonal dos pontos escolhidos**, que o script calcula e imprime. Abaixo de
~0,5% da tensão de pico a curva é visualmente a mesma; se passar disso,
proponha mais pontos em vez de entregar calado.

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

# Manual NSTAR — cap. 8: problemas de verificação (páginas 8-1 a 8-268 do manual)

Fonte: PDFs `Nstar_161-240`, `241-320`, `321-400`, `401-440` (OCR local; os arquivos de verificação originais são `Vprobs\Nonlinear\NSxx.GEO` na instalação do COSMOS/M).
O manual **só mostra os nomes das opções do `EGROUP` (painel Geostar), não os códigos numéricos** — o código da OP3 (tipo plano) não é resolvido pelo PDF.
Para conferir: no Geostar abrir `Propsets > Element Group` do grupo 1 e ler "OP3: Type".

## Problemas mais relevantes para borracha/juntas
| Problema | Assunto | Lição aplicável |
|---|---|---|
| **NS80** | O-ring de borracha comprimido entre duas placas de aço. **Mooney-Rivlin (C1=175, C2=10 psi, ν=0,49)**, **grande deflexão**, controle por **deslocamento**, contato com atrito, PLANE2D **axissimétrico**, 12 passos | Placa mantida por **2 soft springs/trusses (E=1 psi)** para evitar singularidade; atrito 0,01 (desliza) × 0,5 (não desliza): opção de atrito 1 = generalizado, 2 = deslizamento (mais rápido quando desliza). Tempo de CPU 450–670 s |
| **NS87** | Cilindro de borracha em **deformação plana** entre duas placas sem atrito. M-R A=0,293 MPa B=0,177 MPa, **ν=0,4999 (K/G=5000)**, 8 nós u/p, **grande deformação, auto-stepping**, deslocamento prescrito, GAP com alvo rígido; deslocamento = metade do diâmetro | Referência para junta/retentor em deformação plana: **elemento 8 nós u/p + hiperelástico + T.L.** Resultado coincide com o ADINA |
| **NS76C** | Folha de Ogden em **deformação plana**, ν=0,499 | Ogden 3 termos (α=1,3 / 5,0 / −2,0) |
| **NS86** | Barra **elástica não linear com comportamento assimétrico tração/compressão**, **pequena deflexão**, controle por deslocamento; PLANE2D tensão plana etc. | É o modelo usado no nosso .ses (curva). O manual só valida em **pequena deflexão**. Usa a razão R (−1 compressão … +1 tração) para interpolar |
| **NS41** | Flexão de viga com material elástico não linear (PLANE2D, SOLID, shells, viga) | Curva elástica funciona com PLANE2D, erro ≈0,4% |
| **NS36** | Interferência inicial entre dois cilindros, contato nó-a-linha | **Os nós contactores devem estar "dentro" da superfície alvo** (precisa existir normal da superfície; senão o nó é considerado fora de contato, a menos que se faça solução passo a passo com deformação gradual). Modelar o alvo ligeiramente maior que o contactor |
| **NS39** | Contato entre placas circulares, atrito 0,7, nó-a-superfície | Atrito pouco muda o resultado (1,7347 sem × 1,7268 com atrito). Com shells o atrito é ignorado (sem cisalhamento) |
| **NS18** | Chapas ligadas por elementos de atrito | Em grandes deslocamentos a rigidez é reformada a cada passo; trusses nos gaps foram essenciais |
| **NS31 / NS99** | Esmagamento de tubo entre bigornas (plasticidade, grandes deslocamentos, gaps, deformação plana 8 nós) e interferência entre cilindros espessos | Exemplos de contato com grandes deflexões em PLANE2D |
| **NS79** | Passo automático: min 1E-8, máx 0,02 | Ordem de grandeza de DTMIN/DTMAX no `NL_AUTO` |

## Implicações para o gerador DXF + curva → .ses
- **Pequenos deslocamentos + curva (nossa base atual):** consistente com NS86/NS41; confiável enquanto as deformações locais forem moderadas e a curva do ensaio representar bem o estado de tensão da junta (compressão confinada).
- **Grandes deformações:** o caminho validado no manual é M-R/Ogden + T.L. + u/p (NS80, NS87), com ajuste automático por `MPCTYPE` (p. 3-53). Exigiria dados uniaxial **e** deformação plana (e idealmente equibiaxial).
- Contato: nós contactores dentro da largura do alvo (NS36). No 76028 a borracha (x≈1,09–2,81) está bem dentro das placas (x=0–5,35) ✓.
- Sempre aplicar o deslocamento em incrementos pequenos (atrito é dependente da história) e reduzir o incremento quando houver não convergência de gap.

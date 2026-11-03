# Variante com grandes deslocamentos — 76028_AA_Max_23_LD.ses

Arquivos: `casos/76028_AA_Max_23/76028_AA_Max_23.ses` (original) e `..._LD.ses` (variante).

## O que mudou (diff mínimo)
Só a **opção 6 do `EGROUP`** (formulação geométrica; manual p. 7-5/7-6): `0` (pequenos) → `2` (Total Lagrangian), nos grupos 1 (borracha) e 2 (aço).
- `EGROUP,1,PLANE2D,0,1,0,0,4,0,0,0` → `EGROUP,1,PLANE2D,0,1,0,0,4,2,0,0`
- `EGROUP,2,PLANE2D,0,1,2,0,0,0,0,0` → `EGROUP,2,PLANE2D,0,1,2,0,0,2,0,0`
- Grupo 3 (GAP), curva MPC, malha, contornos, tempo e contato: **idênticos**. OP3 (tipo plano) não foi tocado.
Códigos da OP6: 0 pequenos deslocamentos, 1 Lagrangiano atualizado, 2 Lagrangiano total (manual p. 3-42 e exemplos).

## Ressalvas (do manual)
1. **O modelo "elástico por curva" (OP5=4 no nosso .ses) só é verificado no manual com pequena deflexão** (NS86 "small deflection"; NS41 é flexão com curva).
   Todos os exemplos de borracha com grandes deslocamentos/deformações usam **Mooney-Rivlin ou Ogden** com T.L.
   (NS80 O-ring entre placas com atrito; NS87 cilindro em deformação plana entre placas, u/p, auto-stepping, ν=0,4999).
   Em T.L. a deformação é Green-Lagrange e a tensão é 2ª Piola-Kirchhoff; a curva do ensaio (σ×ε de engenharia) pode ser interpretada de forma diferente.
   → Tratar a variante LD como **comparação** com a versão de pequenos deslocamentos e com o ensaio, não como resultado validado.
2. Para grandes deformações da borracha o caminho do manual é **hiperelástico** (`MPCTYPE` 2 = Mooney-Rivlin / 3 = Ogden, ajuste automático a partir de curvas
   uniaxial/deformação plana/equibiaxial; p. 3-53 a 3-64). Só temos dados de compressão/tração uniaxiais → o ajuste de M-R tende a ser pobre sem plane-strain/equibiaxial.
3. Boas práticas do manual para borracha: carregamento inicial lento, **NL_AUTO** (passo adaptativo), controle por deslocamento (já é o caso: deslocamento prescrito),
   ν entre 0,48 e <0,5 (0,49 OK sem u/p); com u/p usar 0,499–0,4999 e elementos de 4–8 nós (4 nós: 1 GDL de pressão).
4. Contato com atrito é não conservativo: aplicar a carga em incrementos que reproduzam a história real; contato com grandes deflexões pede **malha refinada na região de contato** (p. 4-18).
5. NS18: em análise com grandes deslocamentos a rigidez é reformada a cada passo (relevante para custo e convergência).
6. NS80: opção de atrito 1 (generalizado) vs 2 (deslizamento, mais rápido para problemas de deslizamento); soft springs mantêm a placa estável (evitam singularidade).

## Como comparar as duas execuções
Mesmos nós de controle: reação nas placas (`DCR`) × deslocamento (passo 0–100), tensão/deformação máxima na borracha, forma deformada em escala 1,0.
Se as curvas força × deslocamento coincidirem até ~35% de compressão → pequenos deslocamentos já bastam para este caso; se divergirem, a LD precisa de calibração do material.

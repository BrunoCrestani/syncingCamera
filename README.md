# Calibração de câmera — Visão Computacional / UFPR

Gustavo Jakobi (GRR20221253) e Bruno Crestani (GRR20221240).

Calibração da câmera principal de um iPhone 16 Pro com o tabuleiro do VRI (8 × 8 quadrados, 7 × 7 cantos internos). O projeto estima a matriz intrínseca K e a distorção, remove a distorção das fotos e confere a projeção de pontos 3D em fotos que não entraram na calibração. O relatório está em [RELATORIO.pdf](RELATORIO.pdf); o fonte LaTeX está em `relatorio/`.

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `imagens/` | 19 fotos originais do iPhone (JPEG, 4536 × 8064) |
| `preparar_imagens.py` | Aplica a orientação EXIF, reduz as fotos para 1/4 e separa calibração e validação |
| `calibrar.py` | Detecta os cantos, calibra, remove a distorção e confere a projeção |
| `resultados/` | Saídas da última execução |

## Execução

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python preparar_imagens.py
python calibrar.py \
  --calibracao dados_preparados/calibracao \
  --validacao dados_preparados/validacao \
  --colunas 7 --linhas 7 --quadrado-unidades --modelo-distorcao radial1 \
  --saida resultados
```

`preparar_imagens.py` recria `dados_preparados/` a cada execução. As fotos de validação são IMG_8157, IMG_8165, IMG_8171 e IMG_8174 (opção `--validacao`).

Não medimos o lado do quadrado, então `--quadrado-unidades` usa lado 1 e as coordenadas 3D ficam em unidades de quadrado. Com a medida, use `--quadrado-mm VALOR`.

## Método

1. **Cantos.** `findChessboardCorners` procura o tabuleiro na escala original e em cópias reduzidas, porque reflexos e logotipos atrapalham o detector. `findChessboardCornersSB` é a última tentativa. `cornerSubPix` refina os cantos na escala original. Uma homografia confere cada detecção: se o resíduo RMS passa de 2 px, a detecção é descartada.
2. **Calibração.** `calibrateCamera` estima K e a distorção. O modelo `radial1` estima k1, p1 e p2. O modelo `completo` também é ajustado e aparece em `comparacao_modelos`, para comparação.
3. **Distorção.** `getOptimalNewCameraMatrix` (α = 1) e `undistort` geram a foto corrigida. A retitude mede a distância RMS dos cantos à reta ajustada em cada linha e coluna do tabuleiro, antes e depois da correção.
4. **Projeção 3D.** Nas fotos de validação, `solvePnP` estima a pose com metade dos cantos (padrão xadrez). A outra metade é projetada com `projectPoints` e comparada com os cantos detectados. Um cubo com Z ≠ 0 também é projetado. O topo fica do lado da câmera.
5. **Pontos medidos (opcional).** `--pontos arquivo.json` projeta pontos físicos medidos fora do plano, no formato `[{"imagem": "IMG_8157.png", "xyz_mm": [x, y, z], "uv_px": [u, v]}]`. Requer `--quadrado-mm`.

## Saídas

| Arquivo | Conteúdo |
| --- | --- |
| `resumo.json` | K, distorção, R e t por foto, erros, retitude, vértices do cubo e comparação de modelos |
| `calibracao.npz` | K, distorção e K corrigida |
| `projecoes.csv` | Pontos 3D de teste, pixels previstos e observados, erro |
| `cantos_*.jpg` | Cantos detectados |
| `projecao_*.jpg` | Cantos observados (verde), projetados (vermelho) e cubo |
| `distorcao_*.jpg` | Foto original à esquerda e corrigida à direita |

Os erros estão em pixels, na resolução preparada de 1134 × 2016.

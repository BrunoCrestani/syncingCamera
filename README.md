# Calibração de câmera — Visão Computacional / UFPR

Projeto para calibrar uma câmera com tabuleiro, remover distorção e conferir a projeção de pontos 3D em fotografias reservadas. **As fotos já foram recebidas e organizadas; os resultados numéricos ainda dependem da execução com OpenCV.**

## Fotografias recebidas em 08/10/2026

Foram recebidos 123 arquivos: 104 JPG e 19 com extensão DNG. Os JPG possuem 52 duplicatas idênticas por SHA256, restando 52 fotografias únicas. Os 19 arquivos chamados DNG contêm, na realidade, imagens JPEG/MPO; os metadados identificam um **iPhone 16 Pro**, lente traseira de 6,765 mm (equivalente a 24 mm), com resolução 4536 × 8064. Não são arquivos RAW apesar do nome.

A inspeção visual identificou um tabuleiro de **8 × 8 quadrados**, portanto **7 × 7 cantos internos**. O lado físico de um quadrado ainda precisa ser informado.

`preparar_imagens.py` preserva os originais, elimina as cópias da seleção e organiza os grupos em `dados_preparados/`, com inventário de origem, hashes, metadados e folhas de contato. Os JPG sem identificação de câmera são separados por resolução (1200 × 1600 e 1600 × 1200). Não os misturem ao conjunto do iPhone sem confirmar câmera, lente e transformações aplicadas na exportação.

O conjunto identificado do iPhone foi reduzido uniformemente para **1134 × 2016**, sem recorte, usando o mesmo fator 1/4 nas duas direções e em todas as vistas. A matriz K resultante corresponderá a essa resolução. Separaram-se 15 vistas para calibração e 4 para validação antes de ajustar qualquer parâmetro. Algumas vistas têm o tabuleiro parcialmente fora do quadro e podem ser rejeitadas pelo detector.

Para reproduzir a organização em uma nova pasta:

```bash
.venv/bin/python preparar_imagens.py --entrada imagens --saida dados_preparados_novo
```

Para instalar as dependências no computador com acesso à internet:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Consultem o nome exato da pasta do iPhone em `dados_preparados/inventario.json`. Se a medida física ainda não estiver disponível, usem `--quadrado-unidades` no lugar de `--quadrado-mm`. Nesse modo o lado vale 1, as coordenadas e translações são expressas em **unidades de quadrado**, e não se deve apresentá-las como milímetros. K e a distorção podem ser estimadas sem conhecer o lado em milímetros. Quando a medida chegar, executem com `--quadrado-mm VALOR_REAL`.

Comando preparado para o conjunto recebido, sem inventar uma medida física:

```bash
.venv/bin/python calibrar.py \
  --calibracao dados_preparados/iPhone_16_Pro_390156_4536x8064/calibracao \
  --validacao dados_preparados/iPhone_16_Pro_390156_4536x8064/validacao \
  --colunas 7 --linhas 7 --quadrado-unidades --modelo-distorcao radial1 \
  --saida resultados/iphone
```

## Entrega de hoje

O enunciado pede quatro resultados: pesquisa breve, calibração com matrizes, imagens com distorção corrigida e comparação entre posições 3D e pixels observados em algumas imagens. A calibração estéreo é opcional. Para esta entrega, priorize uma câmera.

1. Escolham a câmera e anotem modelo, lente, resolução e nomes da dupla.
2. Meçam o lado de um quadrado do tabuleiro em milímetros. Contem os **cantos internos**, não os quadrados: um tabuleiro de 10 × 7 quadrados possui 9 × 6 cantos internos.
3. Fotografem 15–25 vistas para calibração e pelo menos 3 outras para validação. O script exige pelo menos 3 imagens de calibração e 2 de validação detectadas; 10 ou mais vistas variadas de calibração são recomendáveis para melhorar a estabilidade.
4. Executem o script, escolham as figuras e preencham [RELATORIO.md](RELATORIO.md), preferencialmente em 2–3 páginas.
5. Publiquem o projeto no Git de vocês e coloquem o link no relatório. Confiram que o relatório e os resultados estão no repositório antes da submissão.

## Aquisição

- Usem um tabuleiro plano e rígido, boa iluminação e fotos nítidas com todo o padrão visível.
- Variem distância, inclinação em dois eixos e posição no enquadramento. Incluam o tabuleiro próximo às bordas, onde a distorção aparece mais.
- Mantenham a mesma câmera, lente, resolução, orientação, zoom e foco. No celular, usem uma lente fixa; evitem alternância automática de lente, modo retrato e zoom digital. Se possível, travem o foco.
- Não redimensionem nem recortem fotografias entre calibração e validação. Os parâmetros intrínsecos dependem da resolução e do recorte.
- Reservem as fotos de validação antes de executar. Elas não entram em `calibrateCamera`.
- Para a dupla: uma pessoa pode cuidar de câmera e coleta; a outra, das medidas e do registro. As duas devem revisar o experimento e o relatório.

Criem `imagens/calibracao/` e `imagens/validacao/` e coloquem os arquivos JPG ou PNG nas pastas correspondentes. HEIC deve ser convertido preservando dimensões e orientação.

## Execução

Requer Python 3.10 ou mais recente. Em uma máquina com acesso à internet:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
mkdir -p imagens/calibracao imagens/validacao
```

**Exemplo de comando:** substituam as dimensões e o tamanho do quadrado pelos valores medidos no tabuleiro de vocês; 9 × 6 e 25 mm abaixo são exemplos.

```bash
python3 calibrar.py \
  --calibracao imagens/calibracao \
  --validacao imagens/validacao \
  --colunas 9 --linhas 6 --quadrado-mm 25 \
  --saida resultados
```

O script refina cantos com `cornerSubPix`, estima parâmetros com `calibrateCamera`, corrige imagens com `undistort`, estima poses de novas vistas com `solvePnP` e projeta pontos com `projectPoints`.

Saídas:

| Arquivo | Conteúdo |
| --- | --- |
| `resultados/resumo.json` | K, distorção, R, t, erros por imagem e imagens rejeitadas |
| `resultados/calibracao.npz` | Parâmetros para reutilização com NumPy |
| `resultados/cantos_*.png` | Conferência da detecção do tabuleiro |
| `resultados/distorcao_*.png` | Foto original à esquerda e corrigida à direita, com linhas de referência |
| `resultados/projecao_*.png` | Cantos observados em verde e projetados em vermelho |
| `resultados/projecoes.csv` | Coordenadas 3D, pixels previstos, pixels observados e erros |

A correção usa uma nova matriz intrínseca e mantém o quadro completo (`alpha=1`); podem surgir bordas pretas. Não há recorte da ROI. As comparações numéricas de projeção são feitas nas **fotografias originais**, com K e os coeficientes de distorção originais. Não misturem pixels da imagem corrigida com esse modelo.

Aqui, “originais” na comparação significa a vista de entrada da calibração, antes de remover a distorção: no conjunto preparado do iPhone, são os PNG de 1134 × 2016. Os pixels medidos nesses PNG não devem ser comparados diretamente aos arquivos de 4536 × 8064.

## Experimento 3D → 2D

O referencial do objeto tem origem no primeiro canto interno retornado pelo detector, X ao longo das colunas, Y ao longo das linhas e Z perpendicular ao tabuleiro. Os cantos possuem coordenadas conhecidas `(coluna × lado, linha × lado, 0)` em milímetros. São pontos no espaço 3D pertencentes ao plano Z = 0.

Em cada foto reservada, o script usa um subconjunto alternado dos cantos para estimar R e t. O subconjunto complementar serve exclusivamente para conferir as projeções. Isso separa pontos de estimação da pose e pontos de avaliação, além de separar as fotos usadas para calibrar das fotos usadas para conferir. A conferência ainda depende das medidas do mesmo tabuleiro e do detector; não constitui uma referência metrológica externa.

Para cada ponto avaliado:

```text
P_camera = R × P_tabuleiro + t
(u_previsto, v_previsto) = projectPoints(P_tabuleiro, rvec, tvec, K, dist)
erro = sqrt((u_previsto - u_observado)² + (v_previsto - v_observado)²)
RMS = sqrt(média(erro²))
```

No relatório, mostrem 5–10 linhas do CSV, cobrindo pelo menos duas imagens, as sobreposições e o RMS da validação. Relatem também o RMS da calibração. Não chamem este último de precisão 3D: a unidade dos erros é **pixel**. Não há um limiar universal de aprovação; discutam foco, cobertura do enquadramento e se a distorção foi visivelmente reduzida.

### Extensão com pontos fora do plano

Para tornar explícita a variação de Z, fixem um objeto de altura conhecida ao tabuleiro e meçam a posição de um ponto identificável no topo. Fotografem-no em pelo menos duas vistas de validação sem ocultar os cantos. Meçam X, Y e Z no mesmo referencial, identifiquem a orientação dos eixos em cada imagem marcada e anotem o pixel observado na foto original. O sinal de Z segue a regra da mão direita a partir dos eixos X e Y: não suponham automaticamente que a altura física tem Z positivo.

O padrão quadriculado pode apresentar ambiguidade de orientação. Para pontos externos, marquem fisicamente um canto e confiram a correspondência dessa marca com a ordem retornada pelo detector em cada vista. Sem isso, a projeção de cantos ainda pode funcionar, mas as coordenadas de um objeto externo podem estar em outro referencial.

Criem um JSON com esta estrutura, usando **as medidas reais**. Os valores ilustrativos abaixo não são resultados:

```json
[
  {"imagem": "validacao01.jpg", "xyz_mm": [50, 75, -30], "uv_px": [640, 420]},
  {"imagem": "validacao02.jpg", "xyz_mm": [50, 75, -30], "uv_px": [615, 390]}
]
```

Acrescentem `--pontos pontos_medidos.json` ao comando. A pose vem dos cantos do tabuleiro; esses pontos externos não entram no ajuste. As previsões e erros aparecem em `pontos_fisicos` no resumo JSON. Incluam as fotografias com o ponto identificado e a tabela no relatório, se realizarem esta extensão.

## Fundamentação e leitura

A matriz intrínseca é `K = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]`, com focais e ponto principal em pixels. R e t transformam coordenadas do tabuleiro para coordenadas da câmera e mudam a cada foto. Sem distorção, a projeção homogênea é `s [u, v, 1]ᵀ = K [R | t] [X, Y, Z, 1]ᵀ`. A matriz 3 × 4 não incorpora a distorção da lente.

No modelo padrão de cinco coeficientes do OpenCV, `(k1, k2, k3)` modelam a distorção radial e `(p1, p2)` a tangencial. Em coordenadas normalizadas, com `r² = x² + y²`:

```text
xd = x(1 + k1 r² + k2 r⁴ + k3 r⁶) + 2 p1 x y + p2(r² + 2 x²)
yd = y(1 + k1 r² + k2 r⁴ + k3 r⁶) + p1(r² + 2 y²) + 2 p2 x y
u = fx xd + cx; v = fy yd + cy
```

Zhang usa um padrão plano em diferentes orientações: as homografias fornecem restrições para a estimação dos parâmetros intrínsecos, seguida de refinamento não linear. O artigo menciona pelo menos duas orientações sob suas condições; na prática, coletem mais fotos variadas para estabilidade. O código usa o modelo convencional de lente do OpenCV. Lentes fisheye podem exigir o módulo específico `cv.fisheye`.

Leituras:

- [OpenCV — Camera Calibration (Python)](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html): cantos, `calibrateCamera`, remoção da distorção e reprojeção.
- [OpenCV — Camera calibration with OpenCV](https://docs.opencv.org/4.x/d4/d94/tutorial_camera_calibration.html): aquisição e fluxo completo.
- [OpenCV — calib3d](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html): referência de `solvePnP` e `projectPoints`.
- `zhang-2000-A_flexible_new_technique_for_camera_calibration.pdf`: Zhang, Z. *A Flexible New Technique for Camera Calibration*. IEEE TPAMI, 22(11), 1330–1334, 2000. DOI: 10.1109/34.888718.
- `10-compVis-camera-calibration.pdf`: slides locais do Prof. Eduardo Todt, UFPR, 2026.

Os PDFs locais foram consultados na preparação. Os tutoriais online devem ser lidos pela dupla: o ambiente de preparação não conseguiu resolver `docs.opencv.org`.

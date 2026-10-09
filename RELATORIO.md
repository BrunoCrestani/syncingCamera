# Calibração de câmera e projeção de pontos 3D

**Dupla:** [nomes]  
**Disciplina:** Visão Computacional — UFPR  
**Data:** [data]  
**Git:** [URL do repositório]

> Modelo de relatório: preencher com medidas e resultados reais; remover esta observação antes de entregar.

## Objetivo e fundamentação

Calibramos [câmera e lente] para estimar a matriz intrínseca K e a distorção da lente, corrigir fotografias e conferir a projeção de pontos com coordenadas conhecidas no espaço 3D.

A calibração com padrão plano em poses variadas se apoia no método de Zhang (2000). K contém as focais fx e fy e o ponto principal (cx, cy), em pixels. Os parâmetros extrínsecos R e t transformam o referencial do tabuleiro para o da câmera. Sem distorção, a projeção é `s [u,v,1]ᵀ = K [R|t] [X,Y,Z,1]ᵀ`. O modelo utilizado inclui distorção radial e tangencial. Consultamos [indicar os tutoriais efetivamente lidos] e os materiais da disciplina.

## Aquisição e procedimento

Usamos [modelo da câmera], lente [identificação], resolução [largura × altura] pixels e [configuração de foco/zoom]. O tabuleiro tinha [colunas × linhas] cantos internos e quadrados de [lado] mm. Coletamos [N] imagens para calibração e [M] outras para validação, variando [inclinação, distância e posição]. O detector aceitou [N válidas] e [M válidas]; [número e motivos] foram rejeitadas.

Detectamos e refinamos os cantos com `findChessboardCorners` e `cornerSubPix`. Estimamos K e a distorção com `calibrateCamera` e removemos a distorção com `getOptimalNewCameraMatrix` e `undistort`. Versão do OpenCV: [versão de resumo.json].

## Matrizes e correção de distorção

Matriz intrínseca K, em pixels:

```text
[ fx   0  cx ]
[  0  fy  cy ]
[  0   0   1 ]
```

Substituir pelos valores numéricos de `resultados/resumo.json`.

Coeficientes `[k1, k2, p1, p2, k3]`: [valores]. RMS da calibração: [valor] px.

Para a imagem [nome], os extrínsecos foram:

```text
R = [valores de resumo.json]
t = [valores] mm
```

![Imagem original à esquerda e corrigida à direita](resultados/distorcao_NOME_DA_FOTO.jpg.png)

**Figura 1.** [Descrever o que se observa nas linhas/bordas reais do tabuleiro, incluindo se a diferença é pequena.] A imagem corrigida utiliza a matriz `K_corrigida`, [valores se necessários], e mantém o enquadramento completo, podendo apresentar bordas pretas.

## Conferência da projeção 3D → 2D

Definimos os cantos do tabuleiro por `P = (coluna × lado, linha × lado, 0)` mm. São pontos 3D no plano Z = 0. Nas imagens reservadas, estimamos a pose com parte dos cantos usando `solvePnP` e projetamos os demais com `projectPoints`, incluindo distorção. Os pontos usados para conferir não foram usados para estimar essa pose. As coordenadas observadas são do detector, na fotografia original.

| Imagem | X, Y, Z (mm) | u, v previstos (px) | u, v observados (px) | Erro (px) |
| --- | --- | --- | --- | --- |
| [foto 1] | [valores] | [valores] | [valores] | [valor] |
| [foto 1] | [valores] | [valores] | [valores] | [valor] |
| [foto 2] | [valores] | [valores] | [valores] | [valor] |
| [foto 2] | [valores] | [valores] | [valores] | [valor] |

Preencher com 5–10 pontos de `projecoes.csv` em pelo menos duas imagens. Erro por ponto: distância euclidiana entre pixel previsto e observado. RMS: raiz da média dos erros ao quadrado.

![Observado em verde e projetado em vermelho](resultados/projecao_NOME_DA_FOTO.jpg.png)

**Figura 2.** Projeções em [foto 1]. Incluir também uma segunda vista ou uma montagem com ambas.

| Vista reservada | Pontos conferidos | Erro médio (px) | RMS (px) | Erro máximo (px) |
| --- | --- | --- | --- | --- |
| [foto 1] | [N] | [valor] | [valor] | [valor] |
| [foto 2] | [N] | [valor] | [valor] | [valor] |

RMS global da validação: [valor de rms_validacao_px] px. [Se fizeram a extensão com Z diferente de zero, descrever as medidas físicas, o referencial e os erros dos pontos externos.]

## Discussão e conclusão

[Explicar se os pontos projetados coincidiram com os observados, comparando calibração e validação, e se a correção reduziu a curvatura observada. Relatar limitações concretas: nitidez, diversidade de poses, planicidade e precisão das medidas do tabuleiro.]

A avaliação mede erro em pixels; não estima diretamente precisão métrica 3D. Os pontos de teste estão [no plano / também fora do plano, se medidos]. A pose e os pixels observados dependem do detector de cantos, o que limita a independência da referência experimental.

## Referências

1. OpenCV. *Camera Calibration (Python).* https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html. Acesso em: [data real da leitura].
2. OpenCV. *Camera calibration with OpenCV.* https://docs.opencv.org/4.x/d4/d94/tutorial_camera_calibration.html. Acesso em: [data real da leitura].
3. Zhang, Z. *A Flexible New Technique for Camera Calibration.* IEEE TPAMI, 22(11), 1330–1334, 2000. DOI: 10.1109/34.888718.
4. Todt, E. *Camera Model and Calibration.* Slides da disciplina, UFPR, 2026.

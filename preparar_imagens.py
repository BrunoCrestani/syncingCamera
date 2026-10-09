"""Prepara as fotos para a calibração: orientação EXIF, redução e separação.

Todas as fotos recebem a mesma rotação EXIF e o mesmo fator de redução, sem
recorte. Assim, K vale para a resolução preparada. As fotos de validação são
escolhidas antes da calibração e não entram em calibrateCamera.
"""

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageOps

EXTENSOES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
# Vistas reservadas antes de calibrar, escolhidas por variarem a inclinação.
VALIDACAO_PADRAO = ["IMG_8157", "IMG_8165", "IMG_8171", "IMG_8174"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path("imagens"))
    parser.add_argument("--saida", type=Path, default=Path("dados_preparados"))
    parser.add_argument("--fator", type=int, default=4, help="Divide largura e altura por este fator")
    parser.add_argument("--validacao", nargs="+", default=VALIDACAO_PADRAO,
                        help="Nomes (sem extensão) das fotos reservadas para validar")
    args = parser.parse_args()

    paths = sorted(p for p in args.entrada.iterdir() if p.suffix.lower() in EXTENSOES)
    if not paths:
        raise SystemExit(f"Nenhuma foto em {args.entrada}")
    faltando = set(args.validacao) - {p.stem for p in paths}
    if faltando:
        raise SystemExit(f"Fotos de validação inexistentes: {sorted(faltando)}")

    entrada = args.entrada.resolve()
    if args.saida.resolve() in (entrada, *entrada.parents):
        raise SystemExit("A saída não pode ser a pasta de entrada nem conter essa pasta.")
    if args.saida.exists():
        shutil.rmtree(args.saida)
    inventario = []
    tamanhos = set()
    for path in paths:
        with Image.open(path) as image:
            exif = image.getexif()
            extra = exif.get_ifd(34665)
            oriented = ImageOps.exif_transpose(image).convert("RGB")
        original = oriented.size
        target = (original[0] // args.fator, original[1] // args.fator)
        tamanhos.add(target)
        oriented = oriented.resize(target, Image.Resampling.LANCZOS)
        conjunto = "validacao" if path.stem in args.validacao else "calibracao"
        dest = args.saida / conjunto / f"{path.stem}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        oriented.save(dest)
        inventario.append({
            "arquivo": str(path), "preparado": str(dest), "conjunto": conjunto,
            "camera": exif.get(272), "lente": extra.get(42036),
            "focal_mm": float(extra[37386]) if 37386 in extra else None,
            "focal_35mm": extra.get(41989),
            "resolucao_original": list(original), "resolucao_preparada": list(target),
        })
        print(f"{conjunto:10s} {dest.name} {target[0]}x{target[1]}")

    if len(tamanhos) != 1:
        raise SystemExit(f"As fotos têm resoluções diferentes: {sorted(tamanhos)}")
    (args.saida / "inventario.json").write_text(
        json.dumps(inventario, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

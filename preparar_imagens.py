"""Audita os arquivos originais e prepara grupos separados para calibração."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path("imagens"))
    parser.add_argument("--saida", type=Path, default=Path("dados_preparados"))
    args = parser.parse_args()
    if args.saida.exists():
        raise SystemExit(f"A saída já existe: {args.saida}. Use outra pasta para preservar os arquivos.")
    paths = sorted(p for p in args.entrada.iterdir() if p.is_file())
    groups = defaultdict(list)
    records = []
    hashes = {}
    for path in paths:
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if content_hash in hashes:
            records.append({"arquivo": str(path), "sha256": content_hash, "duplicata_de": hashes[content_hash]})
            continue
        try:
            with Image.open(path) as image:
                exif = image.getexif()
                extra = exif.get_ifd(34665) if 34665 in exif else {}
                oriented = ImageOps.exif_transpose(image)
                record = {
                    "arquivo": str(path), "sha256": content_hash, "formato_real": image.format,
                    "resolucao_original": list(image.size), "orientacao_exif": exif.get(274),
                    "camera": exif.get(272), "fabricante": exif.get(271),
                    "lente": extra.get(42036), "focal_mm": float(extra[37386]) if 37386 in extra else None,
                    "data_original": extra.get(36867),
                }
                if record["camera"]:
                    camera_id = str(record["camera"]).replace(" ", "_")
                    # Grupo identificado por câmera, lente e resolução, sem misturar os JPG sem EXIF.
                    lens_id = hashlib.sha256(str(record["lente"]).encode()).hexdigest()[:6]
                    group = f"{camera_id}_{lens_id}_{oriented.width}x{oriented.height}"
                else:
                    group = f"jpg_sem_camera_identificada_{oriented.width}x{oriented.height}"
                record["grupo"] = group
                groups[group].append((path, record))
                records.append(record)
                hashes[content_hash] = str(path)
        except (OSError, ValueError) as exc:
            records.append({"arquivo": str(path), "erro": str(exc)})

    args.saida.mkdir(parents=True)
    output_groups = []
    for group, entries in sorted(groups.items()):
        # As vistas do iPhone abaixo foram escolhidas visualmente antes de calibrar.
        preferred = {"IMG_8157.DNG", "IMG_8165.DNG", "IMG_8171.DNG", "IMG_8174.DNG"}
        if all(entry[1]["camera"] == "iPhone 16 Pro" for entry in entries) and preferred.issubset(
                {p.name for p, _ in entries}):
            validation = preferred
        else:
            shuffled = list(entries)
            random.Random(42).shuffle(shuffled)
            validation = {p.name for p, _ in shuffled[:max(2, round(len(entries) * 0.2))]}
        thumbnails = []
        for index, (path, record) in enumerate(entries, 1):
            subset = "validacao" if path.name in validation else "calibracao"
            out_folder = args.saida / group / subset
            out_folder.mkdir(parents=True, exist_ok=True)
            with Image.open(path) as image:
                oriented = ImageOps.exif_transpose(image).convert("RGB")
                if record["camera"] == "iPhone 16 Pro":
                    # Redução uniforme de 1/4, sem recorte, em todas as vistas deste conjunto.
                    target = (oriented.width // 4, oriented.height // 4)
                    oriented = oriented.resize(target, Image.Resampling.LANCZOS)
                else:
                    target = oriented.size
                dest = out_folder / f"{index:02d}_{path.stem.replace(' (2)', '')}.png"
                oriented.save(dest)
                thumb = oriented.copy()
                thumb.thumbnail((230, 170))
                thumbnails.append((thumb, dest.name, subset))
                record.update({"arquivo_preparado": str(dest), "conjunto": subset,
                               "resolucao_preparada": list(target),
                               "escala_x": target[0] / ImageOps.exif_transpose(image).width,
                               "escala_y": target[1] / ImageOps.exif_transpose(image).height})
        sheet = Image.new("RGB", (1200, 205 * ((len(thumbnails) + 4) // 5)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, (thumb, name, subset) in enumerate(thumbnails):
            x = i % 5 * 240
            y = i // 5 * 205
            sheet.paste(thumb, (x, y))
            draw.text((x + 3, y + 174), f"{name[:17]} {subset}", fill="black")
        sheet.save(args.saida / group / "contato.jpg")
        counts = Counter(record["conjunto"] for _, record in entries)
        description = {"grupo": group, "contagem": dict(counts),
                       "resolucao_preparada": entries[0][1]["resolucao_preparada"],
                       "identidade_camera_confirmada_por_exif": entries[0][1]["camera"] is not None}
        output_groups.append(description)
        print(group, dict(counts), description["resolucao_preparada"])
    manifest = {"arquivos_recebidos": len(paths), "arquivos_unicos_legiveis": len(hashes),
                "duplicatas": sum("duplicata_de" in r for r in records),
                "grupos": output_groups, "arquivos": records}
    (args.saida / "inventario.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Inventário: {args.saida / 'inventario.json'}")


if __name__ == "__main__":
    main()

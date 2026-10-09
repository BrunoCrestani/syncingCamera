"""Calibração, correção de distorção e validação em imagens reservadas."""

import argparse
import csv
import json
import math
from pathlib import Path


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibracao", required=True, type=Path,
                        help="Pasta das fotografias usadas para calibrar")
    parser.add_argument("--validacao", required=True, type=Path,
                        help="Pasta de outras fotografias, reservadas para validar")
    parser.add_argument("--colunas", required=True, type=int, help="Cantos internos por linha")
    parser.add_argument("--linhas", required=True, type=int, help="Cantos internos por coluna")
    scale = parser.add_mutually_exclusive_group(required=True)
    scale.add_argument("--quadrado-mm", type=float, help="Lado medido de um quadrado, em mm")
    scale.add_argument("--quadrado-unidades", action="store_true",
                       help="Usa lado 1; posições 3D em unidades de quadrado, sem escala métrica")
    parser.add_argument("--saida", type=Path, default=Path("resultados"))
    parser.add_argument("--modelo-distorcao", choices=["completo", "radial1"], default="completo",
                        help="radial1 estima k1, p1, p2 e fixa k2 e k3 em zero")
    parser.add_argument("--pontos", type=Path,
                        help="JSON opcional com pontos físicos medidos fora do plano")
    args = parser.parse_args()
    if args.colunas < 3 or args.linhas < 3 or (args.quadrado_mm is not None and
            (not math.isfinite(args.quadrado_mm) or args.quadrado_mm <= 0)):
        parser.error("Use pelo menos 3 × 3 cantos internos e quadrado com lado positivo.")
    if args.calibracao.resolve() == args.validacao.resolve():
        parser.error("As pastas de calibração e validação devem ser distintas.")
    if args.pontos and args.quadrado_unidades:
        parser.error("Para --pontos com xyz_mm, informe a medida real em --quadrado-mm.")
    return args


def main():
    args = arguments()
    try:
        import cv2 as cv
        import numpy as np
    except ImportError as exc:
        raise SystemExit("Instale as dependências: python3 -m pip install -r requirements.txt") from exc

    pattern = (args.colunas, args.linhas)
    square_size = args.quadrado_mm if args.quadrado_mm is not None else 1.0
    unit = "mm" if args.quadrado_mm is not None else "quadrados"
    obj = np.zeros((args.colunas * args.linhas, 3), np.float32)
    obj[:, :2] = np.mgrid[0:args.colunas, 0:args.linhas].T.reshape(-1, 2)
    obj *= square_size
    args.saida.mkdir(parents=True, exist_ok=True)
    rejected = []
    detections = []
    image_size = None

    def write_image(path, image):
        if not cv.imwrite(str(path), image):
            raise RuntimeError(f"Não foi possível salvar {path}")

    def read_views(folder, group):
        nonlocal image_size
        if not folder.is_dir():
            raise ValueError(f"Pasta inexistente: {folder}")
        paths = sorted(p for p in folder.iterdir()
                       if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})
        if not paths:
            raise ValueError(f"Nenhuma fotografia em {folder}")
        views = []
        for path in paths:
            image = cv.imread(str(path))
            if image is None:
                rejected.append({"imagem": str(path), "motivo": "Não foi possível ler"})
                continue
            size = (image.shape[1], image.shape[0])
            if image_size is None:
                image_size = size
            if size != image_size:
                raise ValueError(f"Resolução diferente em {path}: {size}, esperada {image_size}")
            gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
            found, corners = cv.findChessboardCorners(
                gray, pattern, cv.CALIB_CB_ADAPTIVE_THRESH | cv.CALIB_CB_NORMALIZE_IMAGE)
            method = "classico"
            if not found:
                # O detector SB pode recuperar tabuleiros inclinados que o clássico não detecta.
                found, corners = cv.findChessboardCornersSB(gray, pattern, cv.CALIB_CB_NORMALIZE_IMAGE)
                method = "SB"
            if not found:
                enhanced = cv.createCLAHE(clipLimit=2, tileGridSize=(8, 8)).apply(gray)
                found, corners = cv.findChessboardCornersSB(
                    enhanced, pattern, cv.CALIB_CB_NORMALIZE_IMAGE | cv.CALIB_CB_EXHAUSTIVE | cv.CALIB_CB_ACCURACY)
                method = "SB_com_CLAHE"
            if not found:
                rejected.append({"imagem": str(path), "motivo": "Tabuleiro não detectado"})
                continue
            corners = cv.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                (cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            marked = image.copy()
            cv.drawChessboardCorners(marked, pattern, corners, True)
            write_image(args.saida / f"cantos_{group}_{path.name}.png", marked)
            views.append((path, corners))
            detections.append({"imagem": str(path), "conjunto": group, "metodo": method})
            print(f"Cantos detectados ({method}): {path.name}", flush=True)
        return views

    calibration = read_views(args.calibracao, "calibracao")
    validation = read_views(args.validacao, "validacao")
    if len(calibration) < 3:
        raise ValueError(f"Apenas {len(calibration)} fotos válidas para calibrar. São necessárias pelo menos 3 poses distintas.")
    if len(validation) < 2:
        raise ValueError("Reserve pelo menos 2 fotos válidas para conferir a projeção.")
    # Evita reutilização acidental dos mesmos arquivos em pastas diferentes.
    import hashlib
    calibration_hashes = {hashlib.sha256(p.read_bytes()).digest() for p, _ in calibration}
    if any(hashlib.sha256(p.read_bytes()).digest() in calibration_hashes for p, _ in validation):
        raise ValueError("Uma imagem de validação é uma cópia de uma imagem de calibração.")

    flags = (cv.CALIB_FIX_K2 | cv.CALIB_FIX_K3) if args.modelo_distorcao == "radial1" else 0
    rms, matrix, distortion, rvecs, tvecs = cv.calibrateCamera(
        [obj.copy() for _ in calibration], [c for _, c in calibration], image_size, None, None, flags=flags)
    new_matrix, roi = cv.getOptimalNewCameraMatrix(matrix, distortion, image_size, 1, image_size)
    np.savez(args.saida / "calibracao.npz", K=matrix, dist=distortion, K_corrigida=new_matrix,
             tamanho_imagem=image_size, rvecs=np.asarray(rvecs), tvecs=np.asarray(tvecs))
    summary = {
        "opencv": cv.__version__, "resolucao_px": list(image_size),
        "cantos_internos": list(pattern), "quadrado_mm": args.quadrado_mm,
        "unidade_objeto": unit, "lado_quadrado": square_size,
        "modelo_distorcao": args.modelo_distorcao, "flags_calibracao": int(flags),
        "K": matrix.tolist(), "distorcao_k1_k2_p1_p2_k3": distortion.ravel().tolist(),
        "K_corrigida": new_matrix.tolist(), "roi": list(map(int, roi)),
        "rms_calibracao_px": float(rms), "calibracao": [], "validacao": [],
        "imagens_rejeitadas": rejected,
        "deteccoes": detections,
    }
    for (path, measured), rvec, tvec in zip(calibration, rvecs, tvecs):
        predicted, _ = cv.projectPoints(obj, rvec, tvec, matrix, distortion)
        errors = np.linalg.norm(predicted.reshape(-1, 2) - measured.reshape(-1, 2), axis=1)
        rotation, _ = cv.Rodrigues(rvec)
        summary["calibracao"].append({
            "imagem": str(path), "rms_px": float(np.sqrt(np.mean(errors ** 2))),
            "R": rotation.tolist(), f"t_{unit}": tvec.ravel().tolist(),
            "P_sem_distorcao": (matrix @ np.column_stack((rotation, tvec))).tolist(),
        })

    # Intercala cantos para a pose e cantos para avaliar a projeção.
    indices = np.arange(len(obj))
    pose_indices = indices[(indices % args.colunas + indices // args.colunas) % 2 == 0]
    test_indices = indices[(indices % args.colunas + indices // args.colunas) % 2 == 1]
    rows = []
    poses = {}
    all_errors = []
    for path, measured in validation:
        ok, rvec, tvec = cv.solvePnP(obj[pose_indices], measured[pose_indices], matrix, distortion)
        if not ok:
            raise ValueError(f"Não foi possível estimar a pose: {path}")
        poses[path.name] = (rvec, tvec)
        predicted, _ = cv.projectPoints(obj, rvec, tvec, matrix, distortion)
        predicted = predicted.reshape(-1, 2)
        measured = measured.reshape(-1, 2)
        errors = np.linalg.norm(predicted[test_indices] - measured[test_indices], axis=1)
        all_errors.extend(errors.tolist())
        rotation, _ = cv.Rodrigues(rvec)
        summary["validacao"].append({
            "imagem": str(path), "n_pontos_pose": len(pose_indices), "n_pontos_teste": len(test_indices),
            "erro_medio_px": float(errors.mean()), "rms_px": float(np.sqrt(np.mean(errors ** 2))),
            "erro_maximo_px": float(errors.max()), "R": rotation.tolist(), f"t_{unit}": tvec.ravel().tolist(),
        })
        image = cv.imread(str(path))
        overlay = image.copy()
        for index in test_indices:
            x, y, z = obj[index]
            u, v = predicted[index]
            um, vm = measured[index]
            rows.append([path.name, int(index), float(x), float(y), float(z), float(u), float(v),
                         float(um), float(vm), float(np.linalg.norm(predicted[index] - measured[index]))])
            observed = tuple(np.rint(measured[index]).astype(int))
            projected = tuple(np.rint(predicted[index]).astype(int))
            cv.circle(overlay, observed, 6, (0, 255, 0), 2)
            cv.drawMarker(overlay, projected, (0, 0, 255), cv.MARKER_CROSS, 10, 2)
            cv.line(overlay, observed, projected, (255, 0, 0), 1)
        cv.putText(overlay, "Verde: observado | vermelho: projetado", (20, 35),
                   cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        write_image(args.saida / f"projecao_{path.name}.png", overlay)
        corrected = cv.undistort(image, matrix, distortion, None, new_matrix)
        # Não recorta a ROI: pixels continuam no referencial de K_corrigida.
        comparison = np.hstack((image, corrected))
        for x in range(0, comparison.shape[1], 80):
            cv.line(comparison, (x, 0), (x, comparison.shape[0] - 1), (0, 255, 255), 1)
        write_image(args.saida / f"distorcao_{path.name}.png", comparison)

    with (args.saida / "projecoes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["imagem", "ponto", f"X_{unit}", f"Y_{unit}", f"Z_{unit}", "u_previsto_px", "v_previsto_px",
                         "u_observado_px", "v_observado_px", "erro_px"])
        writer.writerows(rows)
    summary["rms_validacao_px"] = float(np.sqrt(np.mean(np.square(all_errors))))

    if args.pontos:
        # Coordenadas físicas no referencial do tabuleiro; uv na foto ORIGINAL.
        manual = json.loads(args.pontos.read_text(encoding="utf-8"))
        if not isinstance(manual, list) or not manual:
            raise ValueError("O JSON de pontos deve conter uma lista não vazia.")
        records = []
        for item in manual:
            if item["imagem"] not in poses:
                raise ValueError(f"Imagem não validada: {item['imagem']}")
            xyz = np.asarray(item["xyz_mm"], dtype=np.float64)
            uv = np.asarray(item["uv_px"], dtype=np.float64)
            if xyz.shape != (3,) or uv.shape != (2,) or not (np.isfinite(xyz).all() and np.isfinite(uv).all()):
                raise ValueError("Use xyz_mm com 3 números finitos e uv_px com 2 números finitos.")
            rvec, tvec = poses[item["imagem"]]
            rotation, _ = cv.Rodrigues(rvec)
            if (rotation @ xyz + tvec.ravel())[2] <= 0:
                raise ValueError("O ponto está atrás da câmera; confira o referencial.")
            projected, _ = cv.projectPoints(xyz.reshape(1, 3), rvec, tvec, matrix, distortion)
            projected = projected.reshape(2)
            records.append({**item, "uv_previsto_px": projected.tolist(),
                            "erro_px": float(np.linalg.norm(projected - uv))})
        summary["pontos_fisicos"] = records
    (args.saida / "resumo.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RMS de calibração: {rms:.4f} px")
    print(f"RMS de validação: {summary['rms_validacao_px']:.4f} px")
    print(f"Matriz intrínseca K:\n{matrix}")
    print(f"Distorção [k1, k2, p1, p2, k3]: {distortion.ravel()}")
    print(f"Arquivos gravados em: {args.saida.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        raise SystemExit(f"Erro: {exc}") from exc

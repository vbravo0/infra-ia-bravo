#!/usr/bin/env python3
"""Extrae 1.000 CVEs estratificados del segundo semestre de 2024 desde all_cves.zip (REQ-07)."""

import io
import json
import zipfile
import pandas as pd

ZIP_PATH = "/media/vub/25f61be1-310a-49c4-bce7-a8bc793230e32/vub/postgrados/unlu/diplomado-ia/curso2-infra/propuesta/data/all_cves.zip"
OUT_CSV = "/media/vub/25f61be1-310a-49c4-bce7-a8bc793230e32/vub/postgrados/unlu/test-llm-cve/data/sample_1000.csv"

# Objetivos estratificados exactos acordados en la propuesta con Petrocelli:
# LOW: ~1.6% (~16), MEDIUM: ~45% (450), HIGH: ~37% (370), CRITICAL: ~16.4% (164)
TARGETS = {
    "LOW": 16,
    "MEDIUM": 450,
    "HIGH": 370,
    "CRITICAL": 164,
}

def extract_sample_1000():
    print(f"Leyendo {ZIP_PATH}...")
    collected = {"LOW": [], "MEDIUM": [], "HIGH": [], "CRITICAL": []}
    
    with zipfile.ZipFile(ZIP_PATH, "r") as outer:
        with outer.open("cves.zip") as nested:
            with zipfile.ZipFile(io.BytesIO(nested.read()), "r") as inner:
                for name in inner.namelist():
                    if not (name.endswith(".json") and "/2024/" in name):
                        continue
                    
                    # Si ya completamos todos los cupos, cortamos
                    if all(len(v) >= TARGETS[k] for k, v in collected.items()):
                        break
                    
                    try:
                        with inner.open(name) as f:
                            data = json.load(f)
                            
                        meta = data.get("cveMetadata", {})
                        cve_id = meta.get("cveId")
                        date_pub = meta.get("datePublished", "")
                        
                        # Particion temporal estricta: 2do semestre 2024 (desde julio 2024 en adelante)
                        if not (date_pub.startswith("2024-07") or date_pub.startswith("2024-08") or
                                date_pub.startswith("2024-09") or date_pub.startswith("2024-10") or
                                date_pub.startswith("2024-11") or date_pub.startswith("2024-12")):
                            continue
                            
                        cna = data.get("containers", {}).get("cna", {})
                        
                        # Obtener descripcion
                        descs = cna.get("descriptions", [])
                        desc_text = ""
                        for d in descs:
                            if d.get("lang") in ("en", "en-US", ""):
                                desc_text = d.get("value", "")
                                break
                        if not desc_text and descs:
                            desc_text = descs[0].get("value", "")
                        if not desc_text or len(desc_text.strip()) < 15:
                            continue
                            
                        # Obtener CVSS 3.1 o CVSS 3.0
                        metrics = cna.get("metrics", [])
                        score_v3 = None
                        sev = None
                        for m in metrics:
                            v3 = m.get("cvssV3_1") or m.get("cvssV3_0")
                            if v3:
                                score_v3 = v3.get("baseScore")
                                sev = (v3.get("baseSeverity") or "").upper()
                                break
                                
                        if not sev or sev not in TARGETS:
                            continue
                            
                        # Obtener CWE si existe
                        cwe_id = "UNKNOWN"
                        problem_types = cna.get("problemTypes", [])
                        for pt in problem_types:
                            for desc in pt.get("descriptions", []):
                                if desc.get("cweId"):
                                    cwe_id = desc.get("cweId")
                                    break
                                    
                        # Verificar si todavia necesitamos de esta clase
                        if len(collected[sev]) < TARGETS[sev]:
                            collected[sev].append({
                                "CVE-ID": cve_id,
                                "CVSS-V4": "",
                                "CVSS-V3": score_v3,
                                "CVSS-V2": "",
                                "SEVERITY": sev,
                                "DESCRIPTION": desc_text,
                                "CWE-ID": cwe_id,
                            })
                            print(f"[{sev}] {len(collected[sev])}/{TARGETS[sev]} -> {cve_id}")
                    except Exception:
                        continue

    # Unir todo y asignar ID secuencial
    all_rows = []
    current_id = 260001
    for sev_name in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        for item in collected[sev_name]:
            item["ID"] = current_id
            current_id += 1
            all_rows.append(item)
            
    df = pd.DataFrame(all_rows)
    # Reordenar columnas exactas
    df = df[["ID", "CVE-ID", "CVSS-V4", "CVSS-V3", "CVSS-V2", "SEVERITY", "DESCRIPTION", "CWE-ID"]]
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nListo: generado {OUT_CSV} con {len(df)} filas.")
    print("Distribucion:")
    print(df["SEVERITY"].value_counts())

if __name__ == "__main__":
    extract_sample_1000()

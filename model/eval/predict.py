"""Script CLI para generar predicciones batch de un modelo y guardarlas en CSV.

Separa la inferencia pura del computo de metricas o evaluacion.

Uso:
    python model/eval/predict.py --model tfidf --data data/sample_1000.csv --output data/predictions_tfidf.csv
    python model/eval/predict.py --model llm --data data/sample_1000.csv --output data/predictions_llm_v1.csv
"""

from __future__ import annotations

import argparse
import sys
import pandas as pd
from eval.adapters import EvaluatableModel, OllamaEvaluator, TfidfEvaluator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generador batch de predicciones en CSV"
    )
    parser.add_argument(
        "--model",
        choices=["tfidf", "llm"],
        default="tfidf",
        help="Motor de inferencia a ejecutar",
    )
    parser.add_argument(
        "--data",
        default="data/sample_1000.csv",
        help="CSV de entrada con descripciones (debe contener columna DESCRIPTION)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Ruta al CSV de salida donde se guardaran las predicciones",
    )
    parser.add_argument(
        "--model-path",
        default="model.joblib",
        help="Ruta al artefacto .joblib (para tfidf)",
    )
    parser.add_argument(
        "--prompt",
        default="model/prompts/system_prompt.txt",
        help="Ruta al archivo con el prompt (para llm)",
    )

    args = parser.parse_args()

    print(f"Cargando dataset desde {args.data}...")
    df = pd.read_csv(args.data)
    if "DESCRIPTION" not in df.columns:
        print(
            "❌ Error: El dataset debe tener una columna 'DESCRIPTION'.",
            file=sys.stderr,
        )
        sys.exit(1)

    evaluator: EvaluatableModel
    if args.model == "tfidf":
        evaluator = TfidfEvaluator(model_path=args.model_path)
    else:
        evaluator = OllamaEvaluator(
            prompt_path=args.prompt,
            checkpoint_path=args.output,
        )

    print(f"Ejecutando predicciones con motor: {args.model.upper()}...")
    predictions = evaluator.predict_batch(df["DESCRIPTION"].tolist())

    out_df = pd.DataFrame(
        {
            "CVE-ID": df["CVE-ID"] if "CVE-ID" in df.columns else range(len(df)),
            "PREDICTION": predictions,
        }
    )
    out_df.to_csv(args.output, index=False)
    print(
        f"✅ Predicciones guardadas exitosamente en {args.output} ({len(predictions)} filas)."
    )


if __name__ == "__main__":
    main()

"""
entrenar.py - Evalúa el modelo NLP y muestra métricas (ideal para el póster de la ExpoTécnica).

Ejecutar:  python entrenar.py
"""

from collections import Counter

import config
from base_conocimiento import BaseConocimiento
from nlp.clasificador import ClasificadorIntenciones
from nlp.procesamiento import USA_NLTK, tokenizar

FRASES_PRUEBA = [
    "mi compu no quiere arrancar",
    "el wifi no conecta",
    "se me tilda la notebook",
    "creo que tengo un troyano",
    "que temperatura marca el sensor",
    "como veo mi ip",
    "quien gano el partido",
]


def main():
    db = BaseConocimiento(config.DB_PATH)
    if db.esta_vacia():
        db.cargar_desde_json(config.INTENCIONES_PATH)
    ejemplos = db.ejemplos_entrenamiento()
    por_intencion = Counter(tag for _, tag in ejemplos)

    print("=" * 60)
    print(" TECHMIND Nexus - Evaluación del modelo TF-IDF + SVM")
    print("=" * 60)
    print(f"Stemmer: {'NLTK Snowball (español)' if USA_NLTK else 'propio (instalá nltk para mejorar)'}")
    print(f"Frases de entrenamiento: {len(ejemplos)}  |  Intenciones: {len(por_intencion)}\n")
    for tag, cantidad in sorted(por_intencion.items(), key=lambda par: -par[1]):
        print(f"  {tag:22} {'█' * cantidad} {cantidad}")

    print("\nEjemplo de tokenización:")
    print(f"  'Mi PC no enciende!' -> {tokenizar('Mi PC no enciende!')}")

    clasificador = ClasificadorIntenciones(config.UMBRAL_CONFIANZA)
    media, desvio = clasificador.evaluar(ejemplos)
    print(f"\nPrecisión con validación cruzada (3 pliegues): {media:.1%} ± {desvio:.1%}")
    print("(el modelo se prueba con frases que NO vio al entrenar)")

    clasificador.entrenar(ejemplos)
    print("\nPruebas con frases nuevas:")
    for frase in FRASES_PRUEBA:
        r = clasificador.predecir(frase)
        print(f"  {frase:35} -> {str(r['intencion']):20} {r['confianza']:.0%}")


if __name__ == "__main__":
    main()

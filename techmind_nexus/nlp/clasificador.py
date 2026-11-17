"""
clasificador.py - Clasificador de intenciones con TF-IDF + SVM.

¿Cómo funciona?
  1. TF-IDF convierte cada frase en un vector de números: cada palabra recibe un
     peso alto si aparece mucho en la frase pero poco en el resto de las frases.
  2. Usamos DOS vectorizadores combinados (FeatureUnion):
       - por palabras (raíces + bigramas)  -> entiende el significado
       - por caracteres (trozos de 3 a 5)  -> tolera errores de tipeo ("conputadora")
  3. Un SVM (Support Vector Machine) lineal busca los "hiperplanos" que mejor
     separan los vectores de cada intención.
  4. El SVM solo da "distancias" al hiperplano, no probabilidades. Por eso lo
     envolvemos en CalibratedClassifierCV, que aprende a convertir esas
     distancias en probabilidades (0 a 1). Esa probabilidad es la "confianza".
"""

from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from nlp.procesamiento import normalizar, tokenizar


class ClasificadorIntenciones:
    """Envuelve el pipeline TF-IDF + SVM con métodos simples de usar."""

    def __init__(self, umbral=0.30):
        self.umbral = umbral
        self.modelo = None
        self.etiquetas = []

    @staticmethod
    def _crear_pipeline():
        """Arma el pipeline de scikit-learn (función interna reutilizable)."""
        vectorizador = FeatureUnion([
            ("palabras", TfidfVectorizer(analyzer=tokenizar, sublinear_tf=True)),
            ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                           preprocessor=normalizar, sublinear_tf=True)),
        ])
        svm = CalibratedClassifierCV(LinearSVC(C=1.0), cv=3)  # SVM lineal + probabilidades
        return Pipeline([("tfidf", vectorizador), ("svm", svm)])

    @staticmethod
    def _preparar_datos(ejemplos):
        """Convierte [(frase, tag), ...] en dos listas X (frases) e y (tags)."""
        frases = [frase for frase, _ in ejemplos]
        tags = [tag for _, tag in ejemplos]
        return frases, tags

    def entrenar(self, ejemplos):
        """
        Entrena el modelo.

        Parámetros:
            ejemplos (list[tuple[str, str]]): pares (frase, intención).
        Retorna:
            int: cantidad de frases usadas.
        """
        frases, tags = self._preparar_datos(ejemplos)
        if len(set(tags)) < 2:
            raise ValueError("Se necesitan al menos 2 intenciones distintas para entrenar.")
        poco = [t for t in set(tags) if tags.count(t) < 3]
        if poco:
            raise ValueError(f"Cada intención necesita al menos 3 ejemplos. Faltan en: {poco}")
        self.modelo = self._crear_pipeline()
        self.modelo.fit(frases, tags)
        self.etiquetas = list(self.modelo.classes_)
        return len(frases)

    def predecir(self, texto, top=3):
        """
        Clasifica una frase.

        Retorna:
            dict con:
              intencion  (str | None): la intención ganadora, o None si no alcanza el umbral
              confianza  (float): probabilidad de la ganadora (0 a 1)
              candidatas (list[tuple[str, float]]): las 'top' más probables
        """
        if self.modelo is None:
            raise RuntimeError("El modelo no está entrenado.")
        if not normalizar(texto):
            return {"intencion": None, "confianza": 0.0, "candidatas": []}

        probabilidades = self.modelo.predict_proba([texto])[0]
        pares = zip(self.etiquetas, probabilidades)
        candidatas = sorted(pares, key=lambda par: par[1], reverse=True)[:top]  # lambda como key
        mejor, confianza = candidatas[0]
        return {
            "intencion": mejor if confianza >= self.umbral else None,
            "confianza": float(confianza),
            "candidatas": [(t, float(p)) for t, p in candidatas],
        }

    def evaluar(self, ejemplos, pliegues=3):
        """
        Validación cruzada: entrena y prueba con distintas partes de los datos.
        Sirve para mostrar en la ExpoTécnica qué tan preciso es el modelo.

        Retorna:
            tuple(float, float): (precisión promedio, desvío)
        """
        frases, tags = self._preparar_datos(ejemplos)
        cv = StratifiedKFold(n_splits=pliegues, shuffle=True, random_state=42)
        puntajes = cross_val_score(self._crear_pipeline(), frases, tags, cv=cv)
        return float(puntajes.mean()), float(puntajes.std())

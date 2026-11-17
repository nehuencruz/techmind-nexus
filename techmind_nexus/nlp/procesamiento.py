"""
procesamiento.py - Limpieza y tokenización de texto en español.

Pipeline:  texto -> normalizar() -> tokenizar() -> lista de raíces
Ejemplo:   "¡Mi PC no enciende!" -> ["pc", "no", "enciend"]

Usa el stemmer Snowball de NLTK si está instalado. Si no, usa un stemmer
simple propio para que el proyecto funcione igual.
"""

import re
import unicodedata

try:
    from nltk.stem.snowball import SnowballStemmer  # no necesita descargas
    _snowball = SnowballStemmer("spanish")
    USA_NLTK = True
except ImportError:  # pragma: no cover - depende del entorno
    _snowball = None
    USA_NLTK = False


# Palabras vacías (stopwords). Lista propia para no depender de nltk.download().
# OJO: "no" NO está, porque cambia el sentido ("no enciende", "no tengo internet").
STOPWORDS = {
    "a", "al", "algo", "ante", "con", "como", "cual", "de", "del", "el", "en", "es",
    "esa", "ese", "eso", "esta", "este", "esto", "ha", "hay", "la", "las", "le", "les",
    "lo", "los", "me", "mi", "mis", "muy", "o", "para", "pero", "por", "que", "se",
    "si", "sin", "su", "sus", "te", "tu", "tus", "un", "una", "uno", "y", "ya", "yo",
    "mucho", "mas", "tengo", "tiene", "estoy", "anda", "hace",
}
# "sin" se elimina porque el dato útil está en la palabra que sigue
# ("sin internet" -> "internet"). Cambiar esta lista mejora o empeora el modelo:
# ¡buen experimento para la ExpoTécnica!


def quitar_acentos(texto):
    """Convierte 'canción' en 'cancion' (también sirve para la LCD, que no tiene tildes)."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar(texto):
    """
    Pasa a minúsculas, quita tildes, signos y espacios repetidos.

    Parámetros:
        texto (str): frase original del usuario.
    Retorna:
        str: frase limpia.
    """
    texto = quitar_acentos(texto.lower())
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)   # deja solo letras, números y espacios
    texto = re.sub(r"(.)\1{2,}", r"\1", texto)     # "holaaaa" -> "hola"
    return re.sub(r"\s+", " ", texto).strip()


def _stem_simple(palabra):
    """Stemmer de respaldo: recorta sufijos comunes del español."""
    sufijos = ("aciones", "iciones", "amiento", "imiento", "mente", "acion", "icion",
               "ando", "iendo", "ados", "idos", "ado", "ido", "ar", "er", "ir",
               "es", "as", "os", "a", "e", "o", "s")
    for suf in sufijos:
        if palabra.endswith(suf) and len(palabra) - len(suf) >= 3:
            return palabra[: -len(suf)]
    return palabra


def raiz(palabra):
    """Devuelve la raíz (stem) de una palabra: 'enciende' -> 'enciend'."""
    return _snowball.stem(palabra) if USA_NLTK else _stem_simple(palabra)


def tokenizar(texto):
    """
    Divide la frase en palabras, saca stopwords y devuelve raíces.

    Esta función se le pasa a TfidfVectorizer como 'analyzer'.
    """
    palabras = normalizar(texto).split()
    tokens = [raiz(p) for p in palabras if p not in STOPWORDS]
    # Agregamos bigramas ("no_enciend") para capturar frases de dos palabras
    bigramas = [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    return tokens + bigramas

"""
consola.py - Probar TECHMIND Nexus desde la terminal, sin navegador ni placas.

Ejecutar:  python consola.py
Salir:     escribí "salir"
"""

import config
from chatbot import Chatbot


def main():
    bot = Chatbot(ruta_db=config.DB_PATH)
    print("\n=== TECHMIND Nexus (modo consola) ===  escribí 'salir' para terminar\n")
    while True:
        try:
            mensaje = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if mensaje.lower() == "salir":
            break
        r = bot.procesar("consola", mensaje)
        print(f"\nBot [{r['titulo']} · {r['confianza']:.0%}]:\n{r['respuesta']}")
        if r["opciones"]:
            print("  Opciones: " + " | ".join(r["opciones"]))
        if r["sugerencias"]:
            print("  ¿Quisiste decir?: " + " | ".join(s["mensaje"] for s in r["sugerencias"]))
        print()
    print("¡Chau!")


if __name__ == "__main__":
    main()

import logging

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    print("=== Inicio del programa ===")
    logger.debug("Este es un mensaje de debug")
    logger.info("Este es un mensaje de info")
    logger.warning("Este es un mensaje de warning")
    logger.error("Este es un mensaje de error")
    print("=== Fin del programa ===")

if __name__ == "__main__":
    main()

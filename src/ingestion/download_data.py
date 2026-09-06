import os
import gdown
import logging

# Configuration basique du logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    # ID du dossier Google Drive fourni
    folder_id = "1wYlA6xd1dWkzhCBanogywvn85_Tg5cuY"

    # Répertoire de destination
    output_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../data/raw/")
    )

    # Création du répertoire s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    logging.info(f"Début du téléchargement du dossier Google Drive (ID: {folder_id}).")
    logging.info(f"Destination : {output_dir}")

    try:
        # Téléchargement du dossier avec gdown
        gdown.download_folder(
            id=folder_id, output=output_dir, quiet=False, use_cookies=False
        )
        logging.info("Téléchargement des données terminé avec succès !")
    except Exception as e:
        logging.error(f"Une erreur est survenue lors du téléchargement : {e}")


if __name__ == "__main__":
    main()

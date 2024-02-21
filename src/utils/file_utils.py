""""""

import hashlib
from pathlib import Path


def get_file_digest(
    fp_pdf: Path, digest: str = "blake2b", digest_size: int = 10
) -> str:
    """Extraire le hachage d'un fichier avec la fonction `digest`.

    Fonctionne pour Python >= 3.8, mais le code pourra être simplifié
    pour Python >= 3.11 quand ce sera la version minimale requise par
    les principaux projets.

    Parameters
    ----------
    fp_pdf : Path
        Chemin du fichier PDF à traiter.
    digest : str
        Nom de la fonction de hachage à utiliser, "sha1" par défaut.
    digest_size : int
        Taille du digest (blake2b, sinon ignoré).

    Returns
    -------
    fd_hexdigest : str
        Hachage du fichier.
    """
    with open(fp_pdf, mode="rb") as f:
        # python >= 3.8
        if digest == "blake2b":
            # constructeur direct privilégié car plus rapide (doc module hashlib)
            # et digest_size configurable pour les algos blake2
            f_digest = hashlib.blake2b(digest_size=digest_size)
        else:
            f_digest = hashlib.new(digest)
        while chunk := f.read(8192):
            f_digest.update(chunk)
        # alternative en 1 ligne (remplace les 3 lignes précédentes) pour python >= 3.11:
        # f_digest = hashlib.file_digest(f, digest)
    fd_hexdigest = f_digest.hexdigest()
    return fd_hexdigest

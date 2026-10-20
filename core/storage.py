from whitenoise.storage import CompressedManifestStaticFilesStorage


class KcomatStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Stockage WhiteNoise (noms hashés + gzip/brotli) tolérant aux références
    manquantes dans les CSS tierces : par exemple, le thème bootswatch de Jazzmin
    pointe vers un `bootstrap.min.css.map` qui n'est pas livré. La référence est
    laissée telle quelle au lieu de faire échouer collectstatic.
    """

    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            return name

from whitenoise.storage import CompressedManifestStaticFilesStorage


class KcomatStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Stockage WhiteNoise (noms hashés + gzip) tolérant aux références
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

    def create_compressor(self, **kwargs):
        # gzip uniquement : la compression brotli (niveau 11) multiplie la durée de collectstatic
        # (plusieurs minutes sur PythonAnywhere) alors que les /static/ y sont servis par le
        # serveur de PythonAnywhere, qui n'utilise pas les fichiers .br.
        kwargs['use_brotli'] = False
        return super().create_compressor(**kwargs)

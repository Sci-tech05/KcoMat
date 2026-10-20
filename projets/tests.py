from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from core.video import analyser
from formations.catalogue import CATALOGUE, charger_catalogue
from formations.models import CategorieFormation, Formation, FormationSessionPassee
from projets.models import Projet, VideoProjet


class AnalyseLienVideoTests(TestCase):
    def test_formats_youtube(self):
        for url in ('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s', 'https://youtu.be/dQw4w9WgXcQ',
                    'youtube.com/shorts/dQw4w9WgXcQ', 'https://m.youtube.com/watch?v=dQw4w9WgXcQ',
                    'https://www.youtube.com/embed/dQw4w9WgXcQ', 'https://www.youtube.com/live/dQw4w9WgXcQ?si=x'):
            video = analyser(url)
            self.assertIsNotNone(video, url)
            self.assertEqual(video.identifiant, 'dQw4w9WgXcQ')
            self.assertTrue(video.miniature.startswith('https://i.ytimg.com/vi/dQw4w9WgXcQ/'))
        self.assertTrue(analyser('https://youtube.com/shorts/dQw4w9WgXcQ').vertical)
        self.assertFalse(analyser('https://youtu.be/dQw4w9WgXcQ').vertical)

    def test_format_tiktok(self):
        video = analyser('https://www.tiktok.com/@kcomat3/video/7412345678901234567?is_from_webapp=1')
        self.assertEqual(video.plateforme, 'tiktok')
        self.assertEqual(video.identifiant, '7412345678901234567')
        self.assertTrue(video.vertical)
        self.assertIn('/player/v1/7412345678901234567', video.lecteur)
        self.assertEqual(video.miniature, '')

    def test_liens_refuses(self):
        for url in ('', 'https://vimeo.com/123456', 'https://www.youtube.com/@KcoMat', 'https://www.tiktok.com/@kcomat3',
                    'https://evil.example/watch?v=dQw4w9WgXcQ', 'javascript:alert(1)'):
            self.assertIsNone(analyser(url), url)


class ProjetVideoTests(TestCase):
    def test_publication_exige_un_lien_video(self):
        projet = Projet(titre='Serre connectée', description_courte='x', description='x', actif=True)
        with self.assertRaises(ValidationError) as ctx:
            projet.full_clean(exclude=['categorie'])
        self.assertIn('lien_video', ctx.exception.message_dict)
        projet.lien_video = 'https://vimeo.com/1'
        with self.assertRaises(ValidationError):
            projet.full_clean(exclude=['categorie'])
        projet.lien_video = 'https://youtu.be/dQw4w9WgXcQ'
        projet.full_clean(exclude=['categorie'])   # valide

    @patch('core.video.resoudre_lien_court', return_value='https://www.tiktok.com/@kcomat3/video/7412345678901234567')
    def test_lien_court_tiktok_deplie(self, _mock):
        projet = Projet(titre='Drone', description_courte='x', description='x', lien_video='https://vm.tiktok.com/ZMabc123/')
        projet.full_clean(exclude=['categorie'])
        self.assertEqual(projet.video.identifiant, '7412345678901234567')

    @override_settings(PUSH_ASYNC=False)
    def test_pages_projet_affichent_l_apercu(self):
        projet = Projet.objects.create(titre='Serre connectée', description_courte='Arrosage', description='x',
                                       lien_video='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        VideoProjet.objects.create(projet=projet, url='https://www.tiktok.com/@kcomat3/video/7412345678901234567', legende='Démo')
        liste = self.client.get(reverse('projets:liste')).content.decode()
        self.assertIn('https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg', liste)
        detail = self.client.get(reverse('projets:detail', args=[projet.slug])).content.decode()
        self.assertIn('youtube-nocookie.com/embed/dQw4w9WgXcQ', detail)     # lecteur chargé au clic
        self.assertIn('/player/v1/7412345678901234567', detail)
        self.assertNotIn('<iframe', detail)                                  # aucune iframe au chargement


class CatalogueFormationsTests(TestCase):
    def setUp(self):
        for fiche in CATALOGUE:
            CategorieFormation.objects.get_or_create(slug=fiche['categorie'], defaults={'nom': fiche['categorie']})

    def test_creation_masquee_et_idempotente(self):
        crees, completees, inchangees = charger_catalogue()
        self.assertEqual(crees, len(CATALOGUE))
        self.assertFalse(Formation.objects.filter(actif=True).exists())
        self.assertTrue(all(f.programme_list() and f.categorie for f in Formation.objects.all()))
        self.assertEqual(charger_catalogue(), (0, 0, len(CATALOGUE)))

    def test_formation_existante_completee_sans_ecraser(self):
        existante = Formation.objects.create(slug='domotique', titre='Ma domotique', description_courte='Texte maison',
                                             description='Mon texte', prix=20000, objectifs='Mon objectif', actif=False)
        charger_catalogue()
        existante.refresh_from_db()
        self.assertEqual(existante.titre, 'Ma domotique')
        self.assertEqual(existante.objectifs, 'Mon objectif')          # non écrasé
        self.assertTrue(existante.programme)                             # complété
        self.assertEqual(Formation.objects.filter(slug='domotique').count(), 1)

    def test_publication_exige_une_image(self):
        formation = Formation(titre='T', slug='t', description_courte='x', description='x', prix=1000, actif=True)
        with self.assertRaises(ValidationError):
            formation.full_clean()


class SessionsVideoTests(TestCase):
    def test_sessions_passees_affichees_en_apercu(self):
        formation = Formation.objects.create(titre='Domotique', description_courte='x', description='x', prix=20000)
        FormationSessionPassee.objects.create(formation=formation, titre='Session Avril 2025', periode='7 au 30 avril 2025',
                                              lien_video='https://youtu.be/dQw4w9WgXcQ')
        FormationSessionPassee.objects.create(formation=formation, titre='Session masquée', publiee=False,
                                              lien_video='https://youtu.be/aaaaaaaaaaa')
        html = self.client.get(reverse('formations:detail', args=[formation.slug])).content.decode()
        self.assertIn('Session Avril 2025', html)
        self.assertIn('7 au 30 avril 2025', html)
        self.assertIn('i.ytimg.com/vi/dQw4w9WgXcQ', html)
        self.assertNotIn('Session masquée', html)

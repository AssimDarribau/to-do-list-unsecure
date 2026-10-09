import os

from django.test import TestCase
from django.urls import reverse

from tasks.models import Task
from tasks.forms import TaskForm


class TaskModelTest(TestCase):
    """Tests liés au modèle Task"""

    def test_task_creation_defaults(self):
        task = Task.objects.create(title="Test task")

        self.assertEqual(task.title, "Test task")
        self.assertFalse(task.complete)
        self.assertIsNotNone(task.created)

    def test_task_str_representation(self):
        task = Task.objects.create(title="Ma tâche")
        self.assertEqual(str(task), "Ma tâche")


class TaskFormTest(TestCase):
    """Tests du formulaire TaskForm"""

    def test_task_form_valid(self):
        form = TaskForm(data={
            "title": "Nouvelle tâche",
            "complete": False
        })
        self.assertTrue(form.is_valid())

    def test_task_form_invalid_without_title(self):
        form = TaskForm(data={
            "complete": False
        })
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)


class TaskUrlsTest(TestCase):
    """Tests de résolution des URLs"""

    def test_index_url_accessible(self):
        response = self.client.get(reverse("list"))
        self.assertEqual(response.status_code, 200)


class TaskViewsTest(TestCase):
    """Tests des vues"""

    def setUp(self):
        self.task = Task.objects.create(title="Task initiale")

    def test_index_view_lists_tasks(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task initiale")

    def test_create_task_via_post(self):
        response = self.client.post("/", {
            "title": "Task POST",
            "complete": False
        })

        self.assertEqual(Task.objects.count(), 2)
        self.assertRedirects(response, "/")

    def test_update_task_get(self):
        response = self.client.get(f"/update_task/{self.task.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task initiale")

    def test_update_task_post(self):
        response = self.client.post(
            f"/update_task/{self.task.id}/",
            {
                "title": "Task modifiée",
                "complete": True
            }
        )

        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Task modifiée")
        self.assertTrue(self.task.complete)
        self.assertRedirects(response, "/")

    def test_delete_task_get(self):
        response = self.client.get(f"/delete_task/{self.task.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task initiale")

    def test_delete_task_post(self):
        response = self.client.post(f"/delete_task/{self.task.id}/")

        self.assertEqual(Task.objects.count(), 0)
        self.assertRedirects(response, "/")


class SecurityTest(TestCase):
    """Tests de non-régression des corrections de sécurité (J2 - exercice 14)"""

    def test_titre_echappe_dans_la_liste(self):
        Task.objects.create(title="<script>alert(1)</script>")
        response = self.client.get("/")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_recherche_sans_injection_sql_et_echappee(self):
        Task.objects.create(title="<b>gras</b>")
        response = self.client.get("/search/", {"q": "' OR '1'='1"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<li>")
        response = self.client.get("/search/", {"q": "gras"})
        self.assertContains(response, "&lt;b&gt;gras&lt;/b&gt;")

    def test_import_json_et_refus_du_format_invalide(self):
        response = self.client.post("/import/", {"tasks_data": '["a", "b"]'})
        self.assertRedirects(response, "/")
        self.assertEqual(Task.objects.count(), 2)
        response = self.client.post("/import/", {"tasks_data": "pas du json"})
        self.assertEqual(response.status_code, 400)

    def test_formulaire_import_protege_par_csrf(self):
        response = self.client.get("/import/")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_admin_panel_refuse_sans_mot_de_passe_configure(self):
        response = self.client.post("/admin_panel/", {"pwd": "nimporte"})
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "SECRET_KEY", status_code=403)

    def test_admin_panel_avec_mot_de_passe_de_l_environnement(self):
        os.environ["TODOLIST_ADMIN_PASSWORD"] = "mot-de-passe-de-test"
        try:
            ok = self.client.post("/admin_panel/", {"pwd": "mot-de-passe-de-test"})
            ko = self.client.post("/admin_panel/", {"pwd": "faux"})
        finally:
            del os.environ["TODOLIST_ADMIN_PASSWORD"]
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ko.status_code, 403)

    def test_suppression_bloque_l_open_redirect(self):
        task = Task.objects.create(title="a supprimer")
        response = self.client.post(f"/delete_task/{task.id}/?next=https://evil.example.com/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_tache_inexistante_renvoie_404(self):
        self.assertEqual(self.client.get("/update_task/9999/").status_code, 404)
        self.assertEqual(self.client.get("/delete_task/9999/").status_code, 404)

    def test_entetes_anti_clickjacking(self):
        response = self.client.get("/")
        self.assertEqual(response["X-Frame-Options"], "DENY")

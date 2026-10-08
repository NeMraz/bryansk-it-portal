from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from core.factories import make_project, make_user

from .models import Comment, Project, Tag, Vote


class PortfolioFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="student",
            password="strong-password-99",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other",
            password="strong-password-99",
        )
        self.staff_user = get_user_model().objects.create_user(
            username="moderator",
            password="strong-password-99",
            is_staff=True,
        )
        self.tag = Tag.objects.create(name="Python")
        self.project = Project.objects.create(
            title="Сайт для школы",
            description="Описание проекта",
            author=self.user,
            github_url="https://github.com/example/project",
            demo_url="https://example.com/demo",
            status=Project.Status.APPROVED,
        )
        self.project.tags.add(self.tag)
        self.pending_project = Project.objects.create(
            title="На проверке",
            description="Проверяемый проект",
            author=self.user,
            status=Project.Status.PENDING,
        )

    def test_project_list_and_detail_pages_render(self):
        response = self.client.get(reverse("portfolio:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Сайт для школы")

        detail_response = self.client.get(reverse("portfolio:detail", kwargs={"pk": self.project.pk}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Сайт для школы")
        self.assertContains(detail_response, f"/projects/?tag={self.tag.pk}")

    def test_author_can_edit_and_delete_project(self):
        self.client.login(username="student", password="strong-password-99")
        edit_response = self.client.post(
            reverse("portfolio:edit", kwargs={"pk": self.project.pk}),
            {
                "title": "Новое название",
                "description": "Новое описание",
                "github_url": "https://github.com/example/new",
                "demo_url": "https://example.com/new-demo",
                "tags": [str(self.tag.pk)],
            },
        )
        self.project.refresh_from_db()
        self.assertRedirects(edit_response, reverse("portfolio:my"))
        self.assertEqual(self.project.title, "Новое название")
        self.assertEqual(self.project.status, Project.Status.PENDING)

        delete_response = self.client.post(reverse("portfolio:delete", kwargs={"pk": self.project.pk}))
        self.assertRedirects(delete_response, reverse("portfolio:my"))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_non_author_cannot_edit(self):
        self.client.login(username="other", password="strong-password-99")
        response = self.client.get(reverse("portfolio:edit", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 403)

    def test_pending_project_is_hidden_from_public_and_can_be_approved(self):
        public_response = self.client.get(reverse("portfolio:detail", kwargs={"pk": self.pending_project.pk}))
        self.assertEqual(public_response.status_code, 404)

        self.client.login(username="moderator", password="strong-password-99")
        response = self.client.post(
            reverse("portfolio:moderate", kwargs={"pk": self.pending_project.pk}),
            {"comment": "Хорошо, можно публиковать.", "action": "approve"},
        )

        self.pending_project.refresh_from_db()
        self.assertRedirects(response, reverse("portfolio:moderation"))
        self.assertEqual(self.pending_project.status, Project.Status.APPROVED)

    def test_project_search_is_case_insensitive_for_cyrillic_and_hides_pending(self):
        self.project.title = "Робот для школы"
        self.project.save()

        response = self.client.get(reverse("portfolio:list"), {"q": "робот"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Робот для школы")
        self.assertNotContains(response, self.pending_project.title)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

        description_response = self.client.get(reverse("portfolio:list"), {"q": "описание"})
        self.assertEqual(description_response.context["page_obj"].paginator.count, 1)

    def test_project_list_filters_by_tag_and_renders_clickable_tags(self):
        response = self.client.get(
            reverse("portfolio:list"),
            {"tag": str(self.tag.pk), "sort": "popular"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_tag"], self.tag.pk)
        self.assertEqual(response.context["sort"], "popular")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, f"?q=&amp;tag={self.tag.pk}&amp;sort=popular")

    def test_invalid_tag_parameter_does_not_crash_or_filter_projects(self):
        for invalid_tag in ("abc", "99999999999999999999"):
            with self.subTest(tag=invalid_tag):
                response = self.client.get(reverse("portfolio:list"), {"tag": invalid_tag})

                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.context["selected_tag"])
                self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_pagination_keeps_search_tag_and_sort_parameters(self):
        for number in range(9):
            project = Project.objects.create(
                title=f"Проект школы {number}",
                description="Описание",
                author=self.user,
                status=Project.Status.APPROVED,
            )
            project.tags.add(self.tag)

        response = self.client.get(
            reverse("portfolio:list"),
            {"q": "школы", "tag": str(self.tag.pk), "sort": "popular"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertContains(response, f"tag={self.tag.pk}&amp;sort=popular&amp;page=2")


class PortfolioRegressionTests(TestCase):
    def test_pending_project_is_visible_to_owner_and_staff_only(self):
        owner = make_user("pending_owner")
        visitor = make_user("pending_visitor")
        moderator = make_user("pending_moderator", is_staff=True)
        project = make_project(owner, approved=False, title="Невидимый проект")
        url = reverse("portfolio:detail", args=[project.pk])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(visitor)
        self.assertEqual(self.client.get(url).status_code, 404)

        for privileged_user in (owner, moderator):
            with self.subTest(username=privileged_user.username):
                self.client.force_login(privileged_user)
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_project_creation_cannot_set_author_or_publication_status(self):
        author = make_user("creation_author")
        attacker = make_user("creation_attacker")
        self.client.force_login(author)

        response = self.client.post(
            reverse("portfolio:create"),
            {
                "title": "Проверяемый проект",
                "description": "Описание",
                "status": Project.Status.APPROVED,
                "author": attacker.pk,
            },
        )

        project = Project.objects.get(title="Проверяемый проект")
        self.assertRedirects(response, reverse("portfolio:my"))
        self.assertEqual(project.author, author)
        self.assertEqual(project.status, Project.Status.PENDING)

    def test_non_owner_cannot_edit_or_delete_project(self):
        author = make_user("protected_author")
        visitor = make_user("protected_visitor")
        project = make_project(author)
        self.client.force_login(visitor)

        for route_name in ("portfolio:edit", "portfolio:delete"):
            with self.subTest(route_name=route_name):
                response = self.client.post(
                    reverse(route_name, args=[project.pk]),
                    {"title": "Подмена", "description": "Подмена"},
                )
                self.assertEqual(response.status_code, 403)

        project.refresh_from_db()
        self.assertEqual(project.title, "Робот-манипулятор")


class VoteAndCommentRegressionTests(TestCase):
    def setUp(self):
        self.author = make_user("vote_author")
        self.voter = make_user("project_voter")
        self.project = make_project(self.author)

    def test_vote_can_be_added_and_removed_but_not_given_to_own_project(self):
        vote_url = reverse("portfolio:vote", args=[self.project.pk])
        self.client.force_login(self.voter)

        first_response = self.client.post(vote_url)
        self.assertEqual(first_response.status_code, 302)
        self.assertTrue(
            Vote.objects.filter(project=self.project, user=self.voter).exists()
        )

        self.client.post(vote_url)
        self.assertFalse(
            Vote.objects.filter(project=self.project, user=self.voter).exists()
        )

        self.client.force_login(self.author)
        self.client.post(vote_url)
        self.assertFalse(Vote.objects.filter(project=self.project).exists())

    def test_database_prevents_duplicate_vote(self):
        Vote.objects.create(project=self.project, user=self.voter)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(project=self.project, user=self.voter)

    def test_comment_html_is_rendered_as_text(self):
        comment = Comment.objects.create(
            project=self.project,
            author=self.voter,
            text="<script>alert(1)</script>",
        )

        response = self.client.get(self.project.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, comment.text)
        self.assertContains(response, "&lt;script&gt;")

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from portfolio.models import Comment, Project
from team_board.models import Response, TeamPost

from .factories import make_event, make_post, make_project, make_user
from .models import Report
from .validators import MAX_IMAGE_SIZE, validate_image_size


User = get_user_model()


class ReportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass12345")
        self.reporter = User.objects.create_user(username="reporter", password="pass12345")
        self.other_user = User.objects.create_user(username="other", password="pass12345")
        self.moderator = User.objects.create_user(
            username="moderator",
            password="pass12345",
            is_staff=True,
        )
        self.project = Project.objects.create(
            title="Проект",
            description="Описание",
            author=self.owner,
            status=Project.Status.APPROVED,
        )
        self.comment = Comment.objects.create(
            project=self.project,
            author=self.owner,
            text="Комментарий",
        )
        self.post = TeamPost.objects.create(
            title="Объявление",
            looking_for="Участника",
            description="Описание объявления",
            author=self.owner,
            status=TeamPost.Status.APPROVED,
        )
        self.response = Response.objects.create(
            post=self.post,
            author=self.reporter,
            message="Отклик",
        )

    def report_url(self, kind, obj):
        return reverse("core:report", args=[kind, obj.pk])

    def submit_report(self, kind, obj, user=None):
        self.client.force_login(user or self.reporter)
        return self.client.post(
            self.report_url(kind, obj),
            {"reason": Report.Reason.SPAM, "details": "Проверить"},
        )

    def test_user_can_report_published_project_only_once(self):
        self.client.force_login(self.reporter)
        form_response = self.client.get(self.report_url("project", self.project))
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, "csrfmiddlewaretoken")

        first_response = self.submit_report("project", self.project)
        second_response = self.submit_report("project", self.project)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(
            Report.objects.filter(
                reporter=self.reporter,
                kind=Report.Kind.PROJECT,
                object_id=self.project.pk,
            ).count(),
            1,
        )

    def test_user_cannot_report_own_or_unpublished_material(self):
        self.submit_report("project", self.project, user=self.owner)
        self.assertFalse(Report.objects.exists())

        self.project.status = Project.Status.PENDING
        self.project.save(update_fields=["status"])
        response = self.submit_report("project", self.project)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Report.objects.exists())

    def test_only_post_owner_can_report_response(self):
        denied = self.submit_report("response", self.response, user=self.other_user)
        self.assertEqual(denied.status_code, 404)

        allowed = self.submit_report("response", self.response, user=self.owner)
        self.assertEqual(allowed.status_code, 302)
        self.assertTrue(
            Report.objects.filter(
                reporter=self.owner,
                kind=Report.Kind.RESPONSE,
                object_id=self.response.pk,
            ).exists()
        )

    def test_report_links_render_on_project_and_team_pages(self):
        self.client.force_login(self.reporter)
        project_page = self.client.get(self.project.get_absolute_url())
        post_page = self.client.get(self.post.get_absolute_url())

        self.assertEqual(project_page.status_code, 200)
        self.assertContains(
            project_page,
            reverse("core:report", args=["project", self.project.pk]),
        )
        self.assertContains(
            project_page,
            reverse("core:report", args=["comment", self.comment.pk]),
        )
        self.assertEqual(post_page.status_code, 200)
        self.assertContains(
            post_page,
            reverse("core:report", args=["team_post", self.post.pk]),
        )

        self.client.force_login(self.owner)
        owner_page = self.client.get(self.post.get_absolute_url())
        self.assertContains(
            owner_page,
            reverse("core:report", args=["response", self.response.pk]),
        )

    def test_only_moderator_can_open_report_queue(self):
        report = Report.objects.create(
            reporter=self.reporter,
            kind=Report.Kind.PROJECT,
            object_id=self.project.pk,
            reason=Report.Reason.SPAM,
        )
        response = self.client.get(reverse("core:reports"))
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.reporter)
        response = self.client.get(reverse("core:reports"))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.moderator)
        response = self.client.get(reverse("core:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)
        self.assertContains(
            response,
            reverse("portfolio:moderate", args=[self.project.pk]),
        )

    def test_deleting_reported_comment_closes_all_new_reports(self):
        first_report = Report.objects.create(
            reporter=self.reporter,
            kind=Report.Kind.COMMENT,
            object_id=self.comment.pk,
            reason=Report.Reason.SPAM,
        )
        second_report = Report.objects.create(
            reporter=self.other_user,
            kind=Report.Kind.COMMENT,
            object_id=self.comment.pk,
            reason=Report.Reason.ABUSE,
        )

        self.client.force_login(self.moderator)
        response = self.client.post(
            reverse("core:report_handle", args=[first_report.pk]),
            {"action": "delete"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())
        self.assertEqual(
            set(
                Report.objects.filter(pk__in=[first_report.pk, second_report.pk])
                .values_list("status", flat=True)
            ),
            {Report.Status.RESOLVED},
        )

    def test_unknown_report_action_is_rejected(self):
        report = Report.objects.create(
            reporter=self.reporter,
            kind=Report.Kind.PROJECT,
            object_id=self.project.pk,
            reason=Report.Reason.OTHER,
        )
        self.client.force_login(self.moderator)
        response = self.client.post(
            reverse("core:report_handle", args=[report.pk]),
            {"action": "delete"},
        )
        self.assertEqual(response.status_code, 400)


class ImageSizeValidatorTests(TestCase):
    def test_rejects_files_larger_than_five_megabytes(self):
        image = SimpleUploadedFile("large.jpg", b"x" * (MAX_IMAGE_SIZE + 1))
        with self.assertRaises(ValidationError):
            validate_image_size(image)


class HomePageTests(TestCase):
    def test_home_page_shows_only_public_content(self):
        author = make_user("home_author")
        make_project(author, title="Опубликованный проект")
        make_project(author, approved=False, title="Скрытый проект")
        make_post(author, title="Открытый набор")
        make_post(author, title="Закрытый набор", is_open=False)
        make_event(days=3, title="Ближайшее событие")
        make_event(days=-3, title="Прошедшее событие")
        make_event(days=2, title="Скрытое событие", is_published=False)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        for visible_text in (
            "Опубликованный проект",
            "Открытый набор",
            "Ближайшее событие",
        ):
            with self.subTest(text=visible_text):
                self.assertContains(response, visible_text)
        for hidden_text in (
            "Скрытый проект",
            "Закрытый набор",
            "Прошедшее событие",
            "Скрытое событие",
        ):
            with self.subTest(text=hidden_text):
                self.assertNotContains(response, hidden_text)


class AccessMatrixTests(TestCase):
    def test_private_pages_redirect_anonymous_users_to_login(self):
        author = make_user("access_author")
        project = make_project(author)
        protected_urls = (
            reverse("portfolio:create"),
            reverse("portfolio:my"),
            reverse("portfolio:edit", args=[project.pk]),
            reverse("team_board:create"),
            reverse("team_board:my"),
            reverse("accounts:profile_edit"),
            reverse("core:reports"),
        )

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response.url.startswith(reverse("accounts:login"))
                )

    def test_moderator_pages_return_forbidden_to_regular_users(self):
        user = make_user("access_regular")
        self.client.force_login(user)

        for url in (
            reverse("portfolio:moderation"),
            reverse("team_board:moderation"),
            reverse("core:reports"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_post_only_actions_reject_get_requests(self):
        user = make_user("access_staff", is_staff=True)
        project = make_project(user)
        post = make_post(user)
        comment = Comment.objects.create(
            project=project,
            author=user,
            text="Комментарий",
        )
        report = Report.objects.create(
            reporter=user,
            kind=Report.Kind.PROJECT,
            object_id=project.pk,
            reason=Report.Reason.SPAM,
        )
        self.client.force_login(user)

        post_only_urls = (
            reverse("portfolio:vote", args=[project.pk]),
            reverse("portfolio:comment_create", args=[project.pk]),
            reverse("portfolio:comment_delete", args=[comment.pk]),
            reverse("team_board:respond", args=[post.pk]),
            reverse("team_board:toggle", args=[post.pk]),
            reverse("core:report_handle", args=[report.pk]),
        )

        for url in post_only_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)


class StaticPagesTests(TestCase):
    def test_privacy_page_is_public_and_linked_from_registration(self):
        response = self.client.get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Политика обработки персональных данных")
        self.assertContains(
            self.client.get(reverse("accounts:register")),
            reverse("privacy"),
        )

    @override_settings(DEBUG=False)
    def test_custom_404_page_is_rendered(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Страница не найдена", status_code=404)

    @override_settings(DEBUG=False)
    def test_custom_403_page_is_rendered(self):
        self.client.force_login(make_user("forbidden_regular"))
        response = self.client.get(reverse("portfolio:moderation"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Доступ запрещён", status_code=403)

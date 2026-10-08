from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.factories import make_post, make_user

from .models import Response, TeamPost


class TeamBoardFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner",
            password="Valid-test-pass-123",
        )
        self.member = user_model.objects.create_user(
            username="member",
            password="Valid-test-pass-123",
        )
        self.moderator = user_model.objects.create_user(
            username="moderator",
            password="Valid-test-pass-123",
            is_staff=True,
        )
        self.post = TeamPost.objects.create(
            title="Команда для игры",
            looking_for="Python-разработчик",
            description="Делаем игру для школьного конкурса.",
            author=self.owner,
            status=TeamPost.Status.APPROVED,
        )

    def test_new_announcement_is_private_until_moderated(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("team_board:create"),
            {
                "title": "Ищу дизайнера",
                "looking_for": "Дизайнер",
                "description": "Помоги сделать макеты.",
                "status": TeamPost.Status.APPROVED,
                "author": self.moderator.pk,
            },
        )

        post = TeamPost.objects.get(title="Ищу дизайнера")
        self.assertRedirects(response, reverse("team_board:my"))
        self.assertEqual(post.author, self.owner)
        self.assertEqual(post.status, TeamPost.Status.PENDING)
        self.assertTrue(post.is_open)

        public_response = self.client.get(post.get_absolute_url())
        self.assertEqual(public_response.status_code, 200)
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(post.get_absolute_url()).status_code,
            404,
        )
        self.assertNotContains(
            self.client.get(reverse("team_board:list")),
            "Ищу дизайнера",
        )

    def test_moderator_must_provide_rejection_reason_and_can_approve(self):
        pending = TeamPost.objects.create(
            title="Объявление на проверке",
            looking_for="Тестировщик",
            description="Нужно тестировать игру.",
            author=self.owner,
        )
        moderation_url = reverse("team_board:moderate", args=[pending.pk])
        self.client.force_login(self.moderator)

        response = self.client.post(
            moderation_url,
            {"action": "reject", "comment": "  "},
        )
        pending.refresh_from_db()
        self.assertEqual(pending.status, TeamPost.Status.PENDING)
        self.assertContains(response, "причину")

        response = self.client.post(
            moderation_url,
            {"action": "approve", "comment": ""},
        )
        pending.refresh_from_db()
        self.assertRedirects(response, reverse("team_board:moderation"))
        self.assertEqual(pending.status, TeamPost.Status.APPROVED)
        self.assertIsNotNone(pending.moderated_at)

    def test_only_owner_and_moderator_can_see_responses(self):
        response = Response.objects.create(
            post=self.post,
            author=self.member,
            message="Могу помочь с Python.",
        )
        detail_url = self.post.get_absolute_url()

        self.client.force_login(self.member)
        public_response = self.client.get(detail_url)
        self.assertNotContains(public_response, response.message)
        self.assertNotContains(public_response, "Отклики (1)")

        self.client.force_login(self.owner)
        owner_response = self.client.get(detail_url)
        self.assertContains(owner_response, response.message)

        self.client.force_login(self.moderator)
        moderator_response = self.client.get(detail_url)
        self.assertContains(moderator_response, response.message)

    def test_member_can_respond_only_once_and_cannot_respond_to_own_post(self):
        self.client.force_login(self.member)
        response_url = reverse("team_board:respond", args=[self.post.pk])

        first_response = self.client.post(
            response_url,
            {"message": "Могу помочь."},
        )
        self.assertRedirects(first_response, self.post.get_absolute_url())
        self.assertEqual(Response.objects.filter(post=self.post, author=self.member).count(), 1)

        duplicate_response = self.client.post(
            response_url,
            {"message": "Второе сообщение."},
        )
        self.assertRedirects(duplicate_response, self.post.get_absolute_url())
        self.assertEqual(Response.objects.filter(post=self.post, author=self.member).count(), 1)
        self.assertContains(self.client.get(self.post.get_absolute_url()), "Вы уже откликнулись")

        self.client.force_login(self.owner)
        self.client.post(response_url, {"message": "Сам себе."})
        self.assertFalse(Response.objects.filter(post=self.post, author=self.owner).exists())

    def test_closed_post_is_hidden_by_default_and_rejects_responses(self):
        self.post.is_open = False
        self.post.save()

        self.assertNotContains(self.client.get(reverse("team_board:list")), self.post.title)
        self.assertContains(
            self.client.get(reverse("team_board:list"), {"closed": "1"}),
            self.post.title,
        )

        self.client.force_login(self.member)
        self.client.post(
            reverse("team_board:respond", args=[self.post.pk]),
            {"message": "Хочу в команду."},
        )
        self.assertFalse(Response.objects.filter(post=self.post).exists())
        self.assertContains(self.client.get(self.post.get_absolute_url()), "Набор в команду закрыт")

    def test_edit_returns_post_to_moderation_and_keeps_open_state(self):
        self.post.is_open = False
        self.post.save()
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("team_board:edit", args=[self.post.pk]),
            {
                "title": "Обновлённая команда",
                "looking_for": "Дизайнер",
                "description": "Обновлённое описание.",
            },
        )

        self.post.refresh_from_db()
        self.assertRedirects(response, reverse("team_board:my"))
        self.assertEqual(self.post.status, TeamPost.Status.PENDING)
        self.assertFalse(self.post.is_open)
        self.assertIsNone(self.post.moderated_at)

    def test_non_owner_cannot_edit_and_toggle_requires_post(self):
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.get(reverse("team_board:edit", args=[self.post.pk])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse("team_board:toggle", args=[self.post.pk])).status_code,
            405,
        )


class TeamBoardRegressionTests(TestCase):
    def test_pending_announcement_is_visible_only_to_owner_and_staff(self):
        owner = make_user("pending_post_owner")
        visitor = make_user("pending_post_visitor")
        moderator = make_user("pending_post_moderator", is_staff=True)
        post = make_post(owner, approved=False, title="Объявление на проверке")

        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)
        self.client.force_login(visitor)
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)

        for privileged_user in (owner, moderator):
            with self.subTest(username=privileged_user.username):
                self.client.force_login(privileged_user)
                self.assertEqual(
                    self.client.get(post.get_absolute_url()).status_code,
                    200,
                )

    def test_anonymous_user_cannot_create_or_respond(self):
        owner = make_user("anonymous_post_owner")
        post = make_post(owner)

        create_response = self.client.get(reverse("team_board:create"))
        self.assertEqual(create_response.status_code, 302)
        self.assertTrue(create_response.url.startswith(reverse("accounts:login")))

        response = self.client.post(
            reverse("team_board:respond", args=[post.pk]),
            {"message": "Хочу помочь"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Response.objects.filter(post=post).exists())

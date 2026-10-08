from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.factories import PASSWORD, make_user

from .models import Profile


class AccountsFlowTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

    def test_profile_is_registered_in_admin(self):
        self.assertIn(Profile, admin.site._registry)

    def test_registration_creates_profile_and_logs_user_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "bryansk_student",
                "password1": "strong-password-97",
                "password2": "strong-password-97",
                "agree": "on",
            },
        )

        user = get_user_model().objects.get(username="bryansk_student")
        self.assertRedirects(
            response,
            reverse("accounts:profile", kwargs={"user_id": user.id}),
        )
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_profile_can_be_edited_with_avatar(self):
        user = get_user_model().objects.create_user(
            username="student",
            password="test-password-97",
        )
        profile = Profile.objects.create(user=user)
        self.client.force_login(user)

        image_bytes = BytesIO()
        Image.new("RGB", (1, 1), color="blue").save(image_bytes, format="PNG")
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "school": "Школа № 1",
                "city": "Брянск",
                "interests": "Python",
                "about": "Изучаю Django",
                "avatar": SimpleUploadedFile(
                    "avatar.png",
                    image_bytes.getvalue(),
                    content_type="image/png",
                ),
            },
        )

        profile.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("accounts:profile", kwargs={"user_id": user.id}),
        )
        self.assertEqual(profile.city, "Брянск")
        self.assertTrue(profile.avatar)
        self.assertTrue(profile.avatar.storage.exists(profile.avatar.name))

    def test_login_logout_and_private_edit_access(self):
        get_user_model().objects.create_user(
            username="student",
            password="test-password-97",
        )

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "student", "password": "test-password-97"},
        )
        self.assertRedirects(response, reverse("home"))

        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"))

        response = self.client.get(reverse("accounts:profile_edit"))
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:profile_edit')}",
        )


class AccountRegressionTests(TestCase):
    def test_registration_rejects_weak_password_and_duplicate_username(self):
        weak_response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "new_student",
                "password1": "12345",
                "password2": "12345",
                "agree": "on",
            },
        )
        self.assertEqual(weak_response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username="new_student").exists()
        )

        make_user("existing_student")
        duplicate_response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "existing_student",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "agree": "on",
            },
        )
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(
            get_user_model().objects.filter(username="existing_student").count(),
            1,
        )

    def test_registration_requires_consent(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "no_consent_student",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(username="no_consent_student").exists()
        )
        self.assertContains(response, "Без согласия регистрация невозможна.")

    def test_login_rejects_wrong_password_and_unknown_profile_is_404(self):
        make_user("student")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "student", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(
            self.client.get(reverse("accounts:profile", args=[999999])).status_code,
            404,
        )

    def test_user_can_update_public_profile(self):
        user = make_user("profile_student")
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:profile_edit"),
            {
                "school": "Лицей № 1",
                "city": "Брянск",
                "interests": "Python",
                "about": "Изучаю программирование",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile", args=[user.pk]))
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.city, "Брянск")
        self.assertEqual(user.profile.about, "Изучаю программирование")

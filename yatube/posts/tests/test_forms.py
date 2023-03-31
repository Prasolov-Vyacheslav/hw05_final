import shutil
import tempfile

from http import HTTPStatus

from django.test import Client, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import CommentForm, PostForm
from ..models import Comment, Group, Post, User

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm
        cls.user = User.objects.create_user(username="auth")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание"
        )
        cls.group_for_edit = Group.objects.create(
            title="Тестовая группа для редактирования",
            slug="test-slug-edit",
            description="Тестовое описание"
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовый пост",
            group=cls.group_for_edit
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        self.uploaded = SimpleUploadedFile(
            name="small.gif", content=self.small_gif, content_type="image/gif"
        )

    def test_create_post(self):
        """Тест создания поста"""
        Post.objects.all().delete()
        form_data = {
            "text": "Тестовый пост",
            "group": self.group.id,
            'image': self.uploaded,
        }

        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )

        self.assertRedirects(
            response, reverse(
                "posts:profile",
                args=(self.user.username,)
            )
        )
        created_post = Post.objects.first()

        self.assertTrue(bool(created_post.image))
        self.assertEqual(created_post.text, form_data["text"])
        self.assertEqual(created_post.group.id, form_data["group"])
        self.assertEqual(self.user, created_post.author)

    def test_edit_post(self):
        """Проверка редактирования поста"""
        form_data = {
            "text": "Изменили текст",
            "group": self.group_for_edit.id
        }
        post_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=(self.post.id,)),
            data=form_data,
            follow=True,
        )
        edited_post = Post.objects.first()
        self.assertEqual(self.post.author, edited_post.author)
        self.assertEqual(edited_post.text, form_data["text"])
        self.assertEqual(edited_post.group.id, form_data["group"])
        response_old_group = self.authorized_client.post(
            reverse("posts:group_list", args=(self.group.slug,)),
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response_old_group.context["page_obj"]), 0)
        self.assertEqual(edited_post.id, self.post.id)
        self.assertEqual(Post.objects.count(), post_count)

    def test_anon_user_cant_posting(self):
        """Проверка прав на создание поста"""
        post_count = Post.objects.count()
        form_data = {
            "text": "Этот пост не должен быть создан",
            "group": self.group}

        response = self.client.post(
            reverse("posts:post_create"),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = CommentForm
        cls.user = User.objects.create_user(username="user")

        cls.post = Post.objects.create(
            author=cls.user,
            text="Давайте напишем тут душевные стихотворения!",
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_comment(self):
        """Проверка создания комментария"""
        Comment.objects.all().delete()
        text = {
            "text": "Мысли вяжутся в стишок, море лижет сушу."
            "Дети какают в горшок, а большие - в душу."
        }
        Comment.objects.create(
            post=self.post,
            author=self.user,
            text=text,
        )
        response = self.authorized_client.post(
            reverse("posts:add_comment", args=(self.post.id,)),
            data=text,
            follow=True,
        )

        self.assertRedirects(
            response, reverse(
                "posts:post_detail", args=(self.post.id,)
            )
        )
        created_comment = Comment.objects.first()

        self.assertEqual(created_comment.text, text["text"])
        self.assertEqual(created_comment.author, self.user)

    def test_anon_user_cant_comments(self):
        """Проверка прав на создание комментария"""
        text = {
            "text": "Мысли вяжутся в стишок, море лижет сушу."
            "Дети какают в горшок, а большие - в душу."
        }

        response = self.client.post(
            reverse("posts:add_comment", args=(self.post.id,)),
            data=text,
            follow=True,
        )

        comment = Comment.objects.first()
        expected_url = (
            reverse("users:login")
            + "?next="
            + reverse("posts:add_comment", args=(self.post.id,))
        )

        self.assertRedirects(response, expected_url)
        self.assertIsNone(comment)

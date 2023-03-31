from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User


class PostUrlTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username="author")
        cls.user = User.objects.create(username="user_1")

        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )

        cls.post = Post.objects.create(
            author=cls.author,
            text="Тестовый пост",
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(self.user)
        self.pages_names = (
            ("posts:index", None, "/"),
            ("posts:group_list", (self.group.slug,),
             f"/group/{self.group.slug}/"),
            ("posts:profile", (self.user.username,),
             f"/profile/{self.user.username}/"),
            ("posts:post_detail", (self.post.id,), f"/posts/{self.post.id}/"),
            ("posts:post_create", None, "/create/"),
            ("posts:post_edit", (self.post.id,),
             f"/posts/{self.post.id}/edit/"),
        )

    def test_unexisting_page(self):
        """Страница не существует."""
        response = self.client.get('/test/')
        self.assertEqual(response.status_code, 404)

    def test_all_urls_for_author(self):
        """Все urls доступны автору"""
        for name, args, _ in self.pages_names:
            with self.subTest(name=name):
                response = self.authorized_client.get(reverse(name, args=args))
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_all_urls_for_anonim(self):
        """Все urls доступны анониму, кроме edit и create """
        create_edit_list = ["posts:post_edit", "posts:post_create"]
        for name, args, url in self.pages_names:
            with self.subTest(name=name):
                if name in create_edit_list:
                    reverse_name = reverse(name, args=args)
                    response = self.client.get(
                        reverse_name, follow=True)
                    expected_url = (reverse("users:login")
                                    + f"?next={reverse_name}")
                    self.assertRedirects(response, expected_url)
                else:
                    response = self.client.get(reverse(name, args=args))
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_all_urls_for_not_author(self):
        """Все urls доступны не автору,
        но авторизованному пользователю, кроме edit"""
        for name, args, _ in self.pages_names:
            with self.subTest(name=name):
                response = self.authorized_client_not_author.get(
                    reverse(name, args=args), follow=True
                )
                if name == "posts:post_edit":
                    expected_url = (reverse('posts:post_detail',
                                            args=args))
                    self.assertRedirects(response, expected_url)
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """Все urls используют корректный template"""
        templates_url_names = (
            ("posts:index", None, "posts/index.html"),
            ("posts:group_list", (self.group.slug,), "posts/group_list.html"),
            ("posts:profile", (self.author,), "posts/profile.html"),
            ("posts:post_detail", (self.post.id,), "posts/post_detail.html"),
            ("posts:post_create", None, "posts/create_post.html"),
            ("posts:post_edit", (self.post.id,), "posts/create_post.html"),
        )

        for name, args, template in templates_url_names:
            url = reverse(name, args=args)
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_reverse(self):
        """Тест корректного reverse"""
        for name, args, url in self.pages_names:
            name_reverse = reverse(name, args=args)
            with self.subTest(name=name):
                self.assertEqual(name_reverse, url)

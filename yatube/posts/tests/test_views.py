import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post, User
from posts.forms import PostForm

MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Slava')
        cls.user = User.objects.create_user(username='User_01')
        cls.user_author = User.objects.create_user(username='Pushkin')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        uploaded = SimpleUploadedFile(
            name="small.gif", content=small_gif, content_type="image/gif"
        )
        cls.post_data = {
            "text": (
                "Тестовый пост"
            ),
            "group": cls.group,
            "author": cls.user,
            "image": uploaded,
            "pub_date": "Тестовая дата публикации",
        }
        cls.post = Post.objects.create(
            author=cls.post_data["author"],
            text=cls.post_data["text"],
            group=cls.post_data["group"],
            image=cls.post_data["image"],
            pub_date=cls.post_data["pub_date"]
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client(enforce_csrf_checks=True)

    def get_context(self, response, one_post=False):
        """Функция проверки контекста"""
        if one_post:
            post = response.context['post']
        else:
            post = response.context['page_obj'][0]
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.image, self.post.image)

    def test_index_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse("posts:index"))
        self.get_context(response)
        self.assertContains(response, '<img')

    def test_group_list_show_correct_context(self):
        """Список постов в шаблоне group_list равен ожидаемому контексту."""
        response = self.authorized_client.get(
            reverse("posts:group_list", args=(self.group.slug,))
        )
        group = response.context.get('group')
        self.get_context(response)
        self.assertEqual(group, self.group)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:profile", args=(self.user.username,))
        )
        author = response.context.get('author')
        self.get_context(response)
        self.assertEqual(author, self.user)
        self.assertContains(response, '<img')

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        self.get_context(response, one_post=True)
        self.assertContains(response, '<img')

    def test_create_edit_page_show_correct_context(self):
        """Шаблон post_create и post_edit
        сформирован с правильным контекстом."""
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
            "image": forms.fields.ImageField,
        }
        post_urls = {
            "post_create": reverse("posts:post_create"),
            "post_edit": reverse(
                "posts:post_edit",
                args=(self.post.id,)),
        }
        for name, url in post_urls.items():
            with self.subTest(name=name):
                response = self.authorized_client.get(url)
                self.assertIn('form', response.context)
                self.assertIsInstance(response.context["form"], PostForm)
                for value, expected in form_fields.items():
                    with self.subTest(name=name, value=value):
                        form_field = response.context["form"].fields[value]
                        self.assertIsInstance(form_field, expected)

    def test_new_post_on_group_page(self):
        """Проверка наличия нового поста на странице группы"""
        group_author = Group.objects.create(title='test-title1',
                                            slug='slug_group_author')
        response = (self.authorized_client.get(
            reverse('posts:group_list', args=(group_author.slug,))))
        self.assertEqual(len(response.context["page_obj"]), 0)
        post = Post.objects.first()
        self.assertEqual(post.group, self.post.group)
        response_old_group = self.authorized_client.post(
            reverse("posts:group_list", args=(self.group.slug,)),
            follow=True,
        )
        self.assertEqual(len(response_old_group.context['page_obj']), 1)

    def test_comment_show_correct_context_on_post_page(self):
        """Комментарий правильно отображается на странице поста"""
        text = (
            "Мысли вяжутся в стишок, море лижет сушу."
            "Дети какают в горшок, а большие - в душу."
        )
        Comment.objects.create(
            post=self.post,
            author=self.user_author,
            text=text,
        )

        response = self.authorized_client.get(
            reverse("posts:post_detail", args=(self.post.id,))
        )

        context = response.context["comments"].first()
        context_detail = {
            context.post.id: self.post.id,
            context.text: text,
            context.author.username: self.user_author.username,
        }

        for context, expected in context_detail.items():
            with self.subTest(context=context):
                self.assertEqual(context, expected)

    def test_cache_index_page(self):
        """Тест работы кэша"""
        post_cashe = Post.objects.create(author=self.user, text="Тест кэша")
        url = reverse("posts:index")
        response = self.authorized_client.get(url)
        post_cashe.delete()
        response_old = self.authorized_client.get(url)
        self.assertEqual(response.content, response_old.content)
        cache.clear()
        response_new = self.authorized_client.get(url)
        self.assertNotEqual(response_old.content, response_new.content)

    def test_custom_template_error(self):
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')


class FollowTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author")
        self.user = User.objects.create_user(username="user")

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_user_subscribe_unsubscribe(self):
        """Пользователь может подписываться"""
        follower = self.user.follower.count()
        following = self.user.following.count()
        self.assertFalse(self.user.follower.exists())

        self.authorized_client.get(
            reverse(
                "posts:profile_follow",
                args=(self.author.username,)
            )
        )
        self.assertEqual(self.user.follower.first().author, self.author)
        self.assertEqual(follower + 1, self.user.follower.count())
        self.assertEqual(following + 1, self.author.following.count())

    def test_forbidden_user_subscribe_to_himself(self):
        """Пользователь не может подписаться на себя"""
        author_client = Client()
        author_client.force_login(self.author)
        follower = self.user.follower.count()
        following = self.user.following.count()
        author_client.get(
            reverse(
                "posts:profile_follow",
                args=(self.author.username,)
            )
        )
        self.assertEqual(follower, self.author.follower.count())
        self.assertEqual(following, self.author.following.count())

    def test_authorized_user_unsubscribe(self):
        """Пользователь может отписаться"""
        Follow.objects.create(user=self.user, author=self.author)
        follower = self.user.follower.count()
        self.authorized_client.get(
            reverse(
                "posts:profile_unfollow",
                args=(self.author.username,)
            )
        )
        self.assertFalse(self.user.follower.exists())
        self.assertEqual(follower - 1, self.user.follower.count())

    def test_new_post_shown_in_feed(self):
        """Посты появляются в ленте только у подписчиков"""
        response = self.authorized_client.get(reverse("posts:follow_index"))
        page_obj_before = response.context.get("page_obj")
        Follow.objects.create(user=self.user, author=self.author)
        post = Post.objects.create(
            text="Тестовый пост",
            author=self.author,
        )
        response = self.authorized_client.get(reverse("posts:follow_index"))
        page_obj_after = response.context.get("page_obj")
        self.assertIn(post, response.context.get("page_obj").object_list)
        unsub = User.objects.create_user(username="unsub")
        unsub_client = Client()
        unsub_client.force_login(unsub)
        post2 = Post.objects.create(
            text="Еще один тестовый пост",
            author=self.author,
        )

        response = unsub_client.get(reverse("posts:follow_index"))
        self.assertNotIn(post2, response.context.get("page_obj").object_list)

        self.assertEqual(Post.objects.count(), Post.objects.count())
        self.assertNotEqual(page_obj_before, page_obj_after)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username="author")

        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание"
        )

        cls.object_size = 13
        post_objs = []
        for object in range(cls.object_size):
            post_obj = Post(
                author=cls.author,
                text=f"Тестовая пост {object}",
                group=cls.group
            )
            post_objs.append(post_obj)
        Post.objects.bulk_create(post_objs)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.pages_names = (
            ("posts:index", None,),
            ("posts:group_list", (self.group.slug,),),
            ("posts:profile", (self.author.username,),),
        )

    def test_two_page_contains_records(self):
        """Проверка:
        Количество постов на первой странице равно 10
        На второй странице должно быть три поста."""
        posts_per_page = (
            ('?page=1', settings.PAGE_COUNT),
            ('?page=2', settings.PAGE_COUNT_SEC_PAGE)
        )
        for name, args in self.pages_names:
            with self.subTest(name=name):
                for page, posts_num in posts_per_page:
                    with self.subTest(page=page):
                        response = self.authorized_client.get(
                            reverse(name, args=args) + page
                        )
                        self.assertEqual(len(response.context['page_obj']),
                                         posts_num)

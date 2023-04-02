from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models
from django.urls import reverse

User = get_user_model()


class Group(models.Model):
    title = models.CharField(
        'Название групп',
        max_length=200,
    )
    slug = models.SlugField(
        'Хэштег',
        unique=True
    )
    description = models.TextField(
        'Описание',
        max_length=400
    )

    class Meta:
        verbose_name_plural = 'Группы'

    def __str__(self) -> str:
        return self.title


class Post(models.Model):
    text = models.TextField('Текст')
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True,
        db_index=True
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='posts'
    )
    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name_plural = 'Посты'

    def __str__(self) -> str:
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        verbose_name="Пост",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        User,
        verbose_name="Автор",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    text = models.TextField(
        verbose_name="Текст",
        help_text="Напишите комментарий"
    )
    created = models.DateTimeField(
        verbose_name="Дата публикации",
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created"]
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return self.text[:30]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        help_text='Пользователь, который подписывается',
        verbose_name='Подписчик',
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        help_text='На кого подписываются',
        verbose_name='Автор',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'], name='unique_follow')
        ]

    def __str__(self):
        return f'Пользователь {self.user} подписался на {self.author}'

    def test_cache_index_page(self):
        """Тест работы кэша"""
        post_cashe = Post.objects.create(author=self.user, text="Тест кэша")
        url = reverse("posts:index")

        response = self.authorized_client.get(url)
        post_cashe.delete()
        response_old = self.authorized_client.get(url)
        self.assertNotEqual(response.content, response_old.content)

        cache.clear()
        response_new = self.authorized_client.get(url)
        self.assertEqual(response_old.content, response_new.content)

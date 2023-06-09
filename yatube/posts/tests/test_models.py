from django.test import TestCase

from ..models import Comment, Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Slava')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост, который имеет более 15 символов',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text="Мысли вяжутся в стишок, море лижет сушу."
            "Дети какают в горшок, а большие - в душу."
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected = post.text[:15]
        group = PostModelTest.group
        expected_group = group.title
        comment = PostModelTest.comment
        expected_comment = comment.text[:30]
        self.assertEqual(expected, Post.__str__(post))
        self.assertEqual(expected_group, Group.__str__(group))
        self.assertEqual(expected_comment, Comment.__str__(comment))

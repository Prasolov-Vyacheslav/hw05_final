from django.forms import ModelForm

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ("text", "group", "image")
        labels = {
            "text": "Текст",
            "group": "Группа",
        }
        help_texts = {
            "text": "Введите текст",
            "group": "Выберите группу",
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ("text",)
        help_texts = {
            "text": "Не стесняйся, озвучь свое мнение",
        }

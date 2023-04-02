from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Comment, Follow, Group, Post, User
from .forms import CommentForm, PostForm
from .utils import get_page_context


def index(request):
    page_obj = get_page_context(
        request, Post.objects.select_related('author', 'group').all()
    )
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    page_obj = get_page_context(
        request, group.posts.select_related('author').all()
    )
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group').all()
    posts_count_author = posts.count()
    page_obj = get_page_context(request, posts)
    follower = author.follower.count()
    if request.user.is_authenticated and request.user != author:
        user = request.user
        following = Follow.objects.filter(user=user, author=author).exists()
        following = author.following.count()
    else:
        following = False
        following = author.following.count()
    context = {
        'author': author,
        'posts_count_author': posts_count_author,
        'page_obj': page_obj,
        'following': following,
        'follower': follower,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comment_form = CommentForm(request.POST or None)
    context = {
        "post": post,
        "form": comment_form,
        "comments": Comment.objects.filter(post=post_id),
    }

    return render(request, 'posts/post_detail.html', context)


@login_required(login_url='/auth/login/')
def post_create(request):
    user = request.user

    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(False)
        post.author = user
        post.save()
        return redirect("posts:profile", user.username)

    return render(request, "posts/create_post.html", {"form": form})


@login_required(login_url='/auth/login/')
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_edit', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    user = request.user
    posts_list = Post.objects.filter(author__id__in=user.follower.values_list(
        'author',
        flat=True
    ))
    page_obj = get_page_context(request, posts_list)
    context = {'page_obj': page_obj,
               'follow': True, }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    auhtor = get_object_or_404(User, username=username)
    user = request.user
    if auhtor != user:
        Follow.objects.get_or_create(user=user, author=auhtor)
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    get_object_or_404(Follow, user=user, author__username=username).delete()
    return redirect('posts:profile', username)

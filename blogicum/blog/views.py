from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (
    ListView, DetailView, CreateView, DeleteView, UpdateView
)
from django.utils import timezone
from .models import Post, Category, Comment
from .forms import PostForm, CommentForm
from django.urls import reverse_lazy, reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count


def count_comments_on_posts(posts):
    return posts.annotate(comment_count=Count('comment_set'))


def split_into_pages(posts, request, per_page=10):
    paginator = Paginator(posts, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


class CommentInteractionMixin(LoginRequiredMixin):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def fetch_related_post(self):
        post_id = self.kwargs.get('post')
        return get_object_or_404(Post, id=post_id)

    def get_login_url(self):
        return reverse('login')


class EditableCommentMixin:
    def retrieve_instance(self, queryset=None):
        comment_id = self.kwargs.get('comment')
        comment = get_object_or_404(Comment, pk=comment_id)
        if (comment.author != self.request.user
                and not self.request.user.is_staff):
            raise Http404("Действие запрещено")
        return comment

    def get_object(self, queryset=None):
        return self.retrieve_instance()

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() == 'get':
            # Блокируем GET-удаление, но разрешаем GET-редактирование
            if '/delete_comment/' in request.path:
                return super().get(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


class PublicPostListMixin:
    model = Post
    paginate_by = 10

    def get_queryset(self):
        now = timezone.now()
        posts = Post.objects.filter(
            pub_date__lte=now,
            is_published=True,
            category__is_published=True
        )
        return count_comments_on_posts(posts).order_by('-pub_date')


class ViewAllComments(ListView):
    model = Comment
    template_name = 'blog/comment.html'
    form_class = CommentForm


class AddNewComment(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'post': self.kwargs['post']})

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            return redirect('login')

        # Получаем пост
        related_post = get_object_or_404(Post, id=self.kwargs['post'])

        # Привязываем автора и пост
        form.instance.author = self.request.user
        form.instance.post = related_post

        return super().form_valid(form)


class EditExistingComment(EditableCommentMixin,
                          LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'post': self.kwargs['post']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ничего не убираем — форма должна быть
        return context


class RemoveExistingComment(EditableCommentMixin,
                            LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_object(self, queryset=None):
        return super().get_object(queryset)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'post': self.kwargs['post']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Явно убираем форму из контекста
        context.pop('form', None)
        return context


class ShowUserProfile(DetailView):
    model = get_user_model()
    template_name = 'blog/profile.html'
    context_object_name = 'profile'

    # Используем username из URL
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        return get_object_or_404(get_user_model(),
                                 username=self.kwargs['username'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        if self.request.user == self.object:
            user_posts = Post.objects.filter(author=self.object)
        else:
            user_posts = Post.objects.filter(
                author=self.object,
                is_published=True,
                pub_date__lte=now,
                category__is_published=True
            )

        user_posts = count_comments_on_posts(user_posts).order_by('-pub_date')
        context['page_obj'] = split_into_pages(user_posts, self.request)

        return context


class UpdateUserProfile(LoginRequiredMixin, UpdateView):
    model = get_user_model()
    template_name = 'blog/user.html'
    context_object_name = 'profile'
    fields = ['username', 'first_name', 'last_name', 'email']

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.object.username})


class CreateNewPost(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', kwargs={
            'username': self.request.user.username
        })


class EditPublishedPost(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post'
    context_object_name = 'form'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('blog:post_detail', post=self.kwargs['post'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if form.instance.author != self.request.user:
            return redirect('blog:post_detail', post=self.kwargs['post'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user.username})


class DeletePublishedPost(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    context_object_name = 'form'

    def get_object(self, queryset=None):
        post_id = self.kwargs.get('post')
        post = get_object_or_404(Post, pk=post_id)
        if post.author != self.request.user and not self.request.user.is_staff:
            raise Http404("Удаление запрещено")
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.get_object())
        return context

    def get_success_url(self):
        return reverse('blog:profile', kwargs={
            'username': self.request.user.username
        })


class DisplayPostDetails(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post'

    def get_object(self, queryset=None):
        post_id = self.kwargs.get('post')
        post = get_object_or_404(Post, pk=post_id)

        now = timezone.now()
        if self.request.user != post.author:
            if (post.pub_date > now
                    or not post.is_published
                    or not post.category.is_published):
                raise Http404("Публикация не найдена или недоступна.")
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comment_set.all()
        if self.request.user.is_authenticated:
            context['form'] = CommentForm()
        return context


class ListAllBlogPosts(PublicPostListMixin, ListView):
    template_name = 'blog/index.html'


class FilterPostsByCategory(PublicPostListMixin, ListView):
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'

    def get_queryset(self):
        category_slug = self.kwargs['slug']
        category = get_object_or_404(Category,
                                     slug=category_slug,
                                     is_published=True)
        return count_comments_on_posts(
            super().get_queryset().filter(category=category)
        ).order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category, slug=self.kwargs['slug'], is_published=True
        )
        return context

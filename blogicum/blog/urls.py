from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.ListAllBlogPosts.as_view(), name='index'),
    path('posts/<int:post>/',
         views.DisplayPostDetails.as_view(),
         name='post_detail'),
    path('posts/<int:post>/comment/', views.AddNewComment.as_view(),
         name='add_comment'),
    path('posts/<int:post>/edit_comment/<int:comment>/',
         views.EditExistingComment.as_view(),
         name='edit_comment'),
    path('posts/<int:post>/delete_comment/<int:comment>/',
         views.RemoveExistingComment.as_view(),
         name='delete_comment'),
    path('category/<slug:slug>/', views.FilterPostsByCategory.as_view(),
         name='category_posts'),
    path('posts/create/', views.CreateNewPost.as_view(),
         name='create_post'),
    path('posts/<int:post>/edit/', views.EditPublishedPost.as_view(),
         name='edit_post'),
    path('posts/<int:post>/delete/', views.DeletePublishedPost.as_view(),
         name='delete_post'),
    path('profile/edit/', views.UpdateUserProfile.as_view(),
         name='edit_profile'),
    path('profile/<str:username>/', views.ShowUserProfile.as_view(),
         name='profile')

]

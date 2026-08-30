from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.RestaurantListView.as_view(), name='restaurant_list'),
    path('<int:pk>/', views.RestaurantDetailView.as_view(), name='restaurant_detail'),
    path('dishes/', views.DishListView.as_view(), name='dish_list'),
    path('dishes/<int:pk>/', views.DishDetailView.as_view(), name='dish_detail'),
    path('reviews/create/', views.ReviewCreateView.as_view(), name='review_create'),
    path('reviews/<int:pk>/update/', views.ReviewUpdateView.as_view(), name='review_update'),
    path('reviews/<int:pk>/delete/', views.ReviewDeleteView.as_view(), name='review_delete'),
    path('reviews/<int:pk>/like/', views.ReviewLikeToggleView.as_view(), name='review_like'),
    path('Logout/', views.LogoutView.as_view(), name='logout'),
    path('Login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
]
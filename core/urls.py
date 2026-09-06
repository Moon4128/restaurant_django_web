from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.RestaurantListView.as_view(), name='restaurant_list'),
    path('<int:pk>/', views.RestaurantDetailView.as_view(), name='restaurant_detail'),
    path('dishes/', views.DishListView.as_view(), name='dish_list'),
    path('dishes/<int:pk>/', views.DishDetailView.as_view(), name='dish_detail'),
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/<int:pk>/', views.CartAddView.as_view(), name='cart_add'),
    path('cart/update/<int:pk>/', views.CartUpdateView.as_view(), name='cart_update'),
    path('cart/remove/<int:pk>/', views.CartRemoveView.as_view(), name='cart_remove'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('orders/', views.OrderHistoryView.as_view(), name='order_history'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/reorder/', views.ReorderView.as_view(), name='reorder'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('reviews/create/', views.ReviewCreateView.as_view(), name='review_create'),
    path('reviews/<int:pk>/update/', views.ReviewUpdateView.as_view(), name='review_update'),
    path('reviews/<int:pk>/delete/', views.ReviewDeleteView.as_view(), name='review_delete'),
    path('reviews/<int:pk>/like/', views.ReviewLikeToggleView.as_view(), name='review_like'),
    path('Logout/', views.LogoutView.as_view(), name='logout'),
    path('Login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
]
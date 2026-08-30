from django.shortcuts import render
from .models import City, Cuisine, Restaurant, RestaurantBranch, Dish, Review
from .forms import CityForm, CuisineForm, RestaurantForm, RestaurantBranchForm, DishForm, ReviewForm
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LogoutView, LoginView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.db.models import Q
from django.shortcuts import redirect
from django.contrib.auth import login
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View


class RestaurantListView(ListView):
    model = Restaurant
    template_name = 'core/restaurant_list.html'
    context_object_name = 'restaurants'

    def get_queryset(self):
        queryset = Restaurant.objects.all()

        q = self.request.GET.get('q') or self.request.GET.get('search')
        if q:
            queryset = queryset.filter(name__icontains=q)

        city_id = self.request.GET.get('city')
        if city_id:
            queryset = queryset.filter(branches__city_id=city_id).distinct()

        cuisine_ids = self.request.GET.getlist('cuisine')
        if cuisine_ids:
            cuisine_ids = [value for value in cuisine_ids if value not in ('', None)]
            if cuisine_ids:
                queryset = queryset.filter(cuisines__id__in=cuisine_ids).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_cities'] = City.objects.all().order_by('name')
        context['all_cuisines'] = Cuisine.objects.all().order_by('name')
        context['selected_cuisine_ids'] = [
            value for value in self.request.GET.getlist('cuisine') if value
        ]
        restaurants = list(self.object_list)

        grouped = {}
        for restaurant in restaurants:
            avg_rating = restaurant.average_rating()
            stars = round(avg_rating) if avg_rating else 0
            grouped.setdefault(stars, []).append(restaurant)

        rating_lanes = []
        for stars in range(5, -1, -1):
            if stars in grouped:
                rating_lanes.append({
                    'stars': stars,
                    'restaurants': grouped[stars],
                })

        context['rating_lanes'] = rating_lanes
        return context


class RestaurantDetailView(DetailView):
    model = Restaurant
    template_name = 'core/restaurant_detail.html'
    context_object_name = 'restaurant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        city_id = self.request.GET.get('city')

        if city_id:
            context['branch'] = self.object.branches.filter(
                city_id=city_id
            ).first()
        else:
            context['branch'] = self.object.branches.first()

        selected_cuisine_id = self.request.GET.get('cuisine')
        dishes = self.object.dishes.all().select_related('cuisine')

        if selected_cuisine_id:
            dishes = dishes.filter(cuisine_id=selected_cuisine_id)
            context['selected_cuisine'] = self.object.cuisines.filter(id=selected_cuisine_id).first()
        else:
            context['selected_cuisine'] = None

        context['dishes'] = dishes
        context['reviews'] = self.object.reviews.all()

        return context

    
class DishListView(ListView):
    model = Dish
    template_name = 'core/dish_list.html'
    context_object_name = 'dishes'

    def get_queryset(self):
        restaurant_id = self.request.GET.get('restaurant')
        cuisine_id = self.request.GET.get('cuisine')

        dishes = Dish.objects.select_related('restaurant', 'cuisine').all()

        if restaurant_id:
            dishes = dishes.filter(restaurant_id=restaurant_id)

        if cuisine_id:
            dishes = dishes.filter(cuisine_id=cuisine_id)

        return dishes.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        restaurant_id = self.request.GET.get('restaurant')
        cuisine_id = self.request.GET.get('cuisine')

        context['restaurant'] = Restaurant.objects.filter(id=restaurant_id).first() if restaurant_id else None
        context['selected_cuisine'] = Cuisine.objects.filter(id=cuisine_id).first() if cuisine_id else None

        return context

class DishDetailView(DetailView):
    model = Dish
    template_name = 'core/dish_detail.html'
    context_object_name = 'dish'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['reviews'] = self.object.reviews.all()

        return context


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'core/review_form.html'

    def get_initial(self):
        initial = super().get_initial()
        restaurant_id = self.request.GET.get('restaurant') or self.request.POST.get('restaurant')
        if restaurant_id:
            initial['restaurant'] = restaurant_id
        return initial

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'review_id': self.object.id,
                'username': self.object.user.username,
                'content': self.object.content,
                'rating': self.object.rating,
                'likes_count': self.object.likes.count(),
                'restaurant_id': self.object.restaurant.id,
            })

        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy(
            'core:restaurant_detail',
            kwargs={'pk': self.object.restaurant.pk}
        )

class ReviewUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = 'core/review_form.html'

    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy(
            'core:restaurant_detail',
            kwargs={'pk': self.object.restaurant.pk}
        )

class ReviewDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Review
    template_name = 'core/review_delete.html'

    def test_func(self):
        review = self.get_object()
        return self.request.user == review.user or self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy(
            'core:restaurant_detail',
            kwargs={'pk': self.object.restaurant.pk}
        )

class ReviewLikeToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        review = Review.objects.get(pk=kwargs['pk'])
        like = review.likes.filter(user=request.user).first()

        if like:
            like.delete()
            liked = False
        else:
            review.likes.create(user=request.user)
            liked = True

        count = review.likes.count()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'liked': liked, 'count': count})

        return redirect('core:restaurant_detail', pk=review.restaurant.pk)

class LogoutView(LogoutView):
    next_page = 'core:restaurant_list'


class LoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('core:restaurant_list')


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'auth/register.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(reverse_lazy('core:restaurant_list'))
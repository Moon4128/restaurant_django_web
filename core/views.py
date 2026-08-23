from django.shortcuts import render
from .models import City, Cuisine, Restaurant, RestaurantBranch, Dish, Review
from .forms import CityForm, CuisineForm, RestaurantForm, RestaurantBranchForm, DishForm
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LogoutView, LoginView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.db.models import Q
from django.shortcuts import redirect
from django.contrib.auth import login
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View


class RestaurantListView(ListView):
    model = Restaurant
    template_name = 'core/restaurant_list.html'
    context_object_name = 'restaurants'

    def get_queryset(self):
        city_id = self.request.GET.get('city')
        if city_id:
            return Restaurant.objects.filter(branches__city_id=city_id).distinct()

        return Restaurant.objects.all()


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

        context['reviews'] = self.object.reviews.all()

        return context

    
class DishListView(ListView):
    model = Dish
    template_name = 'core/dish_list.html'
    context_object_name = 'dishes'

    def get_queryset(self):
        restaurant_id = self.request.GET.get('restaurant')
        cuisine_id = self.request.GET.get('cuisine')

        dishes = Dish.objects.all()

        if restaurant_id:
            dishes = dishes.filter(restaurant_id=restaurant_id)

        if cuisine_id:
            dishes = dishes.filter(cuisine_id=cuisine_id)

        return dishes

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
    template_name = 'core/review_form.html'
    fields = ['restaurant', 'dish', 'rating', 'text']

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'core:restaurant_detail',
            kwargs={'pk': self.object.restaurant.pk}
        )

class ReviewDeleteView(UserPassesTestMixin, DeleteView):
    model = Review
    template_name = 'core/review__delete.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_success_url(self):
        return reverse_lazy(
            'core:restaurant_detail',
            kwargs={'pk': self.object.restaurant.pk}
        )
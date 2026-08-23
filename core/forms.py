from .models import City, Cuisine, Restaurant, RestaurantBranch, Dish
from django import forms

class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['name']

class CuisineForm(forms.ModelForm):
    class Meta:
        model = Cuisine
        fields = ['name']

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ['name', 'cuisines', 'image']

class RestaurantBranchForm(forms.ModelForm):
    class Meta:
        model = RestaurantBranch
        fields = ['restaurant', 'address', 'phone', 'image', 'city']

class DishForm(forms.ModelForm):
    class Meta:
        model = Dish
        fields = ['name', 'restaurant', 'price', 'image', 'cuisine', 'description']
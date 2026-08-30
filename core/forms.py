from .models import City, Cuisine, Restaurant, RestaurantBranch, Dish, Review
from django import forms

class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['name']

class CuisineForm(forms.ModelForm):
    class Meta:
        model = Cuisine
        fields = ['name', 'image']

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

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['restaurant', 'dish', 'rating', 'content', 'media']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
            'media': forms.FileInput(),
        }

class RestaurantFilterForm(forms.Form):
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
        empty_label='All Cities',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    cuisine = forms.ModelChoiceField(
        queryset=Cuisine.objects.all(),
        required=False,
        empty_label='All Cuisines',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
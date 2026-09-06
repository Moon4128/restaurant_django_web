from .models import City, Cuisine, Restaurant, RestaurantBranch, Dish, Review, Profile
from django import forms
import re
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm

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


class CheckoutForm(forms.Form):
    fulfillment_type = forms.ChoiceField(
        choices=(('delivery', 'Delivery'), ('pickup', 'Pickup')),
        widget=forms.RadioSelect,
    )
    payment_method = forms.ChoiceField(
        choices=(('card', 'Pay now'), ('cash', 'Pay on receipt')),
        widget=forms.RadioSelect,
    )
    customer_name = forms.CharField(max_length=100, label='Full name')
    phone = forms.CharField(max_length=30, label='Phone')
    city = forms.CharField(max_length=100, label='City', required=False)
    address = forms.CharField(max_length=200, label='Street and house', required=False)
    apartment = forms.CharField(max_length=50, label='Apartment / entrance', required=False)
    note = forms.CharField(max_length=500, label='Delivery note', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    cardholder_name = forms.CharField(max_length=100, label='Name on card', required=False)
    card_number = forms.CharField(max_length=23, min_length=12, label='Card number', required=False)
    expiry = forms.CharField(max_length=5, min_length=5, label='Expiry date', required=False)
    cvv = forms.CharField(max_length=4, min_length=3, label='CVV', required=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common = {'class': 'form-control'}
        for name, attrs in {
            'customer_name': {'autocomplete': 'name', 'placeholder': 'Alex Johnson'},
            'phone': {'autocomplete': 'tel', 'placeholder': '+1 (555) 123-4567', 'inputmode': 'tel'},
            'city': {'autocomplete': 'address-level2', 'placeholder': 'City'},
            'address': {'autocomplete': 'street-address', 'placeholder': 'Street and house number'},
            'apartment': {'autocomplete': 'address-line2', 'placeholder': 'Apartment, entrance, floor'},
            'cardholder_name': {'autocomplete': 'cc-name', 'placeholder': 'Alex Johnson'},
            'card_number': {'autocomplete': 'cc-number', 'placeholder': '1234 5678 9012 3456', 'inputmode': 'numeric'},
            'expiry': {'autocomplete': 'cc-exp', 'placeholder': 'MM/YY', 'inputmode': 'numeric'},
            'cvv': {'autocomplete': 'cc-csc', 'placeholder': '123', 'inputmode': 'numeric'},
        }.items():
            self.fields[name].widget.attrs.update(common, **attrs)
        self.fields['note'].widget.attrs.update(common, placeholder='Door code or other details')

    def clean_card_number(self):
        if self.cleaned_data.get('payment_method') == 'cash' and not self.cleaned_data.get('card_number'):
            return ''
        value = re.sub(r'\D', '', self.cleaned_data['card_number'])
        if len(value) < 12 or len(value) > 19:
            raise forms.ValidationError('Enter a valid card number.')
        checksum = 0
        for index, digit in enumerate(map(int, reversed(value))):
            if index % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        if checksum % 10 != 0:
            raise forms.ValidationError('Enter a valid card number.')
        return value

    def clean_expiry(self):
        value = self.cleaned_data['expiry']
        if self.cleaned_data.get('payment_method') == 'cash' and not value:
            return ''
        if not re.fullmatch(r'(0[1-9]|1[0-2])/\d{2}', value):
            raise forms.ValidationError('Use MM/YY format.')
        return value

    def clean_cvv(self):
        value = self.cleaned_data['cvv']
        if self.cleaned_data.get('payment_method') == 'cash' and not value:
            return ''
        if not value.isdigit():
            raise forms.ValidationError('CVV must contain only digits.')
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('fulfillment_type') == 'delivery':
            for field in ('city', 'address'):
                if not cleaned.get(field):
                    self.add_error(field, 'This field is required for delivery.')
        if cleaned.get('payment_method') == 'card':
            for field in ('cardholder_name', 'card_number', 'expiry', 'cvv'):
                if not cleaned.get(field):
                    self.add_error(field, 'This field is required when paying now.')
        return cleaned


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'autocomplete': 'username'}),
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
        }


class AvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']

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
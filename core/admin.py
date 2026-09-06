from django.contrib import admin
from .models import City, Cuisine, Restaurant, RestaurantBranch, Dish, Order, OrderItem, Profile

admin.site.register(City)
admin.site.register(Cuisine)
admin.site.register(Restaurant)
admin.site.register(RestaurantBranch)
admin.site.register(Dish)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Profile)
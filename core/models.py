from django.db import models
from django.contrib.auth.models import User

class City(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Cuisine(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name



class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    cuisines = models.ManyToManyField(
        Cuisine,
        blank=True,
        related_name='restaurants'
    )
    image = models.ImageField(upload_to='rest_images/', blank=True, null=True)

    def average_rating(self):
        result = self.reviews.aggregate(
            models.Avg('rating')
        )['rating__avg']

        if result is None:
            return 0

        return round(result, 1)

    def __str__(self):
        return self.name

class Dish(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(
        upload_to='dish_images/',
        blank=True,
        null=True
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='dishes'
    )

    cuisine = models.ForeignKey(
        Cuisine,
        on_delete=models.CASCADE,
        related_name='dishes'
    )

    def average_rating(self):
        result = self.reviews.aggregate(
            models.Avg('rating')
        )['rating__avg']

        if result is None:
            return 0

        return round(result, 1)

    def __str__(self):
        return self.name

class Review(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='restaurant_reviews'
    )

    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name='reviews',
        blank=True,
        null=True,
    )

    rating = models.PositiveIntegerField(
        choices=(
            (1, '1'),
            (2, '2'),
            (3, '3'),
            (4, '4'),
            (5, '5'),
        )
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.restaurant.name} — {self.user.username}'

class RestaurantBranch(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='branches'
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='branches'
    )
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    image = models.ImageField(upload_to='rest_images/', blank=True, null=True)

    def __str__(self):
        return f'{self.restaurant.name} — {self.city.name}'


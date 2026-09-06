from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

class City(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} profile'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class Cuisine(models.Model):
    name = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to='', blank=True, null=True)

    @property
    def emoji(self):
        emoji_map = {
            'american': '🍔',
            'chinese': '🥟',
            'french': '🥐',
            'georgian': '🍲',
            'indian': '🍛',
            'italian': '🍝',
            'japanese': '🍣',
            'mediterranean': '🫒',
            'mexican': '🌮',
            'spanish': '🍤',
            'thai': '🍜',
            'turkish': '🥙',
            'ukrainian': '🥔',
        }

        normalized = self.name.strip().lower()
        for cuisine_name, icon in emoji_map.items():
            if cuisine_name in normalized:
                return icon
        return '🍽️'

    def __str__(self):
        return self.name



class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    cuisines = models.ManyToManyField(
        Cuisine,
        blank=True,
        related_name='restaurants'
    )
    image = models.ImageField(upload_to='', blank=True, null=True)

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
        upload_to='',
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
    content = models.TextField()
    media = models.FileField(upload_to='reviews_media/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_image(self):
        if not self.media:
            return False
        name = self.media.name.lower()
        return name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"))

    def __str__(self):
        return f'{self.restaurant.name} — {self.user.username}'


@receiver(post_delete, sender=Review)
def delete_review_media(sender, instance, **kwargs):
    if instance.media:
        instance.media.delete(save=False)

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
    image = models.ImageField(upload_to='', blank=True, null=True)

    def __str__(self):
        return f'{self.restaurant.name} — {self.city.name}'

class Like(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_reviews')
    created_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Payment pending'),
        ('paid', 'Paid'),
        ('preparing', 'Preparing'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fulfillment_type = models.CharField(max_length=20, choices=(('delivery', 'Delivery'), ('pickup', 'Pickup')), default='delivery')
    payment_method = models.CharField(max_length=20, choices=(('card', 'Pay now'), ('cash', 'Pay on receipt')), default='card')
    customer_name = models.CharField(max_length=100, default='')
    phone = models.CharField(max_length=30, default='')
    city = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=200, blank=True)
    apartment = models.CharField(max_length=50, blank=True)
    note = models.TextField(blank=True)
    payment_last4 = models.CharField(max_length=4, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Order #{self.pk} — {self.user.username}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    dish = models.ForeignKey(Dish, on_delete=models.SET_NULL, null=True, blank=True)
    dish_name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
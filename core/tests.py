import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import City, Cuisine, Dish, Order, OrderItem, Restaurant, Review


class ReviewFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='alice',
            email='alice@example.com',
            password='secret123'
        )
        self.restaurant = Restaurant.objects.create(name='Test Bistro')
        self.cuisine = Cuisine.objects.create(name='Italian')
        self.restaurant.cuisines.add(self.cuisine)
        self.dish = Dish.objects.create(
            name='Margherita',
            description='Tomato, mozzarella, basil.',
            price='12.50',
            restaurant=self.restaurant,
            cuisine=self.cuisine,
        )

    def test_dish_detail_renders_dish_and_review_form(self):
        response = self.client.get(reverse('core:dish_detail', kwargs={'pk': self.dish.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Margherita')
        self.assertContains(response, 'dishReviewForm')

    def test_user_can_add_dish_to_cart(self):
        self.client.login(username='alice', password='secret123')
        response = self.client.post(reverse('core:cart_add', kwargs={'pk': self.dish.pk}))

        self.assertRedirects(response, reverse('core:dish_detail', kwargs={'pk': self.dish.pk}))
        self.assertEqual(self.client.session['cart'][str(self.dish.pk)], 1)

    def test_guest_cannot_open_or_add_to_cart(self):
        cart_response = self.client.get(reverse('core:cart'))
        add_response = self.client.post(reverse('core:cart_add', kwargs={'pk': self.dish.pk}))

        self.assertRedirects(
            cart_response,
            f'{reverse("core:login")}?next={reverse("core:cart")}',
        )
        self.assertRedirects(
            add_response,
            f'{reverse("core:login")}?next={reverse("core:cart_add", kwargs={"pk": self.dish.pk})}',
        )

    def test_authenticated_user_can_change_cart_quantity(self):
        self.client.login(username='alice', password='secret123')
        add_url = reverse('core:cart_add', kwargs={'pk': self.dish.pk})
        update_url = reverse('core:cart_update', kwargs={'pk': self.dish.pk})

        self.client.post(add_url)
        increase = self.client.post(update_url, {'action': 'increase'})
        decrease = self.client.post(update_url, {'action': 'decrease'})

        self.assertEqual(increase.json()['quantity'], 2)
        self.assertEqual(increase.json()['cart_count'], 2)
        self.assertEqual(decrease.json()['quantity'], 1)
        self.assertEqual(decrease.json()['cart_count'], 1)

    def test_checkout_creates_order_and_clears_cart(self):
        self.client.login(username='alice', password='secret123')
        self.client.post(reverse('core:cart_add', kwargs={'pk': self.dish.pk}))

        response = self.client.post(
            reverse('core:checkout'),
            {
                'fulfillment_type': 'delivery',
                'payment_method': 'card',
                'customer_name': 'Alice Example',
                'phone': '+15551234567',
                'city': 'New York',
                'address': '1 Main Street',
                'apartment': '4B',
                'note': '',
                'cardholder_name': 'Alice Example',
                'card_number': '4242 4242 4242 4242',
                'expiry': '12/30',
                'cvv': '123',
            },
        )

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('core:order_detail', kwargs={'pk': order.pk}))
        self.assertEqual(str(order.total), '12.50')
        self.assertEqual(order.payment_last4, '4242')
        self.assertEqual(order.address, '1 Main Street')
        self.assertEqual(order.fulfillment_type, 'delivery')
        self.assertEqual(order.items.get().quantity, 1)
        self.assertEqual(self.client.session.get('cart'), {})

    def test_checkout_supports_pickup_and_payment_on_receipt(self):
        self.client.login(username='alice', password='secret123')
        self.client.post(reverse('core:cart_add', kwargs={'pk': self.dish.pk}))

        response = self.client.post(reverse('core:checkout'), {
            'fulfillment_type': 'pickup',
            'payment_method': 'cash',
            'customer_name': 'Alice Example',
            'phone': '+15551234567',
        })

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('core:order_detail', kwargs={'pk': order.pk}))
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_last4, '')
        self.assertEqual(order.fulfillment_type, 'pickup')

    def test_order_history_only_shows_current_users_orders(self):
        self.client.login(username='alice', password='secret123')
        order = Order.objects.create(user=self.user, total='12.50', payment_last4='4242')

        response = self.client.get(reverse('core:order_history'))

        self.assertContains(response, f'Order #{order.pk}')

    def test_user_can_open_and_update_profile(self):
        self.client.login(username='alice', password='secret123')

        response = self.client.post(reverse('core:profile'), {
            'form_type': 'profile',
            'username': 'alice-updated',
            'first_name': 'Alice',
            'last_name': 'Example',
        })

        self.assertRedirects(response, reverse('core:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'alice-updated')
        self.assertEqual(self.user.first_name, 'Alice')

    def test_user_can_change_password_without_being_logged_out(self):
        self.client.login(username='alice', password='secret123')

        response = self.client.post(reverse('core:profile'), {
            'form_type': 'password',
            'old_password': 'secret123',
            'new_password1': 'new-secret123',
            'new_password2': 'new-secret123',
        })

        self.assertRedirects(response, reverse('core:profile'))
        self.assertTrue(self.client.session.get('_auth_user_id'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-secret123'))

    def test_admin_can_delete_another_users_review(self):
        admin = get_user_model().objects.create_superuser(
            username='admin', email='admin@example.com', password='adminpass123'
        )
        review = Review.objects.create(
            restaurant=self.restaurant,
            user=self.user,
            rating=2,
            content='Needs improvement.'
        )

        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('core:review_delete', kwargs={'pk': review.pk}))

        self.assertRedirects(response, reverse('core:restaurant_detail', kwargs={'pk': self.restaurant.pk}))
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_user_can_repeat_an_order_into_cart(self):
        order = Order.objects.create(user=self.user, total='25.00', payment_last4='4242')
        OrderItem.objects.create(
            order=order,
            dish=self.dish,
            dish_name=self.dish.name,
            unit_price=self.dish.price,
            quantity=2,
        )

        self.client.login(username='alice', password='secret123')
        self.client.post(reverse('core:cart_add', kwargs={'pk': self.dish.pk}))
        response = self.client.post(reverse('core:reorder', kwargs={'pk': order.pk}))

        self.assertRedirects(response, reverse('core:cart'))
        self.assertEqual(self.client.session['cart'][str(self.dish.pk)], 2)

        self.client.post(reverse('core:reorder', kwargs={'pk': order.pk}))
        self.assertEqual(self.client.session['cart'][str(self.dish.pk)], 2)

    def test_user_can_create_review_from_restaurant_page(self):
        self.client.login(username='alice', password='secret123')

        response = self.client.post(
            reverse('core:review_create'),
            {
                'restaurant': self.restaurant.id,
                'rating': 5,
                'content': 'Great food and service.'
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.first().content, 'Great food and service.')

    def test_owner_can_delete_review(self):
        review = Review.objects.create(
            restaurant=self.restaurant,
            user=self.user,
            rating=4,
            content='Nice place.'
        )

        self.client.login(username='alice', password='secret123')
        response = self.client.post(
            reverse('core:review_delete', kwargs={'pk': review.pk}),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_deleting_review_removes_attached_media(self):
        review = Review.objects.create(
            restaurant=self.restaurant,
            user=self.user,
            rating=4,
            content='Nice place.',
            media=SimpleUploadedFile('review.jpg', b'fake-image-data', content_type='image/jpeg'),
        )
        media_name = review.media.name
        media_path = review.media.path

        self.assertTrue(review.media.storage.exists(media_name))
        review.delete()

        self.assertFalse(review.media.storage.exists(media_name))
        self.assertFalse(os.path.exists(media_path))

    def test_user_can_submit_review_with_ajax(self):
        self.client.login(username='alice', password='secret123')

        response = self.client.post(
            reverse('core:review_create'),
            {
                'restaurant': self.restaurant.id,
                'rating': 5,
                'content': 'Great food and service.',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['success'], True)
        self.assertEqual(Review.objects.count(), 1)

    def test_user_can_like_review_with_ajax(self):
        review = Review.objects.create(
            restaurant=self.restaurant,
            user=self.user,
            rating=4,
            content='Nice place.'
        )

        self.client.login(username='alice', password='secret123')
        response = self.client.post(
            reverse('core:review_like', kwargs={'pk': review.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['liked'], True)

    def test_owner_sees_review_edit_and_delete_actions(self):
        review = Review.objects.create(
            restaurant=self.restaurant,
            user=self.user,
            rating=4,
            content='Nice place.'
        )

        self.client.login(username='alice', password='secret123')
        response = self.client.get(
            reverse('core:restaurant_detail', kwargs={'pk': self.restaurant.pk})
        )

        self.assertContains(response, reverse('core:review_update', kwargs={'pk': review.pk}))
        self.assertContains(response, reverse('core:review_delete', kwargs={'pk': review.pk}))

    def test_login_redirects_to_restaurant_list(self):
        response = self.client.post(
            reverse('core:login'),
            {
                'username': 'alice',
                'password': 'secret123',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('core:restaurant_list'))

    def test_search_and_city_filter_work_together(self):
        paris = City.objects.create(name='Paris')
        french = Cuisine.objects.create(name='French')

        second = Restaurant.objects.create(name='Paris Bistro')
        second.cuisines.add(french)
        second.branches.create(city=paris, address='Somewhere', phone='123')

        response = self.client.get(
            reverse('core:restaurant_list'),
            {'q': 'Paris', 'city': paris.id, 'cuisine': french.id}
        )

        self.assertContains(response, 'Paris Bistro')
        self.assertNotContains(response, self.restaurant.name)

    def test_multiple_cuisines_can_be_selected(self):
        mediterranean = Cuisine.objects.create(name='Mediterranean')
        japanese = Cuisine.objects.create(name='Japanese')

        med_restaurant = Restaurant.objects.create(name='Rome Bistro')
        med_restaurant.cuisines.add(mediterranean)

        jap_restaurant = Restaurant.objects.create(name='Tokyo Grill')
        jap_restaurant.cuisines.add(japanese)

        response = self.client.get(
            reverse('core:restaurant_list'),
            {'cuisine': [str(mediterranean.id), str(japanese.id)]}
        )

        self.assertContains(response, 'Rome Bistro')
        self.assertContains(response, 'Tokyo Grill')

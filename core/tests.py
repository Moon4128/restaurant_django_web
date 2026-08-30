from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import City, Cuisine, Restaurant, Review


class ReviewFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='alice',
            email='alice@example.com',
            password='secret123'
        )
        self.restaurant = Restaurant.objects.create(name='Test Bistro')
        self.restaurant.cuisines.add(Cuisine.objects.create(name='Italian'))

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

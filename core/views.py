from django.shortcuts import render
from .models import City, Cuisine, Restaurant, RestaurantBranch, Dish, Review, Order, OrderItem
from .forms import CityForm, CuisineForm, RestaurantForm, RestaurantBranchForm, DishForm, ReviewForm, CheckoutForm, ProfileForm, AvatarForm
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LogoutView, LoginView
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.db.models import Q
from django.db import transaction
from django.shortcuts import redirect
from django.contrib.auth import login, update_session_auth_hash
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View, FormView


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
        context['restaurant'] = self.object.restaurant
        context['cart_quantity'] = self.request.session.get('cart', {}).get(str(self.object.pk), 0)

        return context


class CartView(LoginRequiredMixin, TemplateView):
    template_name = 'core/cart.html'
    login_url = reverse_lazy('core:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.request.session.get('cart', {})
        dishes = Dish.objects.select_related('restaurant').filter(id__in=cart.keys())
        items = []
        total = 0

        for dish in dishes:
            quantity = int(cart.get(str(dish.pk), 0))
            if quantity < 1:
                continue
            subtotal = dish.price * quantity
            items.append({'dish': dish, 'quantity': quantity, 'subtotal': subtotal})
            total += subtotal

        context['items'] = items
        context['total'] = total
        context['cart_count'] = sum(item['quantity'] for item in items)
        return context


class CartAddView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')

    def post(self, request, *args, **kwargs):
        dish = Dish.objects.get(pk=kwargs['pk'])
        cart = request.session.get('cart', {})
        dish_key = str(dish.pk)
        cart[dish_key] = int(cart.get(dish_key, 0)) + 1
        request.session['cart'] = cart
        request.session.modified = True

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'quantity': cart[dish_key],
                'cart_count': sum(int(value) for value in cart.values()),
            })

        return redirect('core:dish_detail', pk=dish.pk)


class CartUpdateView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')

    def post(self, request, *args, **kwargs):
        dish = Dish.objects.get(pk=kwargs['pk'])
        action = request.POST.get('action')
        cart = request.session.get('cart', {})
        dish_key = str(dish.pk)
        quantity = int(cart.get(dish_key, 0))

        if action == 'increase':
            quantity += 1
        elif action == 'decrease':
            quantity -= 1
        else:
            return JsonResponse({'success': False, 'error': 'Unknown cart action.'}, status=400)

        if quantity > 0:
            cart[dish_key] = quantity
        else:
            cart.pop(dish_key, None)

        request.session['cart'] = cart
        request.session.modified = True
        cart_count = sum(int(value) for value in cart.values())

        return JsonResponse({
            'success': True,
            'quantity': max(quantity, 0),
            'subtotal': str(dish.price * max(quantity, 0)),
            'cart_count': cart_count,
            'total': str(sum(
                item.price * int(cart.get(str(item.pk), 0))
                for item in Dish.objects.filter(pk__in=cart.keys())
            )),
        })


class CartRemoveView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    def post(self, request, *args, **kwargs):
        cart = request.session.get('cart', {})
        cart.pop(str(kwargs['pk']), None)
        request.session['cart'] = cart
        request.session.modified = True
        return redirect('core:cart')


class CheckoutView(LoginRequiredMixin, FormView):
    template_name = 'core/checkout.html'
    form_class = CheckoutForm
    login_url = reverse_lazy('core:login')

    def get_cart_items(self):
        cart = self.request.session.get('cart', {})
        dishes = Dish.objects.filter(pk__in=cart.keys())
        return [
            (dish, int(cart.get(str(dish.pk), 0)))
            for dish in dishes
            if int(cart.get(str(dish.pk), 0)) > 0
        ]

    def dispatch(self, request, *args, **kwargs):
        if not self.get_cart_items():
            return redirect('core:cart')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = self.get_cart_items()
        context['items'] = items
        context['total'] = sum(dish.price * quantity for dish, quantity in items)
        return context

    @transaction.atomic
    def form_valid(self, form):
        items = self.get_cart_items()
        total = sum(dish.price * quantity for dish, quantity in items)
        order = Order.objects.create(
            user=self.request.user,
            total=total,
            status='paid' if form.cleaned_data['payment_method'] == 'card' else 'pending',
            fulfillment_type=form.cleaned_data['fulfillment_type'],
            payment_method=form.cleaned_data['payment_method'],
            customer_name=form.cleaned_data['customer_name'],
            phone=form.cleaned_data['phone'],
            city=form.cleaned_data['city'],
            address=form.cleaned_data['address'],
            apartment=form.cleaned_data['apartment'],
            note=form.cleaned_data['note'],
            payment_last4=form.cleaned_data['card_number'][-4:] if form.cleaned_data['card_number'] else '',
        )
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                dish=dish,
                dish_name=dish.name,
                unit_price=dish.price,
                quantity=quantity,
            )
            for dish, quantity in items
        ])
        self.request.session['cart'] = {}
        self.request.session.modified = True
        return redirect('core:order_detail', pk=order.pk)


class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'core/order_history.html'
    context_object_name = 'orders'
    login_url = reverse_lazy('core:login')

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'core/order_detail.html'
    context_object_name = 'order'
    login_url = reverse_lazy('core:login')

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class ReorderView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')

    def post(self, request, *args, **kwargs):
        order = Order.objects.filter(user=request.user, pk=kwargs['pk']).first()
        if not order:
            raise Http404

        cart = {}
        for item in order.items.select_related('dish'):
            if item.dish_id:
                cart[str(item.dish_id)] = item.quantity
        request.session['cart'] = cart
        request.session.modified = True
        return redirect('core:cart')


class ProfileView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    template_name = 'profile.html'

    def get(self, request):
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return render(request, self.template_name, {
            'profile_form': ProfileForm(instance=request.user),
            'avatar_form': AvatarForm(instance=profile),
            'password_form': PasswordChangeForm(request.user),
        })

    def post(self, request):
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if request.POST.get('form_type') == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                return redirect('core:profile')
            profile_form = ProfileForm(instance=request.user)
            avatar_form = AvatarForm(instance=profile)
        elif request.POST.get('form_type') == 'avatar':
            avatar_form = AvatarForm(request.POST, request.FILES, instance=profile)
            if avatar_form.is_valid():
                avatar_form.save()
                return redirect('core:profile')
            profile_form = ProfileForm(instance=request.user)
            password_form = PasswordChangeForm(request.user)
        else:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                return redirect('core:profile')
            avatar_form = AvatarForm(instance=profile)
            password_form = PasswordChangeForm(request.user)

        return render(request, self.template_name, {
            'profile_form': profile_form,
            'avatar_form': avatar_form,
            'password_form': password_form,
        })


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
                'dish_id': self.object.dish.id if self.object.dish else None,
                'media_url': self.object.media.url if self.object.media and self.object.is_image else '',
            })

        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        if self.object.dish_id:
            return reverse_lazy('core:dish_detail', kwargs={'pk': self.object.dish_id})
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
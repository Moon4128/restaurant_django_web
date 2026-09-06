def cart(request):
    if not request.user.is_authenticated:
        return {'cart_count': 0}

    cart_data = request.session.get('cart', {})
    return {
        'cart_count': sum(int(quantity) for quantity in cart_data.values()),
    }


def profile_data(request):
    if not request.user.is_authenticated:
        return {'user_profile': None}

    from .models import Profile
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return {'user_profile': profile}

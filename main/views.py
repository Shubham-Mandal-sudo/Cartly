from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum, F
from functools import wraps
from .models import *
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Initialize the Razorpay Client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# ==========================================
# AUTHENTICATION VIEWS
# ==========================================

def login_view(request):
    """Handles user login by validating credentials against the database."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # authenticate(): Safely hashes the password and checks if the credentials exist in the DB
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # login(): Creates a secure session for the user in their browser
            login(request, user)
            messages.success(request, f"Welcome back, {username}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'main/login.html')


def register_view(request):
    """Handles new user registration and sets up their specific profile type (Customer/Seller)."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')
        company_name = request.POST.get('company_name', '').strip()

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register')
        
        # Prevent duplicate usernames
        if User.objects.filter(username=username).exists():
            messages.error(request, "That username is already taken.")
            return redirect('register')

        # create_user(): Securely hashes the password before saving to the DB
        user = User.objects.create_user(username=username, email=email, password=password)

        if role == 'seller':
            # Note: is_approved_seller is set to True here to bypass admin approval for testing
            userprofile = UserProfile.objects.create(user=user, is_approved_seller=True)
            SellerProfile.objects.create(user=userprofile, company_name=company_name, is_active=True)
            messages.success(request, "Seller account created and automatically approved for testing!")
        else:
            UserProfile.objects.create(user=user)
            messages.success(request, "Customer account created successfully!")

        login(request, user)
        return redirect('home')

    return render(request, 'main/register.html')


@login_required
def logout_view(request):
    """Destroys the user's session and logs them out."""
    logout(request)
    messages.success(request, "You have been logged out successfully!")
    return redirect('login') 
    

# ==========================================
# PUBLIC STORE VIEWS
# ==========================================

def home_view(request):
    """Displays the main product catalog with search and category filtering."""
    products = Product.objects.filter(in_stock=True, seller__is_active=True)
    categories = Product.CategoryChoices.choices

    # Handle search bar queries
    query = request.GET.get('q')
    if query:
        # Q(): Allows complex 'OR' database queries (e.g., search Title OR Description)
        products = products.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    # Handle dropdown category filter
    category_val = request.GET.get('category')
    if category_val:
        products = products.filter(category=category_val)

    context = {
        'products': products,
        'categories': categories,
        'current_query': query or '',
        'current_category': category_val or '',
    }
    return render(request, 'main/home.html', context)


def product_detail_view(request, id):
    """Displays a single product's details."""
    # get_object_or_404(): Safely queries the DB; if the ID doesn't exist, shows a standard 404 page instead of crashing
    product = get_object_or_404(Product, id=id)
    return render(request, 'main/product_detail.html', {'product': product})


# ==========================================
# CART & CHECKOUT VIEWS
# ==========================================

@login_required(login_url='login') 
def add_to_cart_view(request, product_id):
    """Adds a product to the user's cart or increments the quantity if it already exists."""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get('quantity', 1))

        # get_or_create(): Fetches the object if it exists, otherwise creates it automatically. Returns a (object, boolean) tuple.
        cart, created = Cart.objects.get_or_create(user=request.user.profile)

        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart, 
            product=product,
            defaults={'quantity': quantity} 
        )

        # If the item was already in the cart, just increase the count
        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f"Added {quantity} x {product.title} to your cart.")
        return redirect('product_detail', id=product.id)

    return redirect('home')


@login_required(login_url='login')
def view_cart(request):
    """Calculates totals and displays the contents of the user's cart."""
    cart, created = Cart.objects.get_or_create(user=request.user.profile)
    cart_items = cart.items.all()
    
    # Calculate subtotal using Python's sum() generator
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'main/cart.html', context)


@login_required(login_url='login')
def remove_from_cart_view(request, item_id):
    """Deletes a specific item from the cart."""
    if request.method == 'POST':
        # Security check: Ensure the item being deleted actually belongs to this specific user's cart
        item_to_remove = get_object_or_404(CartItem, id=item_id, cart__user=request.user.profile)
        product_name = item_to_remove.product.title
        item_to_remove.delete()
        messages.info(request, f"Removed {product_name} from your cart.")
        
    return redirect('cart')


@login_required(login_url='login')
def checkout_view(request):
    cart = get_object_or_404(Cart, user=request.user.profile)
    cart_items = cart.items.all()
    
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('home')

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    default_address = request.user.profile.default_shipping_address or ""

    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address', '').strip()
        
        if not shipping_address:
            messages.error(request, "Please provide a valid shipping address.")
            return redirect('checkout')

        # 1. Create the Order in your database (Status: Not Paid)
        order = Order.objects.create(
            customer=request.user,
            shipping_address=shipping_address,
            total_price=total_price, 
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order, product=item.product, quantity=item.quantity,
                price_at_purchase=item.product.price, status=OrderItem.Status.PENDING 
            )

        # 2. Create the Order in Razorpay's system
        # Razorpay expects the amount in "paise" (smallest currency unit), so multiply by 100
        amount_in_paise = int(total_price * 100)
        razorpay_order = razorpay_client.order.create({
            "amount": amount_in_paise,
            "currency": "INR", # Change to "INR" if you are testing in Indian Rupees
            "payment_capture": "1" # Auto-capture payment
        })

        # 3. Save Razorpay's Order ID to your database
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        # 4. Redirect them to the Payment Page instead of the home page!
        context = {
            'order': order,
            'amount_in_paise': amount_in_paise,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'callback_url': request.build_absolute_uri('/payment/callback/')
        }
        return render(request, 'main/payment.html', context)

    # GET Request
    context = {
        'cart_items': cart_items, 'total_price': total_price, 'default_address': default_address
    }
    return render(request, 'main/checkout.html', context)


# CSRF Exempt is required because Razorpay servers will POST to this URL, 
# and they won't have your user's CSRF token!
@csrf_exempt 
def payment_callback_view(request):
    if request.method == "POST":
        # Extract data sent by Razorpay
        payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')

        order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
        if not order:
            return redirect('home')

        try:
            # 1. Verify that the payment actually came from Razorpay and wasn't spoofed
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            
            # 2. SUCCESS! Mark order as paid
            order.razorpay_payment_id = payment_id
            order.is_paid = True
            order.save()

            # 3. Now it is safe to empty the user's cart!
            cart = Cart.objects.get(user=order.customer.profile)
            cart.items.all().delete()

            messages.success(request, f"Payment successful! Order #{order.id} is confirmed.")
            return redirect('order_history')

        except razorpay.errors.SignatureVerificationError:
            # FAILURE! The signature didn't match
            return redirect('payment_failed', order_id=order.id)
            
    return redirect('home')

def payment_failed_view(request, order_id):
    """Displays a failure message and allows them to try again or contact support."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'main/payment_failed.html', {'order': order})


# ==========================================
# SELLER SECURITY & DASHBOARD VIEWS
# ==========================================

def approved_seller_required(view_func):
    """
    Custom Decorator: Protects seller views. Blocks non-logged-in users, 
    standard customers, and pending sellers from accessing seller tools.
    """
    # @wraps(): Preserves the original view's name and metadata for Django's URL router
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in first.")
            return redirect('login')
        
        # hasattr(): Safely checks if the profile/sellerprofile exists before calling it to prevent crashes
        if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'sellerprofile'):
            if request.user.profile.sellerprofile.is_active:
                return view_func(request, *args, **kwargs)
            else:
                messages.warning(request, "Your seller account is pending admin approval.")
                return redirect('home')
        else:
            messages.error(request, "You do not have permission to view the seller dashboard.")
            return redirect('home')
            
    return _wrapped_view


@approved_seller_required
def seller_dashboard(request):
    """Displays a list of all products currently listed by the logged-in seller."""
    products = Product.objects.filter(seller=request.user.profile.sellerprofile).order_by('-created_at')
    return render(request, 'main/seller_dashboard.html', {'products': products})


@approved_seller_required
def add_product_view(request):
    """Handles the creation of new products and bulk uploading of images."""
    categories = Product.CategoryChoices.choices

    if request.method == 'POST':
        title = request.POST.get('title')
        category_val = request.POST.get('category')
        price = request.POST.get('price')
        # NEW: Extract the MRP
        mrp = request.POST.get('mrp') 
        # Convert empty strings to None so the database accepts it
        if not mrp:
            mrp = None
        description = request.POST.get('description')
        in_stock = request.POST.get('in_stock') == 'on' 

        if not price or not title:
            messages.error(request, "Title and Price are required.")
            return redirect('add_product')

        product = Product.objects.create(
            seller=request.user.profile.sellerprofile, 
            category=category_val,
            title=title,
            description=description,
            price=price,
            mrp=mrp,
            in_stock=in_stock
        )

        # request.FILES.getlist(): Extracts an array of uploaded files instead of just one
        images = request.FILES.getlist('product_images')
        if len(images) > 10:
            messages.warning(request, "You uploaded more than 10 images. Only the first 10 were saved.")
            images = images[:10] # Enforce 10 image maximum

        # Save images and automatically set the first uploaded image as the main cover
        for index, img_file in enumerate(images):
            is_cover = (index == 0) 
            ProductImage.objects.create(
                product=product,
                image=img_file,
                is_main_cover=is_cover
            )

        messages.success(request, f'"{product.title}" has been added to your catalog!')
        return redirect('seller_dashboard')

    return render(request, 'main/add_product.html', {'categories': categories})


@approved_seller_required
def edit_product_view(request, product_id):
    """Handles updating product text details, and adding/removing images."""
    # Security check: Ensure the product being edited belongs to this seller
    product = get_object_or_404(Product, id=product_id, seller=request.user.profile.sellerprofile)
    categories = Product.CategoryChoices.choices

    if request.method == 'POST':
        product.title = request.POST.get('title')
        product.category = request.POST.get('category')
        product.price = request.POST.get('price')
        mrp = request.POST.get('mrp')
        product.mrp = mrp if mrp else None
        product.description = request.POST.get('description')
        product.in_stock = request.POST.get('in_stock') == 'on'
        product.save()

        # Handle selective image deletions
        images_to_delete_ids = request.POST.getlist('delete_images')
        if images_to_delete_ids:
            ProductImage.objects.filter(id__in=images_to_delete_ids, product=product).delete()

        # Append new images while enforcing the strict 10-image limit
        new_images = request.FILES.getlist('product_images')
        current_image_count = product.images.count()

        if new_images:
            available_slots = 10 - current_image_count
            if len(new_images) > available_slots:
                messages.warning(request, f"Max 10 images allowed. Only {available_slots} new images were added.")
                new_images = new_images[:available_slots]

            for img_file in new_images:
                ProductImage.objects.create(product=product, image=img_file, is_main_cover=False)

        # Fallback: If they deleted the cover image, promote the first remaining image to cover
        if product.images.exists() and not product.images.filter(is_main_cover=True).exists():
            first_img = product.images.first()
            first_img.is_main_cover = True
            first_img.save()

        messages.success(request, f'"{product.title}" has been updated!')
        return redirect('seller_dashboard')

    return render(request, 'main/edit_product.html', {'product': product, 'categories': categories})


@approved_seller_required
def delete_product_view(request, product_id):
    """Permanently deletes a product from the database."""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, seller=request.user.profile.sellerprofile)
        title = product.title
        product.delete()
        messages.info(request, f'"{title}" has been permanently deleted.')
        
    return redirect('seller_dashboard')


# ==========================================
# CUSTOMER/SELLER ORDER HISTORY & ANALYTICS
# ==========================================

@login_required(login_url='login')
def order_history_view(request):
    """Displays a customer's purchase history."""
    # prefetch_related(): A major DB optimization. It grabs the Order, OrderItems, and attached Products in just 2 queries instead of looping queries (N+1 problem)
    orders = Order.objects.filter(customer=request.user).order_by('-created_at').prefetch_related('items__product')
    return render(request, 'main/order_history.html', {'orders': orders})


@approved_seller_required
def seller_sales_view(request):
    """Seller Analytics Dashboard handling time-filtered sales reports and shipping status updates."""
    seller = request.user.profile.sellerprofile
    
    # --- 1. HANDLE STATUS UPDATES (POST) ---
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        new_status = request.POST.get('status')
        item = get_object_or_404(OrderItem, id=item_id, product__seller=seller)
        
        # Validation: Make sure they didn't bypass the HTML dropdown options
        if new_status in dict(OrderItem.Status.choices):
            item.status = new_status
            item.save()
            messages.success(request, f"Updated status to {new_status} for {item.product.title}.")
        return redirect('seller_sales')

    # --- 2. FETCH AND FILTER SALES DATA (GET) ---
    items = OrderItem.objects.filter(product__seller=seller).order_by('-order__created_at')

    time_filter = request.GET.get('filter', 'all')
    now = timezone.now()
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Apply custom date ranges if provided
    if start_date and end_date:
        # __date__gte / __date__lte: Filters strictly where Date is Greater/Less Than or Equal To
        items = items.filter(
            order__created_at__date__gte=start_date,
            order__created_at__date__lte=end_date
        )
        time_filter = 'custom' 
        
    # Apply standard preset filters using timedelta (subtracting days from current time)
    else:
        if time_filter == 'today':
            items = items.filter(order__created_at__date=now.date())
        elif time_filter == 'week':
            items = items.filter(order__created_at__gte=now - timedelta(days=7))
        elif time_filter == 'month':
            items = items.filter(order__created_at__gte=now - timedelta(days=30))
        elif time_filter == 'year':
            items = items.filter(order__created_at__gte=now - timedelta(days=365))

    # --- 3. CALCULATE ANALYTICS ---
    # aggregate(): Performs DB-level math (much faster than calculating in Python)
    # Sum() totals it up. F() grabs the exact DB column value so we can multiply Quantity * Price per row!
    stats = items.aggregate(
        total_revenue=Sum(F('quantity') * F('price_at_purchase')),
        total_items_sold=Sum('quantity')
    )
    
    context = {
        'items': items,
        'time_filter': time_filter,
        'total_revenue': stats['total_revenue'] or 0,
        'total_items_sold': stats['total_items_sold'] or 0,
        'start_date': start_date or '',
        'end_date': end_date or '',
    }
    return render(request, 'main/seller_sales.html', context)
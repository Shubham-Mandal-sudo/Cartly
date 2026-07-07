import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver
# Create your models here.

class UserProfile(models.Model):
    # related_name='profile' allows you to do `request.user.profile` in views/templates
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_approved_seller = models.BooleanField(default=False)
    default_shipping_address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
class SellerProfile(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.SET_NULL, null=True)
    company_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.company_name

class Product(models.Model):
    # 1. Define the hardcoded categories here
    class CategoryChoices(models.TextChoices):
        ELECTRONICS = 'ELECTRONICS', 'Electronics & Media'
        FASHION = 'FASHION', 'Fashion & Apparel'
        FOOD = 'FOOD', 'Food & Beverage'
        HEALTH = 'HEALTH', 'Health & Beauty'
        HOME = 'HOME', 'Home, Garden & Furniture'
        SPORTS = 'SPORTS', 'Sports & Fitness'
        MISC = 'MISC', 'Miscellaneous'

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE) 
    
    # 2. Change the category field to a CharField
    category = models.CharField(
        max_length=50,
        choices=CategoryChoices.choices,
        default=CategoryChoices.MISC
    )
    
    title = models.CharField(max_length=500)
    description = models.TextField()
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    in_stock = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def discount_percentage(self):
        if self.mrp and self.mrp > self.price:
            discount = ((self.mrp - self.price) / self.mrp) * 100
            return round(discount) 
        return 0

    def get_main_image_url(self):
        main_img = self.images.filter(is_main_cover=True).first()
        if main_img:
            return main_img.image.url
        first_img = self.images.first()
        if first_img:
            return first_img.image.url
        return None

class Cart(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    shipping_address = models.TextField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    is_paid = models.BooleanField(default=False)

class OrderItem(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        SHIPPED = 'SHIPPED', 'Shipped'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items') 
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

# --- 1. UNIQUE FILENAME GENERATOR ---
def product_image_upload_path(instance, filename):
    # Extract the file extension (e.g., '.jpg', '.png')
    ext = filename.split('.')[-1]
    
    # Generate a random, unique UUID string and attach the extension
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    # Save it to the 'product_images/' folder
    return os.path.join('product_images/', unique_filename)


# --- 2. UPDATED PRODUCT IMAGE MODEL ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    
    # FIXED: Pass the function name to upload_to (do NOT include parentheses!)
    image = models.ImageField(upload_to=product_image_upload_path)
    
    is_main_cover = models.BooleanField(default=False) 
    
    def __str__(self):
        return f"Image for {self.product.title}"


# --- 3. CUSTOM DESTRUCTOR (SIGNAL) ---
@receiver(post_delete, sender=ProductImage)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes the physical image file from the server's hard drive 
    whenever the ProductImage database entry is deleted.
    """
    if instance.image:
        # Check if the file actually exists on the hard drive
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


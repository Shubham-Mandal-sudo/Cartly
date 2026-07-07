from django.contrib import admin
from .models import (
    UserProfile, SellerProfile, Product, 
    ProductImage, Cart, CartItem, Order, OrderItem
)

# --- USER & SELLER MANAGEMENT ---

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_approved_seller')
    list_filter = ('is_approved_seller',)
    search_fields = ('user__username', 'user__email')

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('company_name', 'user__username')
    # This is where you will go to approve new sellers by checking 'is_active'


# --- CATALOG MANAGEMENT ---

# This allows you to add/delete images directly inside the Product admin page
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1 # Shows one blank row for a new image by default

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'category', 'price', 'in_stock', 'created_at')
    list_filter = ('in_stock', 'category', 'created_at')
    search_fields = ('title', 'description', 'seller__company_name')
    list_editable = ('price', 'in_stock') # Allows you to change price/stock directly from the list view!
    inlines = [ProductImageInline]


# --- ORDER MANAGEMENT ---

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0 
    # We remove 'status' from readonly_fields so you (the admin) can edit it here if needed!
    readonly_fields = ('product', 'quantity', 'price_at_purchase')
    
    # Optional: explicitly define the fields so they show up in a nice order
    fields = ('product', 'quantity', 'price_at_purchase', 'status')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # FIXED: Removed 'status' from list_display
    list_display = ('id', 'customer', 'total_price', 'created_at')
    
    # FIXED: Removed 'status' from list_filter
    list_filter = ('created_at',)
    
    search_fields = ('customer__username', 'id')
    readonly_fields = ('customer', 'total_price', 'shipping_address', 'created_at')
    inlines = [OrderItemInline]


# --- CART MANAGEMENT (Optional but helpful for debugging) ---

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]
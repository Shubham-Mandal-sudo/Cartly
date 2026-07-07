from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('product/<int:id>/', views.product_detail_view, name='product_detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/', views.view_cart, name='cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/add-product/', views.add_product_view, name='add_product'),
    path('seller/edit-product/<int:product_id>/', views.edit_product_view, name='edit_product'),
    path('seller/delete-product/<int:product_id>/', views.delete_product_view, name='delete_product'),
    path('my-orders/', views.order_history_view, name='order_history'),
    path('seller/sales/', views.seller_sales_view, name='seller_sales'),
    path('payment/callback/', views.payment_callback_view, name='payment_callback'),
    path('payment/failed/<int:order_id>/', views.payment_failed_view, name='payment_failed'),
    path('', views.home_view, name='home'),
]


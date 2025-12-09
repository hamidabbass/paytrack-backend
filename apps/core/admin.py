"""
Admin registration for Core app
"""

from django.contrib import admin
from .models import Product, InstallmentPlan, InstallmentPayment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'shopkeeper', 'category', 'selling_price', 'stock_quantity', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'shopkeeper__email', 'sku']
    raw_id_fields = ['shopkeeper']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'shopkeeper', 'total_amount', 'remaining_amount', 'status', 'created_at']
    list_filter = ['status', 'frequency', 'created_at']
    search_fields = ['buyer__email', 'shopkeeper__email', 'product__name']
    raw_id_fields = ['shopkeeper', 'buyer', 'product']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InstallmentPayment)
class InstallmentPaymentAdmin(admin.ModelAdmin):
    list_display = ['installment_plan', 'installment_number', 'amount', 'due_date', 'status', 'payment_date']
    list_filter = ['status', 'payment_method', 'due_date']
    search_fields = ['installment_plan__buyer__email', 'transaction_id']
    raw_id_fields = ['installment_plan', 'verified_by']
    readonly_fields = ['created_at', 'updated_at']

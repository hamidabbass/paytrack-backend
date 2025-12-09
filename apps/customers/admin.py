from django.contrib import admin
from .models import Customer, InstallmentRecord, PaymentRecord


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'father_name', 'mobile_number', 'shopkeeper', 'is_active', 'created_at')
    list_filter = ('is_active', 'shopkeeper', 'created_at')
    search_fields = ('name', 'father_name', 'mobile_number', 'address')
    ordering = ('-created_at',)


@admin.register(InstallmentRecord)
class InstallmentRecordAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product_name', 'total_cost', 'monthly_installment', 'remaining_amount', 'is_completed')
    list_filter = ('is_completed', 'shopkeeper', 'created_at')
    search_fields = ('customer__name', 'product_name')
    ordering = ('-created_at',)


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('installment_record', 'amount_paid', 'payment_date', 'created_at')
    list_filter = ('payment_date', 'created_at')
    ordering = ('-payment_date',)

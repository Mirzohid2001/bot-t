from django.contrib import admin

from .models import User, Consent, SubscriptionPlan, UserSubscription, PaymentMethod, Payment, Method, UserCard, \
    SupportSession, SupportMessage, ClientCard, Advice, GiftedSubscription, Material


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'created')
    search_fields = ('telegram_id', 'username')
    ordering = ('-created',)


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ('user', 'consent_given', 'consent_date')
    list_filter = ('consent_given',)
    search_fields = ('user__telegram_id', 'user__username')
    readonly_fields = ('consent_date',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'renewable')
    search_fields = ('name',)
    list_filter = ('renewable',)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_expiring_soon')
    search_fields = ('user__telegram_id', 'plan__name')
    list_filter = ('plan', 'start_date', 'end_date')
    readonly_fields = ('is_expiring_soon',)

    def is_expiring_soon(self, obj):
        return obj.is_expiring_soon()

    is_expiring_soon.boolean = True  # True yoki False ko'rinishida chiqaradi
    is_expiring_soon.short_description = 'Tez orada tugaydi'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription_plan', 'payment_method', 'amount', 'transaction_id', 'status', 'payment_date')
    search_fields = ('user__telegram_id', 'transaction_id')
    list_filter = ('status', 'payment_date', 'payment_method')


@admin.register(Method)
class MethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(UserCard)
class UserCardAdmin(admin.ModelAdmin):
    list_display = ('user', 'cardholder_name', 'card_number', 'card_expiry')
    search_fields = ('user__telegram_id', 'cardholder_name', 'card_number')
    readonly_fields = ('card_number',)  # Buni faqat o'qiladigan qilish mumkin


@admin.register(SupportSession)
class SupportSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'started_at', 'ended_at')
    search_fields = ('user__telegram_id', 'user__username')
    list_filter = ('is_active', 'started_at', 'ended_at')


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', 'message_text', 'timestamp')
    search_fields = ('session__user__telegram_id', 'sender')
    list_filter = ('timestamp',)


@admin.register(ClientCard)
class ClientCardAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'age', 'created')
    search_fields = ('user__telegram_id', 'name')
    list_filter = ('created',)


@admin.register(Advice)
class AdviceAdmin(admin.ModelAdmin):
    list_display = ('title', 'content')
    search_fields = ('title',)


admin.site.register(GiftedSubscription)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'material_type')
    list_filter = ('material_type',)
    search_fields = ('title',)

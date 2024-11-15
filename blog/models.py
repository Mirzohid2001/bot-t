from datetime import timedelta

from django.db import models
from django.utils import timezone


# Create your models here.

class User(models.Model):
    telegram_id = models.CharField(max_length=200)
    username = models.CharField(max_length=200)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username if self.username else self.telegram_id


class Consent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consents')
    consent_given = models.BooleanField(default=False)
    consent_date = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return f"Rozilik: {self.user.username} - {self.consent_given}"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField()
    renewable = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timezone.timedelta(days=self.plan.duration_days)
        super(UserSubscription, self).save(*args, **kwargs)

    def is_expiring_soon(self):
        return self.end_date - timezone.now() <= timedelta(days=7)

    def __str__(self):
        return f"{self.user} - {self.plan.name}"

    def __str__(self):
        return f"{self.user} - {self.plan.name}"


class GiftedSubscription(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_gifts')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_gifts')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100)
    gifted_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} gifted {self.plan.name} to {self.recipient}"


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Payment(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='payments')
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20,
                              choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')])
    payment_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user} - {self.subscription_plan.name if self.subscription_plan else 'Balance Top-up'} - {self.payment_method.name if self.payment_method else 'N/A'} - {self.status}"


class Method(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cards")
    card_number = models.CharField(max_length=16)
    card_expiry = models.CharField(max_length=5)
    cardholder_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.cardholder_name} - {self.card_number[-4:]}"


class SupportSession(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name="support_sessions")
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Support Session for {self.user.username or self.user.telegram_id} - Active: {self.is_active}"


class SupportMessage(models.Model):
    session = models.ForeignKey(SupportSession, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=250)
    message_text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Message from {self.sender} in Session {self.session.id}"


class ClientCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_cards')
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    goals = models.TextField()
    challenges = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def str(self):
        return f"ClientCard for {self.user.username}"


class Advice(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()

    def __str__(self):
        return self.title


class Material(models.Model):
    MATERIAL_TYPES = [
        ('methodichka', 'Методичка'),
        ('workbook', 'Рабочие тетради'),
    ]

    title = models.CharField(max_length=100)
    document = models.FileField(upload_to='materials/')
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES)

    def __str__(self):
        return self.title


class Session(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chat_history = models.JSONField()

    def __str__(self):
        return f"Session(user_id={self.user.id})"


class FeedBack(models.Model):
    content = models.TextField()

    def __str__(self):
        return self.content

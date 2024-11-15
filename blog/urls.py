from django.urls import path
from .views import UserRegistrationView, ConsentView, SubscriptionPlanListView, SubscribeView, SubscriptionStatusView, \
    PaymentMethodListView, MakePaymentView, PaymentStatusView, ConsentStatusView, MethodsListView, MethodDetailView, \
    StatisticsView, ProfileView, UserCardView, StartSupportSessionView, SendSupportMessageView, GetSupportMessagesView, \
    ClientCardView, AdviceView, GiftSubscriptionView, SessionView, FeedBackView, MaterialListAPIView, \
    MaterialDetailAPIView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(),name='register'),
    path('consent/<str:telegram_id>/', ConsentView.as_view(), name='consent'),
    path('consent-status/<str:telegram_id>/', ConsentStatusView.as_view(), name='consent-status'),
    path('subscription-plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('subscribe/<str:telegram_id>/', SubscribeView.as_view(), name='subscribe'),
    path('gift-subscription/<int:telegram_id>/', GiftSubscriptionView.as_view(), name='gift_subscription'),
    path('subscription-status/<str:telegram_id>/', SubscriptionStatusView.as_view(), name='subscription-status'),
    path('payment-methods/', PaymentMethodListView.as_view(), name='payment-methods'),
    path('make-payment/<str:telegram_id>/', MakePaymentView.as_view(), name='make-payment'),
    path('payment-status/<str:transaction_id>/', PaymentStatusView.as_view(), name='payment-status'),
    path('methods/', MethodsListView.as_view(), name='methods-list'),
    path('methods/<int:method_id>/', MethodDetailView.as_view(), name='method-detail'),
    path('statistics/<str:telegram_id>/', StatisticsView.as_view(), name='statistics'),
    path('profile/<str:telegram_id>/', ProfileView.as_view(), name='profile'),
    path('add-card/<str:telegram_id>/', UserCardView.as_view(), name='add-card'),
    path('support/start-session/<str:telegram_id>/', StartSupportSessionView.as_view(), name='start-support-session'),
    path('support/send-message/', SendSupportMessageView.as_view(), name='send-support-message'),
    path('support/get-messages/<int:session_id>/', GetSupportMessagesView.as_view(), name='get-support-messages'),
    path('support/advice/', AdviceView.as_view(), name='advice'),
    path('client-cards/<str:telegram_id>/', ClientCardView.as_view(), name='client-card'),
    path('advice/', AdviceView.as_view(), name='advice'),
    path('materials/', MaterialListAPIView.as_view(), name='material-list'),
    path('materials/<str:material_type>/', MaterialDetailAPIView.as_view(), name='material-detail'),
    path('sessions/<int:telegram_id>/', SessionView.as_view(), name='sessions'),
    path('feedback/', FeedBackView.as_view(), name='feedback'),
]
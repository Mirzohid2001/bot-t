from _decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from tutorial.quickstart.serializers import UserSerializer

from .models import User, SubscriptionPlan, UserSubscription, Payment, PaymentMethod, Consent, Method, SupportSession, \
    SupportMessage, ClientCard, Advice, GiftedSubscription, Material
from .serializers import UserRegistrationSerializer, ConsentSerializer, UserSubscriptionSerializer, \
    SubscriptionPlanSerializer, PaymentSerializer, PaymentMethodSerializer, MethodSerializer, UserCardSerializer, \
    ClientCardSerializer, AdviceSerializer, MaterialSerializer, SessionSerializer, FeedBackSerializer


class UserRegistrationView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user, created = User.objects.get_or_create(
                telegram_id=serializer.validated_data['telegram_id'],
                defaults={'username': serializer.validated_data.get('username', '')}
            )
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response({'message': 'Пользователь успешно зарегистрирован.'}, status=status_code)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConsentView(APIView):
    def get(self, request, telegram_id):
        user = get_object_or_404(User, telegram_id=telegram_id)
        consent, created = Consent.objects.get_or_create(user=user)
        serializer = ConsentSerializer(consent)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, telegram_id):
        user = get_object_or_404(User, telegram_id=telegram_id)
        consent_given = request.data.get('consent_given', False)
        consent, created = Consent.objects.update_or_create(
            user=user,
            defaults={
                'consent_given': consent_given,
                'consent_date': timezone.now() if consent_given else None
            }
        )
        message = "Согласие получено." if consent_given else "Согласие отозвано."
        return Response({'message': message}, status=status.HTTP_200_OK)


class ConsentStatusView(APIView):
    def get(self, request, telegram_id):
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            consent = Consent.objects.get(user=user)
            return Response({
                'consent_given': consent.consent_given,
                'consent_date': consent.consent_date
            }, status=status.HTTP_200_OK)
        except Consent.DoesNotExist:
            return Response({'consent_given': False, 'consent_date': None}, status=status.HTTP_200_OK)


class SubscriptionPlanListView(APIView):
    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubscribeView(APIView):
    def post(self, request, telegram_id):
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({'error': 'Введите ID типа подписки.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Тип подписки не найден.'}, status=status.HTTP_404_NOT_FOUND)
        user_subscription = UserSubscription.objects.create(user=user, plan=plan)
        serializer = UserSubscriptionSerializer(user_subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


logger = logging.getLogger(__name__)


class GiftSubscriptionView(APIView):
    def post(self, request, telegram_id):
        try:
            sender = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Foydalanuvchi topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        recipient_username = request.data.get('recipient_username')
        plan_id = request.data.get('plan_id')
        transaction_id = request.data.get('transaction_id')

        if not recipient_username:
            return Response({'error': 'Sovgʻa qabul qiluvchining username kiriting.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not plan_id:
            return Response({'error': 'Obuna rejasini ID kiriting.'}, status=status.HTTP_400_BAD_REQUEST)
        if not transaction_id:
            return Response({'error': 'Tranzaksiya ID kiriting.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient = User.objects.get(username=recipient_username)
        except User.DoesNotExist:
            return Response({'error': 'Qabul qiluvchi topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Obuna rejasi topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        if not isinstance(transaction_id, str):
            return Response({'error': 'Tranzaksiya ID matn ko\'rinishida bo\'lishi kerak.'},
                            status=status.HTTP_400_BAD_REQUEST)

        logger.debug(
            f"Sender ID: {sender.id}, Recipient ID: {recipient.id}, Plan ID: {plan.id}, Transaction ID: {transaction_id}")

        if len(transaction_id) > 255:
            return Response({'error': 'Tranzaksiya ID juda uzun.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            gifted_subscription = GiftedSubscription.objects.create(
                sender=sender,
                recipient=recipient,
                plan=plan,
                transaction_id=transaction_id
            )
        except Exception as e:
            logger.error(f"Error creating GiftedSubscription: {e}")
            return Response({'error': 'Xatolik yuz berdi sovg\'a yaratishda.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            user_subscription = UserSubscription.objects.create(
                user=recipient,
                plan=plan,
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=plan.duration_days),
                amount=plan.price
            )
        except Exception as e:
            logger.error(f"Error creating UserSubscription: {e}")
            return Response({'error': 'Xatolik yuz berdi abonentlik yaratishda.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {"message": f"'{plan.name}' obunasi {recipient.username} foydalanuvchisiga sovgʻa qilindi."},
            status=status.HTTP_201_CREATED
        )


class SubscriptionStatusView(APIView):
    def get(self, request, telegram_id):
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
        user_subscription = UserSubscription.objects.filter(user=user).order_by('-end_date').first()
        if user_subscription and user_subscription.end_date > timezone.now():
            serializer = UserSubscriptionSerializer(user_subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'message': 'Пользователь не подписан или срок подписки истек.'}, status=status.HTTP_200_OK)


class MakePaymentView(APIView):
    def post(self, request, telegram_id):
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)

        method_id = request.data.get('payment_method')
        transaction_id = request.data.get('transaction_id')
        amount = request.data.get('amount')  # Optional for balance top-up

        if not transaction_id:
            return Response({'error': 'Введите ID транзакции.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment_method = PaymentMethod.objects.get(id=method_id)
        except PaymentMethod.DoesNotExist:
            return Response({'error': 'Способ оплаты не найден.'}, status=status.HTTP_404_NOT_FOUND)

        # Handle optional subscription plan
        plan_id = request.data.get('subscription_plan')
        subscription_plan = None
        if plan_id:
            try:
                subscription_plan = SubscriptionPlan.objects.get(id=plan_id)
                amount = subscription_plan.price  # Override amount for subscription
            except SubscriptionPlan.DoesNotExist:
                return Response({'error': 'Тип подписки не найден.'}, status=status.HTTP_404_NOT_FOUND)
        elif amount:
            try:
                amount = Decimal(amount)  # Convert amount to Decimal
                if amount <= 0:
                    raise ValueError
            except (ValueError, TypeError, Decimal.InvalidOperation):
                return Response({'error': 'Неверный формат суммы.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create payment
        payment = Payment.objects.create(
            user=user,
            subscription_plan=subscription_plan,
            payment_method=payment_method,
            amount=amount,
            transaction_id=transaction_id,
            status='pending'
        )

        # Update user balance if it’s a top-up
        if subscription_plan is None:
            user.balance += amount  # No error here because amount is Decimal
            user.save()

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PaymentStatusView(APIView):
    def get(self, request, transaction_id):
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response({'error': 'Транзакция не найдена.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentMethodListView(APIView):
    def get(self, request):
        methods = PaymentMethod.objects.all()
        serializer = PaymentMethodSerializer(methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MethodsListView(APIView):
    def get(self, request):
        methods = Method.objects.all()
        serializer = MethodSerializer(methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MethodDetailView(APIView):
    def get(self, request, method_id):
        try:
            method = Method.objects.get(id=method_id)
            serializer = MethodSerializer(method)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Method.DoesNotExist:
            return Response({'error': 'Метод не найден.'}, status=status.HTTP_404_NOT_FOUND)


class StatisticsView(APIView):
    def get(self, request, telegram_id):
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
        statistics = {
            "total_subscriptions": UserSubscription.objects.filter(user=user).count(),
            "total_payments": Payment.objects.filter(user=user, status='completed').count(),
            "last_subscription": UserSubscription.objects.filter(user=user).order_by('-end_date').first(),
        }
        return Response(statistics, status=status.HTTP_200_OK)


class ProfileView(APIView):
    def get(self, request, telegram_id):
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)

        current_subscription = UserSubscription.objects.filter(user=user, end_date__gte=timezone.now()).first()
        if current_subscription:
            subscription_serializer = UserSubscriptionSerializer(current_subscription)
            subscription_data = subscription_serializer.data
        else:
            subscription_data = None

        profile_data = {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "created": user.created.isoformat(),
            "current_subscription": subscription_data,
            "total_payments": Payment.objects.filter(user=user, status='completed').count(),
            "balance": user.balance,
        }
        return Response(profile_data, status=status.HTTP_200_OK)


class UserCardView(APIView):
    def post(self, request, telegram_id):
        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
        card_data = {
            "user": user.id,
            "card_number": request.data.get("card_number"),
            "card_expiry": request.data.get("card_expiry"),
            "cardholder_name": request.data.get("cardholder_name"),
        }
        serializer = UserCardSerializer(data=card_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StartSupportSessionView(APIView):
    def post(self, request, telegram_id):
        user, created = User.objects.get_or_create(telegram_id=telegram_id)
        session, session_created = SupportSession.objects.get_or_create(user=user, is_active=True)
        if not session_created:
            session.is_active = True
            session.save()
        return Response({
            "session_id": session.id,
            "message": "Сессия поддержки успешно начата."
        }, status=status.HTTP_200_OK)


logger = logging.getLogger(__name__)


class SendSupportMessageView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")
        sender = request.data.get("sender")
        message_text = request.data.get("message_text")

        logger.debug(f"Received support message: session_id={session_id}, sender={sender}, message_text={message_text}")

        if not session_id or not sender or not message_text:
            logger.warning("Missing fields in support message request.")
            return Response({'error': 'Все поля обязательны.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = SupportSession.objects.get(id=session_id, is_active=True)
            logger.debug(f"Found active support session: {session.id} for user {session.user.username}")
        except SupportSession.DoesNotExist:
            logger.error(f"Support session {session_id} not found or inactive.")
            return Response({'error': 'Сессия не найдена или завершена.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            message = SupportMessage.objects.create(
                session=session,
                sender=sender,
                message_text=message_text
            )
            logger.debug(f"SupportMessage created: {message.id}")
        except Exception as e:
            logger.error(f"Error creating SupportMessage: {e}")
            return Response({'error': 'Произошла ошибка при создании сообщения.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'Сообщение успешно отправлено.'}, status=status.HTTP_201_CREATED)


class GetSupportMessagesView(APIView):
    def get(self, request, session_id):
        try:
            session = SupportSession.objects.get(id=session_id)
        except SupportSession.DoesNotExist:
            return Response({'error': 'Сессия не найдена.'}, status=status.HTTP_404_NOT_FOUND)
        messages = SupportMessage.objects.filter(session=session).order_by('timestamp')
        message_data = [
            {
                'sender': msg.sender,
                'message_text': msg.message_text,
                'timestamp': msg.timestamp
            }
            for msg in messages
        ]
        return Response({'messages': message_data}, status=status.HTTP_200_OK)


class ClientCardListCreateView(APIView):
    def get(self, request):
        client_cards = ClientCard.objects.all()
        serializer = ClientCardSerializer(client_cards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ClientCardSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientCardView(APIView):
    def get(self, request, telegram_id):
        user = get_object_or_404(User, telegram_id=telegram_id)
        try:
            client_card = ClientCard.objects.get(user=user)
            serializer = ClientCardSerializer(client_card)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ClientCard.DoesNotExist:
            return Response({'error': 'Ваша карта не найдена. Пожалуйста, создайте новую карту.'},
                            status=status.HTTP_404_NOT_FOUND)

    def post(self, request, telegram_id):
        user = get_object_or_404(User, telegram_id=telegram_id)
        serializer = ClientCardSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdviceView(APIView):
    def get(self, request):
        advice = Advice.objects.all()
        serializer = AdviceSerializer(advice, many=True)
        return Response({"advice": serializer.data}, status=status.HTTP_200_OK)


class MaterialListAPIView(APIView):
    def get(self, request, format=None):
        material_type = request.query_params.get('material_type', None)
        if material_type:
            materials = Material.objects.filter(material_type=material_type)
        else:
            materials = Material.objects.all()
        serializer = MaterialSerializer(materials, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MaterialDetailAPIView(APIView):
    def get(self, request, material_type, format=None):
        material = get_object_or_404(Material, material_type=material_type)
        serializer = MaterialSerializer(material, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SessionView(APIView):
    def post(self, request, telegram_id):
        user = get_object_or_404(User, telegram_id=telegram_id)
        serializer = SessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class MyAccountView(APIView):
#     def get(self, request, telegram_id):
#         try:
#             user = User.objects.get(telegram_id=telegram_id)
#         except User.DoesNotExist:
#             return Response({'error': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
#
#         serializer = UserSerializer(user)
#         return Response(serializer.data, status=status.HTTP_200_OK)


class FeedBackView(APIView):
    def post(self, request):
        serializer = FeedBackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

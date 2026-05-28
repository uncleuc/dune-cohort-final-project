from django.contrib.auth.models import User
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import AccountProfile
from .serializers import AccountSerializer, AdminCreateUserSerializer


class AccountViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('account_profile').order_by('id')
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'username'

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateUserSerializer
        return AccountSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AccountProfile.objects.filter(user=user).update(created_by=request.user)
        response_serializer = AccountSerializer(user, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AccountSerializer(instance, context={'request': request}).data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def me(self, request):
        return Response(AccountSerializer(request.user, context={'request': request}).data)

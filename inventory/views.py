from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product, Customer, Order, OrderItem
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    CustomerSerializer,
    OrderSerializer,
    OrderCreateSerializer,
    OrderItemSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all()

        category_id = self.request.query_params.get('category')
        in_stock = self.request.query_params.get('in_stock')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if in_stock == 'true':
            queryset = queryset.filter(stock__gt=0)

        return queryset


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderItemSerializer

    def get_queryset(self):
        order_id = self.kwargs.get('order_pk')

        return OrderItem.objects.filter(order_id=order_id)
    

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()

    def get_queryset(self):
        queryset = Order.objects.all()

        customer_id = self.kwargs.get('customer_pk')
        status_filter = self.request.query_params.get('status')

        if customer_id is not None:
            queryset = queryset.filter(customer_id=customer_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset
    
    def update(self, request, *args, **kwargs):
        return Response(
            {
                'detail': 'Orders cannot be updated directly.'
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {
                'detail': 'Orders cannot be updated directly.'
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        customer_id = self.kwargs.get('customer_pk')

        customer = get_object_or_404(
            Customer,
            pk=customer_id
        )

        serializer.save(customer=customer)

    def create(self, request, *args, **kwargs):
        if self.kwargs.get('customer_pk') is None:
            return Response(
                {
                    'detail': 'Orders must be created for a specific customer.'
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        order = serializer.instance

        response_serializer = OrderSerializer(
            order,
            context=self.get_serializer_context()
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, customer_pk=None, pk=None):
        order = self.get_object()

        if order.status != Order.Status.PENDING:
            return Response(
                {
                    'detail': 'Only pending orders can be cancelled.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in order.items.select_related('product'):
            product = item.product

            product.stock += item.quantity
            product.save(update_fields=['stock'])

        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])

        serializer = OrderSerializer(
            order,
            context=self.get_serializer_context()
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
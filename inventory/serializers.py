from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import Category, Product, Customer, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'category', 'name', 'description', 'price', 'stock']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone']


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(
        source='product.id',
        read_only=True
    )

    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            'product_id',
            'product_name',
            'quantity',
            'unit_price',
        ]


class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'customer',
            'status',
            'created_at',
            'updated_at',
            'items',
        ]

        read_only_fields = [
            'id',
            'customer',
            'status',
            'created_at',
            'updated_at',
]
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "An order must contain at least one item."
            )

        product_ids = [item['product_id'] for item in value]

        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "A product cannot appear more than once in an order."
            )

        return value

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')

        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product_id = item_data['product_id']
            quantity = item_data['quantity']

            try:
                product = Product.objects.select_for_update().get(
                    id=product_id
                )
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f"Product with id {product_id} does not exist."
                )

            if product.stock < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for product '{product.name}'."
                )

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price
            )

            product.stock -= quantity
            product.save(update_fields=['stock'])

        return order


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        read_only=True
    )

    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'customer',
            'status',
            'created_at',
            'updated_at',
            'items',
            'total',
        ]

    def get_total(self, obj):
        total = sum(
            (
                item.quantity * item.unit_price
                for item in obj.items.all()
            ),
            Decimal('0.00')
        )

        return f"{total:.2f}"
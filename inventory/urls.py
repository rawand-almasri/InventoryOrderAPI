from rest_framework_nested import routers

from .views import (
    CategoryViewSet,
    ProductViewSet,
    CustomerViewSet,
    OrderViewSet,
    OrderItemViewSet,
)


router = routers.SimpleRouter()

router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet)
router.register('customers', CustomerViewSet)
router.register('orders', OrderViewSet)


customer_router = routers.NestedSimpleRouter(
    router,
    r'customers',
    lookup='customer'
)

customer_router.register(
    r'orders',
    OrderViewSet,
    basename='customer-orders'
)


order_router = routers.NestedSimpleRouter(
    router,
    r'orders',
    lookup='order'
)

order_router.register(
    r'items',
    OrderItemViewSet,
    basename='order-items'
)


urlpatterns = (
    router.urls
    + customer_router.urls
    + order_router.urls
)
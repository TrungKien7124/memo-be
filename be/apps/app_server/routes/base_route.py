from rest_framework.routers import DefaultRouter


class BaseRouter(DefaultRouter):
    """Pre-configured router with trailing slash enabled."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('trailing_slash', True)
        super().__init__(*args, **kwargs)

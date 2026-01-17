from __future__ import annotations

from apps.app_server.controllers.base.app_server_health_base_controller import BaseHealthView


class RSEHealthView(BaseHealthView):
    service_name = "rse"

import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import MessageSerializer
from . import services

logger = logging.getLogger(__name__)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return services.get_accessible_messages(
            user=self.request.user,
            channel_id=self.request.query_params.get("channel_id"),
            since_sequence=self._optional_int_query("since_sequence"),
            before_sequence=self._optional_int_query("before_sequence"),
            limit=self._optional_int_query("limit"),
        )

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except services.ChatServiceError as exc:
            return self._service_error_response(exc)

    def create(self, request, *args, **kwargs):
        channel_id = request.query_params.get("channel_id") or request.data.get("channel_id")
        if not channel_id:
            return Response(
                {"detail": "channel_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = services.create_message(
                user=request.user,
                channel_id=channel_id,
                content=serializer.validated_data.get("content", ""),
                message_type=serializer.validated_data.get("message_type") or "text",
                metadata=serializer.validated_data.get("metadata") or {},
                client_message_id=serializer.validated_data.get("client_message_id"),
                client_mutation_id=serializer.validated_data.get("client_mutation_id"),
            )
        except services.ChatServiceError as exc:
            return self._service_error_response(exc)

        services.broadcast_message_event(message, "message.created")
        return Response(
            self.get_serializer(message).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        return self._update_message(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self._update_message(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        parsed_version = self._required_int_body(request, "version")
        if isinstance(parsed_version, Response):
            return parsed_version

        try:
            message = services.delete_message(
                user=request.user,
                message_id=kwargs["pk"],
                version=parsed_version,
                client_mutation_id=request.data.get("client_mutation_id"),
            )
        except services.ChatServiceError as exc:
            return self._service_error_response(exc)

        services.broadcast_message_event(message, "message.deleted")
        return Response(self.get_serializer(message).data, status=status.HTTP_200_OK)

    def _update_message(self, request, *args, **kwargs):
        parsed_version = self._required_int_body(request, "version")
        if isinstance(parsed_version, Response):
            return parsed_version

        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            message = services.update_message(
                user=request.user,
                message_id=kwargs["pk"],
                content=serializer.validated_data.get("content", ""),
                version=parsed_version,
                client_mutation_id=serializer.validated_data.get("client_mutation_id"),
                metadata=serializer.validated_data.get("metadata"),
            )
        except services.ChatServiceError as exc:
            return self._service_error_response(exc)

        services.broadcast_message_event(message, "message.updated")
        return Response(self.get_serializer(message).data, status=status.HTTP_200_OK)

    def _optional_int_query(self, key):
        value = self.request.query_params.get(key)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise services.ChatValidationError(f"{key} must be an integer")

    def _required_int_body(self, request, key):
        value = request.data.get(key)
        if value in (None, ""):
            return Response(
                {"detail": f"{key} is required"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        try:
            return int(value)
        except (TypeError, ValueError):
            return Response(
                {"detail": f"{key} must be an integer"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

    def _service_error_response(self, exc):
        return Response({"detail": exc.detail}, status=exc.status_code)

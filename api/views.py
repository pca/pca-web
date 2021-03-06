from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_auth.registration.views import SocialLoginView
from rest_framework import exceptions
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from wca_allauth.views import WorldCubeAssociationOAuth2Adapter

from wca.models import Event, Result
from wca.serializers import EventSerializer, ResultSerializer

from . import app_settings
from .models import RegionUpdateRequest
from .serializers import (
    RegionSerializer,
    UserDetailSerializer,
    UserRegionUpdateSerializer,
    RegionUpdateRequestSerializer,
)

User = get_user_model()

PH_COUNTRY_ID = "Philippines"
WCA_PROVIDER = "worldcubeassociation"


class WCALoginView(SocialLoginView):
    """ Login with WCA code. access_token is not required. """

    adapter_class = WorldCubeAssociationOAuth2Adapter
    callback_url = app_settings.WCA_CALLBACK_URL
    client_class = OAuth2Client

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)


class UserRetrieveAPIView(RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.none()

    def get_object(self):
        return self.request.user


class RegionListAPIView(APIView):
    serializer_class = RegionSerializer

    def get(self, request, *args, **kwargs):
        regions = [dict(id=id, name=name) for id, name in User.REGION_CHOICES]
        return Response(regions)


class EventListAPIView(ListAPIView):
    serializer_class = EventSerializer
    queryset = Event.objects.all()


class RankingBaseAPIView(ListAPIView):
    serializer_class = ResultSerializer

    def get_event(self):
        event_id = self.kwargs.get("event_id")
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            raise exceptions.NotFound("Event not found.")
        return event

    def get_limit(self):
        limit = self.request.query_params.get("limit", 100)
        try:
            limit = int(limit)
        except ValueError:
            raise exceptions.ParseError("Invalid limit")
        return limit


class NationalRankingSingleAPIView(RankingBaseAPIView):
    def get_queryset(self):
        event = self.get_event()
        limit = self.get_limit()
        result_ids = (
            Result.objects.filter(country_id=PH_COUNTRY_ID, event=event, best__gt=0)
            .order_by("person_id", "best")
            .distinct("person_id")
            .values_list("id")
        )
        results = Result.objects.filter(pk__in=result_ids).order_by("best")
        return results[:limit]


class NationalRankingAverageAPIView(RankingBaseAPIView):
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["rank_type"] = "average"
        return context

    def get_queryset(self):
        event = self.get_event()
        limit = self.get_limit()
        result_ids = (
            Result.objects.filter(country_id=PH_COUNTRY_ID, event=event, average__gt=0)
            .order_by("person_id", "average")
            .distinct("person_id")
            .values_list("id")
        )
        results = Result.objects.filter(pk__in=result_ids).order_by("average")
        return results[:limit]


class RegionalRankingSingleAPIView(RankingBaseAPIView):
    def get_queryset(self):
        region = self.kwargs.get("region_id")
        event = self.get_event()
        limit = self.get_limit()
        wca_ids = User.objects.filter(
            region=region, socialaccount__provider=WCA_PROVIDER, wca_id__isnull=False
        ).values_list("wca_id")
        result_ids = (
            Result.objects.filter(
                country_id=PH_COUNTRY_ID,
                event=event,
                best__gt=0,
                person_id__in=wca_ids,
            )
            .order_by("person_id", "best")
            .distinct("person_id")
            .values_list("id")
        )
        results = Result.objects.filter(pk__in=result_ids).order_by("best")
        return results[:limit]


class RegionalRankingAverageAPIView(RankingBaseAPIView):
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["rank_type"] = "average"
        return context

    def get_queryset(self):
        region = self.kwargs.get("region_id")
        event = self.get_event()
        limit = self.get_limit()
        wca_ids = User.objects.filter(
            region=region, socialaccount__provider=WCA_PROVIDER, wca_id__isnull=False
        ).values_list("wca_id")
        result_ids = (
            Result.objects.filter(
                country_id=PH_COUNTRY_ID,
                event=event,
                average__gt=0,
                person_id__in=wca_ids,
            )
            .order_by("person_id", "average")
            .distinct("person_id")
            .values_list("id")
        )
        results = Result.objects.filter(pk__in=result_ids).order_by("average")
        return results[:limit]


class UserRegionUpdateAPIView(UpdateAPIView):
    serializer_class = UserRegionUpdateSerializer
    queryset = User.objects.none()
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super().check_permissions(request)
        user = self.get_object()

        if user.is_staff or user.is_superuser:
            return

        if user.region:
            self.permission_denied(
                request,
                message=(
                    "Not allowed to set region more than once. "
                    "Send a region update request (only allowed once a year.)"
                ),
            )

        return super().update(request, *args, **kwargs)


class RegionUpdateRequestListCreateAPIView(ListCreateAPIView):
    serializer_class = RegionUpdateRequestSerializer
    queryset = RegionUpdateRequest.objects.order_by("-created_at")
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        last_request = request.user.region_update_requests.order_by(
            "-created_at"
        ).first()

        if last_request and last_request.created_at.year == timezone.now().year:
            self.permission_denied(request, message="You can only request once a year.")

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

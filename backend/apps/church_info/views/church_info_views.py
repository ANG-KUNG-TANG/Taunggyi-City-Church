from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.church_info.selectors.church_info_selectors import (
    get_published_church_information,
)
from apps.church_info.serializers.church_info_serializers import (
    PublicChurchInformationSerializer,
)


class PublicChurchInformationView(APIView):
    """
    Return approved public church information without authentication.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        church_information = get_published_church_information()

        if church_information is None:
            return Response(
                {"detail": "Published church information not found."},
                status=404,
            )

        serializer = PublicChurchInformationSerializer(church_information)
        return Response(serializer.data, status=200)

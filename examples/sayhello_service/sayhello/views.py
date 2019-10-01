from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class SayHelloViewSet(APIView):
    """
    Say Hello to the nice audience.
    """
    def get(self, request, format=None):
        return Response("Hello Djangocon")

    permission_classes = (AllowAny, )

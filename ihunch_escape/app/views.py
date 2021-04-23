from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .predictor import iHunchPredictor


class Upload(APIView):
    parser_class = (FileUploadParser,)
    predictor = iHunchPredictor()

    def post(self, request, format=None):
        file_obj = request.FILES['file']
        pred = self.predictor.predict(file_obj.read())
        return Response(pred, status=status.HTTP_200_OK)

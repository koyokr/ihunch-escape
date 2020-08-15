from django.shortcuts import render
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .serializers import UploadSerializer
from .predictor import iHunchPredictor


class Upload(APIView):
    parser_class = (FileUploadParser,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.predictor = iHunchPredictor()

    def post(self, request, format=None):
        serializer = UploadSerializer(data=request.FILES)
        if serializer.is_valid():
            img_bytes = request.FILES['file'].read()
            pred = self.predictor.predict(img_bytes)
            return Response(pred, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

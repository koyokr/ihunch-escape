from django.shortcuts import render
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import File
from .serializers import FileSerializer

from .predictor import iHunchPredictor
# Create your views here.


class FileUploadView(APIView):
    parser_class = (FileUploadParser,)

    def post(self, request, *args, **kwargs):
        file_serializer = FileSerializer(data=request.FILES)
        if file_serializer.is_valid():
            img_bytes = request.FILES['file'].read()
            pred = iHunchPredictor().predict(img_bytes)
            return Response(pred, status=status.HTTP_200_OK)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

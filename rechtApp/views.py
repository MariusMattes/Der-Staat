from django.shortcuts import render, redirect
from django.http import HttpResponse
import os
import json
from django.http import JsonResponse


def test_views(request):
        return render(request, 'rechtApp/test.html')


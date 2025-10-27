from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("Moin")
# Create your views here.

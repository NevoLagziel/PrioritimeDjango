from django.shortcuts import render
from django.http import HttpResponse
from .models import db_try


def index(request):
    return HttpResponse("Hello, world. You're at the k")


def get_somthing(request):
    myquery = {"account_id": 371138}
    somthing = db_try.find(myquery)
    return HttpResponse(somthing)


# Create your views here.

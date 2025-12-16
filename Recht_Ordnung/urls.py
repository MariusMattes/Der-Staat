"""
URL configuration for Recht_Ordnung project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples: 
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf 
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from rechtApp import views

#ro/o = der pfad in der Adressleiste
#test_views = name der Funktion in der views.py
#name="test" = interner name

urlpatterns = [
    path('ro/login', views.login, name='login'),
    path('ro/logout', views.logout, name='logout'),
    path('ro/registrieren', views.registrieren, name='registrieren'),
    path('ro/test', views.test_views, name="test"), 
    path('ro/profilseite', views.profilseite, name='profilseite'),
    path('ro/strafen', views.strafen, name='strafen'),
    path('ro/bussgelder', views.bussgelder, name='bussgelder'),
    path('ro/urteile', views.urteile, name='urteile'),
    path('ro/gesetze', views.gesetze, name='gesetze'),
    path("ro/gesetze/erstellen", views.gesetzErlassen, name="gesetzErlassen"),
    path("ro/gesetze/entwurf/<int:gesetz_id>", views.gesetzFreigeben, name="gesetzFreigeben"),
    path("ro/vorstrafen_api/<str:buerger_id>", views.vorstrafen_api, name="vorstrafen_api"),
    path("ro/gesetz_api/<int:gesetz_id>", views.gesetz_api, name="gesetz_api"),
    path("backup", views.backup, name="backup"),
]

"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]
"""
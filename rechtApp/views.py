from django.shortcuts import render, redirect
from django.http import HttpResponse
import os
import json
from django.http import JsonResponse
from django.conf import settings

#Allgemeiner Datenbankpfad
dataDir = os.path.join(settings.BASE_DIR, 'rechtApp', 'static', 'datenbank')

# Einzelne JSON-Dateien
gesetzeJsonPfad = os.path.join(dataDir, 'gesetze.json')
bussgelderJsonPfad = os.path.join(dataDir, 'bussgelder.json')
strafenJsonPfad = os.path.join(dataDir, 'strafen.json')
urteileJsonPfad = os.path.join(dataDir, 'urteile.json')

#Hilfsfunktionen
def lade_json(pfad):
    try:
        with open(pfad, 'r', encoding='utf-8') as f:
            daten = json.load(f)
        return daten
    except FileNotFoundError:
        print(f"Datei nicht gefunden: {pfad}")
        return []


def test_views(request):
        return render(request, 'rechtApp/ztest.html')

#Hauptseite-HTML
def hauptseite(request):
    return render(request, 'rechtApp/hauptseite.html')


# Strafen-HTML
def strafen(request):
    data = lade_json(strafenJsonPfad)
    return render(request, 'rechtApp/strafen.html', {'strafen': data})

# Bußgelder-HTML
def bussgelder(request):
    data = lade_json(bussgelderJsonPfad)
    return render(request, 'rechtApp/bussgelder.html', {'bussgelder': data})

# Urteile-HTML
def urteile(request):
    data = lade_json(urteileJsonPfad)
    return render(request, 'rechtApp/urteile.html', {'urteile': data})

# Gesetze-HTML
def gesetze(request):
    data = lade_json(gesetzeJsonPfad)
    return render(request, 'rechtApp/gesetze.html', {'gesetze': data})
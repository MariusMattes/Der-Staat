from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
import os
import json
from django.http import JsonResponse
from django.conf import settings
from lxml import etree as ET
import requests
from django.views.decorators.csrf import csrf_exempt #für testzwecke
from django.views.decorators.http import require_POST #für testzwecke
 
#Allgemeiner Datenbankpfad
#S
allgemeinerPfad = os.path.join(settings.BASE_DIR, 'rechtApp', 'static', 'datenbank')

#Einzelne JSON-Dateien
#S
gesetzeJsonPfad = os.path.join(allgemeinerPfad, 'gesetze.json')
bussgelderJsonPfad = os.path.join(allgemeinerPfad, 'bussgelder.json')
strafenJsonPfad = os.path.join(allgemeinerPfad, 'strafen.json')
urteileJsonPfad = os.path.join(allgemeinerPfad, 'urteile.json')
benutzerJsonPfad = os.path.join(allgemeinerPfad, 'benutzer.json')
arbeitQualiJsonPfad = os.path.join(allgemeinerPfad, 'arbeit_qualifikation.json') #nur für testzwecke


#Einzelne XML-Datei
#S
gesetzeXmlPfad = os.path.join(allgemeinerPfad,'gesetze.xml')
gesetzentwurfXmlPfad = os.path.join(allgemeinerPfad,'gesetzentwurf.xml')

#A
#Bekannte Schnittstellen
MELDEWESEN_API_URL = "http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/personenstandsregister_api" #Benötigt bürger-Id, holt ... bürger-id (zumindest stand jetzt :D)
ARBEIT_API_URL = "http://[2001:7c0:2320:2:f816:3eff:fe61:30b1]/ro/arbeit/qualifikation_api"#BW Cloud Server Andre für testzwecke, später von der gruppe arbeit

 
#A
def hole_ID_aus_URL(request):
    buerger_id = request.GET.get("buerger_id")# HIER wird sie aus der URL gelesen, es können so auch andere parameter ausgelesen werden

    if not buerger_id:
        return HttpResponseBadRequest("Fehlende buerger_id")
    
#A 
def hole_buergerdaten(buerger_id: str): #dict wird erwartet
    payload = {"buerger_id": buerger_id}

    try:
        response = requests.post(MELDEWESEN_API_URL, json=payload, timeout=5) #Wenn POST erwartet wird
        response = requests.get(MELDEWESEN_API_URL, params=payload, timeout=5) #Wwenn GET erwartet wird
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None

#A
def hole_qualifikation_von_arbeit(benutzer_id: int):
    payload = {"id": benutzer_id}

    try:
        response = requests.post(ARBEIT_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        daten = response.json()
        print(daten)
        return daten.get("qualifikation", [])
    except requests.RequestException:
        return []

#Hilfsfunktionen
#S
def ladeJson(pfad):
    try:
        with open(pfad, 'r', encoding='utf-8') as f:
            daten = json.load(f)
        return daten
    except FileNotFoundError:
        print(f"Datei nicht gefunden: {pfad}")
        return []
    
def xmlStrukturierenGesetze():
    parser = ET.XMLParser(remove_blank_text=True)
    return ET.parse(gesetzeXmlPfad, parser)

def xmlStrukturierenGesetzentwurf():
    parser = ET.XMLParser(remove_blank_text=True)
    return ET.parse(gesetzentwurfXmlPfad, parser)


def ladeBenutzer():
    try:
        with open(benutzerJsonPfad, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def speicherBenutzer(daten):
    with open(benutzerJsonPfad, 'w', encoding='utf-8') as f:
        json.dump(daten, f, indent=4, ensure_ascii=False)

#Test-HTML
#S
def test_views(request):
        return render(request, 'rechtApp/ztest.html')


#Hauptseite-HTML
#S
def hauptseite(request):
    return render(request, 'rechtApp/hauptseite.html')


# Strafen-HTML
#S
def strafen(request):
    data = ladeJson(strafenJsonPfad) #Beschreibung sollte aus GesetzID geholt werden bei der strafen.json
    return render(request, 'rechtApp/strafen.html', {'strafen': data})

# Bußgelder-HTML
# S und A
def bussgelder(request):
    qualifkation = request.session.get('qualifikation', []) 
    data = ladeJson(bussgelderJsonPfad)
    if "Polizist" not in qualifkation:
        return HttpResponse("""
                        <script>
                            alert("Schleich di, du bist kein Polizist!");
                            window.history.back();
                        </script>
                        """)
    return render(request, 'rechtApp/bussgelder.html', {'bussgelder': data})

# Urteile-HTML
#S und A
def urteile(request):
    qualifkation = request.session.get('qualifikation', []) 
    data = ladeJson(urteileJsonPfad)
    if "Richter" not in qualifkation:
        return HttpResponse("""
                        <script>
                            alert("Schleich di, du bist kein Richter!");
                            window.history.back();
                        </script>
                        """)
    return render(request, 'rechtApp/urteile.html', {'urteile': data})

# Gesetze-HTML 
#S
def ladeGesetze():
    if not os.path.exists(gesetzeXmlPfad):
        return []

    tree = xmlStrukturierenGesetze()
    root = tree.getroot()
    
    gesetze_liste = []
    for gesetz in root.xpath('//gesetz'):
        gesetze_liste.append({
            'id': gesetz.find('id').text,
            'titel': gesetz.find('titel').text,
            'beschreibung': gesetz.find('beschreibung').text,
            'strafe': gesetz.find('strafe').text,
            'bussgeld': gesetz.find('bussgeld').text,
        })

    return gesetze_liste

#M
def ladeGesetzentwurf():
    if not os.path.exists(gesetzentwurfXmlPfad):
        return []

    tree = xmlStrukturierenGesetzentwurf()
    root = tree.getroot()
    
    gesetze_liste = []
    for gesetz in root.xpath('//gesetz'):
        gesetze_liste.append({
            'id': gesetz.find('id').text,
            'titel': gesetz.find('titel').text,
            'beschreibung': gesetz.find('beschreibung').text,
            'strafe': gesetz.find('strafe').text,
            'bussgeld': gesetz.find('bussgeld').text,
            'zustimmung': gesetz.find('zustimmung').text
        })

    return gesetze_liste

#S und M
def gesetzErlassen(request): 
    if request.method == "POST":
        titel = request.POST.get("titel")
        beschreibung = request.POST.get("beschreibung")
        bussgeld = request.POST.get("bussgeld")
        strafe = request.POST.get("strafe")

        tree = xmlStrukturierenGesetzentwurf()
        root = tree.getroot()

        gesetze = root.findall("gesetz")
        if gesetze:
            letzte_id = int(gesetze[-1].find("id").text)
            neue_id = letzte_id + 1
        else:
            neue_id = 1

        neues_gesetz = ET.SubElement(root, "gesetz")
        ET.SubElement(neues_gesetz, "id").text = str(neue_id)
        ET.SubElement(neues_gesetz, "titel").text = titel
        ET.SubElement(neues_gesetz, "beschreibung").text = beschreibung
        ET.SubElement(neues_gesetz, "bussgeld").text = bussgeld
        ET.SubElement(neues_gesetz, "strafe").text = str(strafe)
        ET.SubElement(neues_gesetz, "zustimmung").text = "0"

        tree.write(gesetzentwurfXmlPfad, encoding="utf-8", xml_declaration=True, pretty_print=True)

        gesetzentwurf_liste = ladeGesetzentwurf()
        gesetze_liste = ladeGesetze()

        return render(request, "rechtApp/gesetze.html", {
            "gesetze": gesetze_liste,
            "gesetzentwurf": gesetzentwurf_liste,
            "qualifikation": request.session.get('qualifikation', []),
        })
        
    return render(request, "rechtApp/gesetze.html", {"gesetze": gesetze_liste})

#M
def gesetzFreigeben(request, gesetz_id):
    if request.method == "POST" and request.POST.get("zustimmung") == "ja":
        benutzer_id = request.session.get("benutzer_id")

        # 1. Prüfen: ist der Benutzer eingeloggt und Legislative?
        if not benutzer_id or not ist_legislative(benutzer_id):
            return HttpResponse("""
                <script>
                    alert("Du bist nicht berechtigt, abzustimmen.");
                    window.history.back();
                </script>
            """)

        # 2. Gesetzentwurf laden
        tree_entwurf = xmlStrukturierenGesetzentwurf()
        root_entwurf = tree_entwurf.getroot()

        for gesetz in root_entwurf.findall("gesetz"):
            if gesetz.find("id").text == str(gesetz_id):
                # 3. Liste der bereits Abstimmenden auslesen/erzeugen
                abgestimmt_el = gesetz.find("abgestimmt_ids")
                if abgestimmt_el is None:
                    abgestimmt_el = ET.SubElement(gesetz, "abgestimmt_ids")
                    abgestimmt_el.text = ""

                bereits_abgestimmt = set(
                    filter(None, (abgestimmt_el.text or "").split(","))
                )

                # 4. Prüfen: hat dieser Benutzer schon abgestimmt?
                if str(benutzer_id) in bereits_abgestimmt:
                    tree_entwurf.write(
                        gesetzentwurfXmlPfad,
                        encoding="utf-8",
                        xml_declaration=True,
                        pretty_print=True,
                    )
                    return HttpResponse("""
                        <script>
                            alert("Du hast bereits abgestimmt.");
                            window.history.back();
                        </script>
                    """)

                # 5. Benutzer-ID hinzufügen
                bereits_abgestimmt.add(str(benutzer_id))
                abgestimmt_el.text = ",".join(bereits_abgestimmt)

                # 6. Zustimmung hochzählen
                zustimmung_el = gesetz.find("zustimmung")
                aktuelle_zustimmung = int(zustimmung_el.text or "0")
                neue_zustimmung = aktuelle_zustimmung + 1
                zustimmung_el.text = str(neue_zustimmung)

                # 7. Wenn mindestens 3 Stimmen → in gesetze.xml übernehmen
                if neue_zustimmung >= 3:
                    # Normale Gesetze laden
                    try:
                        tree_gesetze = xmlStrukturierenGesetze()
                        root_gesetze = tree_gesetze.getroot()
                    except FileNotFoundError:
                        root_gesetze = ET.Element("gesetze")
                        tree_gesetze = ET.ElementTree(root_gesetze)

                    vorhandene_gesetze = root_gesetze.findall("gesetz")
                    if vorhandene_gesetze:
                        letzte_id = int(vorhandene_gesetze[-1].find("id").text)
                        neue_id = letzte_id + 1
                    else:
                        neue_id = 1

                    # Neues Gesetz in gesetze.xml anlegen
                    neues_gesetz = ET.SubElement(root_gesetze, "gesetz")
                    ET.SubElement(neues_gesetz, "id").text = str(neue_id)
                    ET.SubElement(neues_gesetz, "titel").text = (gesetz.find("titel").text or "")
                    ET.SubElement(neues_gesetz, "beschreibung").text = (gesetz.find("beschreibung").text or "")
                    ET.SubElement(neues_gesetz, "bussgeld").text = (gesetz.find("bussgeld").text or "0")
                    ET.SubElement(neues_gesetz, "strafe").text = (gesetz.find("strafe").text or "0")

                    # In gesetze.xml speichern
                    tree_gesetze.write(
                        gesetzeXmlPfad,
                        encoding="utf-8",
                        xml_declaration=True,
                        pretty_print=True,
                    )

                    # Entwurf aus gesetzentwurf.xml entfernen
                    root_entwurf.remove(gesetz)

                # 8. Entwurfsdatei (mit Zustimmungen / Abstimmer-Liste) speichern
                tree_entwurf.write(
                    gesetzentwurfXmlPfad,
                    encoding="utf-8",
                    xml_declaration=True,
                    pretty_print=True,
                )
                break

    return redirect("gesetze")


#S
def gesetze(request):
    gesetze_liste = ladeGesetze()
    gesetzentwurf_liste = ladeGesetzentwurf()
    qualifikation = request.session.get('qualifikation', [])

    return render(request, "rechtApp/gesetze.html", {
        "gesetze": gesetze_liste,
        "gesetzentwurf": gesetzentwurf_liste,
        "qualifikation": qualifikation,
    })


#Login-HTML
#S und A
#Login mit Quali von eigener benutzer.json
# def login(request):
#     if request.method == 'POST':
#         benutzername = request.POST['benutzername']
#         passwort = request.POST['passwort']

#         benutzer_liste = ladeBenutzer()
#         if not benutzer_liste:
#             return HttpResponse("""
#                 <script>
#                     alert("Keine Benutzer vorhanden");
#                     window.history.back();
#                 </script>
#             """)

#         gefundener_benutzer = None
#         benutzername_existiert = False
#         for benutzer in benutzer_liste:
#             if benutzer['benutzername'] == benutzername:
#                 benutzername_existiert = True
#                 if benutzer['passwort'] == passwort:
#                     gefundener_benutzer = benutzer
#                     qualifikation = benutzer.get("qualifikation", [])
#                     request.session['qualifikation'] = qualifikation
#                     request.session['benutzer_id'] = benutzer['id']
#                     print(request.session.get('qualifikation'))
#                 break

#         if not benutzername_existiert:
#             return HttpResponse("""
#                 <script>
#                     alert("Benutzername existiert nicht");
#                     window.history.back();
#                 </script>
#             """)

#         if gefundener_benutzer is None:
#             return HttpResponse("""
#                 <script>
#                     alert("Falsches Passwort");
#                     window.history.back();
#                 </script>
#             """)

#         return redirect('hauptseite')

#     return render(request, 'rechtApp/login.html')

#A und S, quali wird über schnittstelle geholt
def login(request):
    if request.method == 'POST':
        benutzername = request.POST['benutzername']
        passwort = request.POST['passwort']

        benutzer_liste = ladeBenutzer()
        if not benutzer_liste:
            return HttpResponse("""
                <script>
                    alert("Keine Benutzer vorhanden");
                    window.history.back();
                </script>
            """)

        gefundener_benutzer = None
        benutzername_existiert = False

        for benutzer in benutzer_liste:
            if benutzer['benutzername'] == benutzername:
                benutzername_existiert = True
                if benutzer['passwort'] == passwort:
                    gefundener_benutzer = benutzer

                    # ID wird immer noch aus benutzer.json geholt
                    benutzer_id = benutzer['id']
                    print(benutzer_id)
                    request.session['benutzer_id'] = benutzer_id

                    # quali über schnittstelle
                    qualifikation = hole_qualifikation_von_arbeit(benutzer_id)
                    request.session['qualifikation'] = qualifikation

                    print("Qualifikation aus Arbeit-API:", request.session.get('qualifikation'))
                break

        if not benutzername_existiert:
            return HttpResponse("""
                <script>
                    alert("Benutzername existiert nicht");
                    window.history.back();
                </script>
            """)

        if gefundener_benutzer is None:
            return HttpResponse("""
                <script>
                    alert("Falsches Passwort");
                    window.history.back();
                </script>
            """)

        return redirect('hauptseite')

    return render(request, 'rechtApp/login.html')


#Registrieren-HTML
#S
def registrieren(request):
    if request.method == 'POST':
        benutzername = request.POST['benutzername']
        email = request.POST['email']
        passwort = request.POST['passwort']
        pw_wiederholen = request.POST['passwort_wiederholen']

        if passwort != pw_wiederholen:
            return HttpResponse("""
                <script>
                    alert("Passwörter stimmen nicht überein");
                    window.history.back();
                </script>
            """)

        benutzer_liste = ladeBenutzer()

        benutzername_existiert = False
        email_existiert = False
        for benutzer in benutzer_liste:
            if benutzer['benutzername'] == benutzername:
                benutzername_existiert = True
            if benutzer['email'] == email:
                email_existiert = True

        if benutzername_existiert:
            return HttpResponse("""
                <script>
                    alert("Benutzername bereits vergeben");
                    window.history.back();
                </script>
            """)

        if email_existiert:
            return HttpResponse("""
                <script>
                    alert("E-Mail bereits vergeben");
                    window.history.back();
                </script>
            """)

        if len(benutzer_liste) == 0:
            neue_id = 1
        else:
            letzte_id = benutzer_liste[-1]['id'] #-1 und 'id' gleich letzte ID
            neue_id = letzte_id + 1

        neuer_benutzer = {
            'id': neue_id,
            'benutzername': benutzername,
            'email': email,
            'passwort': passwort
        }

        benutzer_liste.append(neuer_benutzer)
        speicherBenutzer(benutzer_liste)

        return redirect('login')

    return render(request, 'rechtApp/registrieren.html')

def logout(request):
    return redirect('login')

#A
def ist_polizist(id_benutzer):
    try:
        with open(benutzerJsonPfad, "r") as f:
            benutzer_liste = json.load(f)
    except FileNotFoundError:
        return False

    for benutzer in benutzer_liste:
        if (
            benutzer.get("id") == id_benutzer
            and "Polizist" in benutzer.get("qualifikation", [])
        ):
            return True
    return False

#A
def ist_richter(id_benutzer):
    try:
        with open(benutzerJsonPfad, "r") as f:
            benutzer_liste = json.load(f)
    except FileNotFoundError:
        return False

    for benutzer in benutzer_liste:
        if (
            benutzer.get("id") == id_benutzer
            and "Richter" in benutzer.get("qualifikation", [])
        ):
            return True
    return False

#A
def ist_legislative(id_benutzer):
    try:
        with open(benutzerJsonPfad, "r") as f:
            benutzer_liste = json.load(f)
    except FileNotFoundError:
        return False

    for benutzer in benutzer_liste:
        if (
            benutzer.get("id") == id_benutzer
            and "Legislative" in benutzer.get("qualifikation", [])
        ):
            return True
    return False


# statt "ist beruf" eventuell Liste mit Berechtigungen erstellen und abgleichen ob Person in Liste? von f

def berechtigungen_abgleichen(id_benutzer):
    try:
        with open(benutzerJsonPfad, "r") as f:
            benutzer_liste = json.load(f)
    except FileNotFoundError:
        return False
    for benutzer in benutzer_liste:
        if (
            benutzer.get("id") == id_benutzer
            and "Platzhalter" in "qualifikationsliste" #vielleicht verstehe ich auch gerade falsch wie es gedacht war, könnt mich da gerne aufklären; von f
        ):
            return True
    return False


#A nur für testzwecke, der teil (o.ä.) liegt später bei team arbeit
@csrf_exempt
@require_POST
def qualifikation_api(request):
    """
    Erwartet POST mit JSON: {"id": 1}
    Antwortet mit z.B.: {"id": 1, "qualifikation": ["Polizist"]}
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "ungültiges JSON"}, status=400)

    benutzer_id = body.get("id")
    if benutzer_id is None:
        return JsonResponse({"error": "ID fehlt"}, status=400)

    daten = ladeJson(arbeitQualiJsonPfad)

    for eintrag in daten:
        if eintrag.get("id") == benutzer_id:
            print(eintrag)
            return JsonResponse({
                "id": benutzer_id,
                "qualifikation": eintrag.get("qualifikation", [])
            })

    return JsonResponse({"error": "Benutzer nicht gefunden"}, status=404)
#weniger ist mehr
# @csrf_exempt
# @require_POST
# def qualifikation_api(request):
#     body = json.loads(request.body.decode("utf-8"))
#     benutzer_id = body["id"]

#     for eintrag in ladeJson(arbeitQualiJsonPfad):
#         if eintrag.get("id") == benutzer_id:
#             return JsonResponse({
#                 "id": benutzer_id,
#                 "qualifikation": eintrag.get("qualifikation", [])
#             })

#     return JsonResponse({
#         "id": benutzer_id,
#         "qualifikation": []
#     })
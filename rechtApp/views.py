from django.shortcuts import render, redirect
from django.http import HttpResponse
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
vorstrafenJsonPfad = os.path.join(allgemeinerPfad, 'vorstrafen.json')
buergerAkteJsonPfad = os.path.join(allgemeinerPfad, 'recht_buergerakte.json')

#Einzelne XML-Datei
#S
gesetzeXmlPfad = os.path.join(allgemeinerPfad,'gesetze.xml')
gesetzentwurfXmlPfad = os.path.join(allgemeinerPfad,'gesetzentwurf.xml')

#A
#Bekannte Schnittstellen
ARBEIT_API_URL = "http://[2001:7c0:2320:2:f816:3eff:feb6:6731]:8000/api/buerger/beruf/"
# Noch nicht bekannt. eventuell mit Andres Server testen MELDEWESEN_PERSONENSUCHE_URL = "http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/personensuche_api"

def hole_beruf_von_arbeit(benutzer_id: str):
    try:
        url = f"{ARBEIT_API_URL}{benutzer_id}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        daten = response.json() # antwort sieht so aus : {"beruf": "Richter"}
        print(daten)  

        beruf = daten.get("beruf")
        if beruf:
            return beruf
        return None
    except requests.RequestException:
        return None

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
    
#A    
def lade_buergerakte(buerger_id: str):
    akten = ladeJson(buergerAkteJsonPfad)

    for akte in akten:
        if akte.get("buerger_id") == buerger_id:
            return akte
        
    return {
        "buerger_id": buerger_id,
        "vorstrafen": [],
        "bussgelder": []
    }

    
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


#Profilseite-HTML
#S
def profilseite(request):
    benutzername = request.session.get("benutzername")
    if not benutzername:
        return redirect("login")

    try:
        with open(benutzerJsonPfad, "r", encoding="utf-8") as f:
            benutzer_liste = json.load(f)
    except:
        return HttpResponse("Fehler beim Laden der Benutzerdaten.")

    benutzer_daten = None
    for b in benutzer_liste:
        if b["benutzername"] == benutzername:
            benutzer_daten = b
            break

    if not benutzer_daten:
        return HttpResponse("Benutzer konnte nicht gefunden werden.")

    try:
        with open(urteileJsonPfad, "r", encoding="utf-8") as f:
            urteile_liste = json.load(f)
    except:
        return HttpResponse("Fehler beim Laden der Urteile.")

    eigene_urteile = []
    for u in urteile_liste:
        if u["person"] == benutzername:
            eigene_urteile.append(u)

    try:
        tree = ET.parse(gesetzeXmlPfad)
        root = tree.getroot()
    except:
        return HttpResponse("Fehler beim Laden der Gesetze.")

    gesetze_dict = {}
    for g in root.findall("gesetz"):
        gid = int(g.find("id").text)
        gesetze_dict[gid] = {
            "id": gid,
            "titel": g.find("titel").text,
            "beschreibung": g.find("beschreibung").text,
            "bussgeld": int(g.find("bussgeld").text),
            "strafe": int(g.find("strafe").text),
        }

    try:
        with open(strafenJsonPfad, "r", encoding="utf-8") as f:
            strafen_liste = json.load(f)
    except:
        return HttpResponse("Fehler beim Laden der Strafen.")

    strafen_dict = {}
    for s in strafen_liste:
        strafen_dict[s["id"]] = s

    try:
        with open(bussgelderJsonPfad, "r", encoding="utf-8") as f:
            bussgelder_liste = json.load(f)
    except:
        return HttpResponse("Fehler beim Laden der Bußgelder.")

    bussgelder_dict = {}
    for bg in bussgelder_liste:
        bussgelder_dict[bg["id"]] = bg

    urteile_komplett = []

    for u in eigene_urteile:

        gesetz = None
        if u["gesetz_id"] in gesetze_dict:
            gesetz = gesetze_dict[u["gesetz_id"]]

        if u["bussgeld_id"]:
            if u["bussgeld_id"] in bussgelder_dict:
                bussgeld = bussgelder_dict[u["bussgeld_id"]]
            else:
                bussgeld = None
        else:
            bussgeld = None

        if u["strafen_id"]:
            if u["strafen_id"] in strafen_dict:
                strafe = strafen_dict[u["strafen_id"]]
            else:
                strafe = None
        else:
            strafe = None

        urteile_komplett.append({
            "id": u["id"],
            "richter": u["richter"],
            "gesetz": gesetz,
            "bussgeld": bussgeld,
            "strafe": strafe
        })

    beruf = request.session.get("beruf", "Unbekannt")

    return render(request, "rechtApp/profilseite.html", {
        "benutzer": benutzer_daten,
        "beruf": beruf,
        "urteile": urteile_komplett,
    })






# Strafen-HTML
#S
def strafen(request):
    data = ladeJson(strafenJsonPfad) #Beschreibung sollte aus GesetzID geholt werden bei der strafen.json
    return render(request, 'rechtApp/strafen.html', {'strafen': data})

# Bußgelder-HTML
# S und A
def bussgelder(request):
    beruf = request.session.get('beruf') 
    data = ladeJson(bussgelderJsonPfad)
    if beruf != "Polizist":
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
    beruf = request.session.get('beruf') 
    data = ladeJson(urteileJsonPfad)
    if beruf != "Richter":
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
    #A
    for gesetz in root.xpath('//gesetz'):
        api_el = gesetz.find('api_relevant')
        api_werte = [] #wenn es das el nicht geben soltle = leere liste
        if api_el is not None:
            api_werte = [
                wert_el.text
                for wert_el in api_el.findall('wert')
                if wert_el.text
            ]

        gesetze_liste.append({
            'id': gesetz.find('id').text,
            'titel': gesetz.find('titel').text,
            'beschreibung': gesetz.find('beschreibung').text,
            'strafe': gesetz.find('strafe').text,
            'bussgeld': gesetz.find('bussgeld').text,
            'api_relevant': api_werte,
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
            "beruf": request.session.get('beruf'),
        })
        
    gesetze_liste = ladeGesetze()
    gesetzentwurf_liste = ladeGesetzentwurf()
    return render(request, "rechtApp/gesetze.html", {
        "gesetze": gesetze_liste,
        "gesetzentwurf": gesetzentwurf_liste,
        "beruf": request.session.get('beruf'),
    })

#M
def gesetzFreigeben(request, gesetz_id):
    if request.method == "POST" and request.POST.get("zustimmung") == "ja":
        benutzer_id = request.session.get("benutzer_id")
        beruf = request.session.get("beruf")

        # 1. Prüfen: ist der Benutzer eingeloggt und Legislative?
        if not benutzer_id or beruf != "Legislative":
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
    beruf = request.session.get('beruf')

    return render(request, "rechtApp/gesetze.html", {
        "gesetze": gesetze_liste,
        "gesetzentwurf": gesetzentwurf_liste,
        "beruf": beruf,
    })


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
                    
                    # benutzername in session speichern
                    request.session['benutzername'] = benutzername

                    # quali über schnittstelle
                    beruf = hole_beruf_von_arbeit(benutzer_id)
                    request.session['beruf'] = beruf

                    print("Beruf aus Arbeit-API:", request.session.get('beruf'))
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

        return redirect('profilseite')

    return render(request, 'rechtApp/login.html')

def logout(request):
    return redirect('login')

#A 
def vorstrafen_api(request, buerger_id):
    akten = ladeJson(buergerAkteJsonPfad)

    for akte in akten:
        if akte.get("buerger_id") == buerger_id:
            vorstrafen = akte.get("vorstrafen", [])
            return JsonResponse({
                "buerger_id": buerger_id,
                "hat_vorstrafen": bool(vorstrafen),
                "vorstrafen": vorstrafen
            }, status=200)

    # keine akte = keine vorstrafen
    return JsonResponse({
        "buerger_id": buerger_id,
        "hat_vorstrafen": False,
        "vorstrafen": []
    }, status=200)

#A
def gesetz_api(request, gesetz_id):
    gesetze = ladeGesetze()

    for gesetz in gesetze:
        if gesetz.get("id") == str(gesetz_id):
            api_werte = gesetz.get("api_relevant", [])
            return JsonResponse({
                "gesetz_id": gesetz.get("id"),
                "titel": gesetz.get("titel"),
                "werte": api_werte,
            }, status = 200)

    return JsonResponse({
        "fehler": "Gesetz nicht gefunden",
        "gesetz_id": str(gesetz_id),
    }, status=404)

#A
def suche_buerger_id_beim_meldewesen(vorname: str, nachname: str, geburtsdatum: str):

    payload = {
        "vorname": vorname,
        "nachname": nachname,
        "geburtsdatum": geburtsdatum,  
    }

    try:
        response = requests.post(MELDEWESEN_PERSONENSUCHE_URL, json=payload, timeout=5)

        # falls meldewesen 404 zurückgibt -> keine Person
        if response.status_code == 404:
            return None

        response.raise_for_status()
        daten = response.json() #hier sollte ein json zurückkommen
    except requests.RequestException:
        return None

    buerger_id = daten.get("buerger_id")

    if buerger_id:
        return buerger_id

    return None

#A
def polizei_personensuche(request):
    buerger_id = None
    fehlermeldung = None

    if request.method == "POST":
        vorname = request.POST.get("vorname", "")
        nachname = request.POST.get("nachname", "")
        geburtsdatum = request.POST.get("geburtsdatum", "")

        if vorname and nachname and geburtsdatum:
            buerger_id = suche_buerger_id_beim_meldewesen(vorname, nachname, geburtsdatum)
            if buerger_id is None:
                fehlermeldung = "Keine Person gefunden."
        else:
            fehlermeldung = "Bitte alle Felder ausfüllen."

    return render(request, "rechtApp/polizei_personensuche.html", {
        "buerger_id": buerger_id,
        "fehlermeldung": fehlermeldung,
    })


# So könnte die gegenstelle bei team meldewesen aussehen
# @csrf_exempt
# @require_POST
# def personensuche_api(request):
#     body = json.loads(request.body.decode("utf-8"))
#     vorname = body["vorname"]
#     nachname = body["nachname"]
#     geburtsdatum = body["geburtsdatum"]

#     for person in ladeJson(personenregisterJsonPfad): #hier euer entsprechendes register
#         if (
#             person.get("vorname") == vorname and
#             person.get("nachname_geburt") == nachname and
#             person.get("geburtsdatum") == geburtsdatum
#         ):
#             return JsonResponse({"buerger_id": person.get("buerger_id")}, status=200)

#     return JsonResponse({"error": "keine_person_gefunden"}, status=404)


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
from pathlib import Path
from datetime import datetime, date, timedelta
import zipfile
import io
import math
from urllib.parse import unquote #für meldewesenlogin
from .jwt_tooling import decode_jwt # für meldewesenlogin #WICHTIG! pip install PyJWT NICHT JWT

import logging #logbuch für fehlersuche
logger = logging.getLogger(__name__) 

from.jwt_tooling import create_jwt #für testzwecke
token = create_jwt("polizist1") #für testzwecke
print(token) #für testzwecke
#http://127.0.0.1:8000/ro/jwt-login?token=

#Allgemeiner Datenbankpfad
#S
allgemeinerPfad = os.path.join(settings.BASE_DIR, 'rechtApp', 'static', 'datenbank')

#Einzelne JSON-Dateien
#S
gesetzeJsonPfad = os.path.join(allgemeinerPfad, 'gesetze.json')
anzeigenJsonPfad = os.path.join(allgemeinerPfad, 'anzeigen.json')
urteileJsonPfad = os.path.join(allgemeinerPfad, 'urteile.json')
benutzerJsonPfad = os.path.join(allgemeinerPfad, 'benutzer.json')
vorstrafenJsonPfad = os.path.join(allgemeinerPfad, 'vorstrafen.json')

#Einzelne XML-Datei
#S
gesetzeXmlPfad = os.path.join(allgemeinerPfad,'gesetze.xml')
gesetzentwurfXmlPfad = os.path.join(allgemeinerPfad,'gesetzentwurf.xml')

#A
#Bekannte Schnittstellen
ARBEIT_API_URL = "http://[2001:7c0:2320:2:f816:3eff:feb6:6731]:8000/api/buerger/beruf/"
Einwohnermeldeamt_API_URL = "http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/api/recht-ordnung/personensuche"
BANK_API_URL = "http://[2001:7c0:2320:2:f816:3eff:fe82:34b2]:8000/bank/strafeMelden"
HAFTSTATUS_SETZEN_EINWOHNERMELDEAMT = "[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/api/recht-ordnung/haftstatus"
ARBEIT_LEGISLATIVE_API = "http://[2001:7c0:2320:2:f816:3eff:feb6:6731]:8000/api/personenliste/legislative"

#A
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

def hole_buerger_id(vorname, nachname, geburtsdatum):

    daten = {
        "vorname": vorname,
        "nachname": nachname,
        "geburtsdatum": geburtsdatum
    }

    try:
        response = requests.post(Einwohnermeldeamt_API_URL, json=daten, timeout=5)
        print("Antwort Einwohnermeldeamt:", response)
        if response.status_code == 200:
            return response.json().get("buerger_id")

    except Exception as e:
        print("Fehler bei Bürger-ID-Abfrage:", e)

    return None

#A
def hole_anzahl_legislative():
    response = requests.get(ARBEIT_LEGISLATIVE_API, timeout=5)
    response.raise_for_status()
    daten = response.json()
    return len(daten.get("personen", []))

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
def lade_vorstrafen_daten():
    daten = ladeJson(vorstrafenJsonPfad)
    if not isinstance(daten, list):
        return []
    return daten

#A
def speichere_vorstrafen_daten(daten):
    with open(vorstrafenJsonPfad, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=4)
    
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

#A
def fuege_vorstrafe_hinzu(buerger_id: str, gesetz_id: int, datum_urteil: str):
    daten = lade_vorstrafen_daten()

    akte = None
    for a in daten:
        if str(a.get("buerger_id")) == str(buerger_id):
            akte = a
            break

    if akte is None:
        akte = {"buerger_id": str(buerger_id), "vorstrafen": []}
        daten.append(akte)

    if "vorstrafen" not in akte or not isinstance(akte["vorstrafen"], list):
        akte["vorstrafen"] = []

    akte["vorstrafen"].append({
        "gesetz_id": int(gesetz_id),
        "datum_urteil": datum_urteil
    })

    speichere_vorstrafen_daten(daten)


#Profilseite-HTML
#S
def profilseite(request):

    # ==============================
    # NEU: Bürger-ID aus JWT-Session (Meldewesen)
    # ==============================
    buerger_id = request.session.get("user_id")
    if not buerger_id:
        return HttpResponse("Nicht eingeloggt.", status=401)

    # ==============================
    # ALT: Lokaler Benutzername aus eigener Benutzerverwaltung
    # → obsolet, da Login künftig über Meldewesen/JWT erfolgt
    # ==============================
    # benutzername = request.session.get("benutzername")
    # if not benutzername:
    #     return redirect("login")

    # try:
    #     with open(benutzerJsonPfad, "r", encoding="utf-8") as f:
    #         benutzer_liste = json.load(f)
    # except:
    #     return HttpResponse("Fehler beim Laden der Benutzerdaten.")

    # benutzer_daten = None
    # for eintrag in benutzer_liste:
    #     if eintrag["benutzername"] == benutzername:
    #         benutzer_daten = eintrag
    #         break

    # if benutzer_daten is None:
    #     return HttpResponse("Benutzer konnte nicht gefunden werden.")

    # ==============================
    # Urteile laden (unverändert)
    # ==============================
    try:
        with open(urteileJsonPfad, "r", encoding="utf-8") as f:
            urteile_liste = json.load(f)
    except:
        return HttpResponse("Fehler beim Laden der Urteile.")

    eigene_urteile = []

    # ==============================
    # ALT: Filter nach benutzername
    # → obsolet
    # ==============================
    # for urteil in urteile_liste:
    #     if urteil["person"] == benutzername:
    #         eigene_urteile.append(urteil)

    # ==============================
    # NEU: Filter nach buerger_id
    # ==============================
    for urteil in urteile_liste:
        if str(urteil.get("buerger_id")) == str(buerger_id):
            eigene_urteile.append(urteil)

    if not os.path.exists(gesetzeXmlPfad):
        return HttpResponse("Gesetze konnten nicht gefunden werden.")

    try:
        tree = ET.parse(gesetzeXmlPfad)
        root = tree.getroot()
    except:
        return HttpResponse("Fehler beim Laden der Gesetze.")

    gesetze_dict = {}

    for gesetz in root.findall("gesetz"):
        titel_el = gesetz.find("titel")
        beschreibung_el = gesetz.find("beschreibung")
        bussgeld_el = gesetz.find("bussgeld")
        strafe_el = gesetz.find("strafe")

        titel = titel_el.text if titel_el is not None else ""
        beschreibung = beschreibung_el.text if beschreibung_el is not None else ""
        bussgeld = int(bussgeld_el.text) if bussgeld_el is not None and bussgeld_el.text else 0
        strafe = int(strafe_el.text) if strafe_el is not None and strafe_el.text else 0

        gesetze_dict[titel] = {
            "titel": titel,
            "beschreibung": beschreibung,
            "bussgeld": bussgeld,
            "strafe": strafe
        }

    urteile_komplett = []

    for urteil in eigene_urteile:
        gesetz_name = urteil["gesetz"]
        gesetz_data = gesetze_dict.get(gesetz_name)

        urteile_komplett.append({
            "id": urteil["id"],
            "richter": urteil["richter"],
            "gesetz": gesetz_data,
            "bussgeld": urteil["bussgeld"],
            "strafe": urteil["strafe"]
        })

    beruf = request.session.get("beruf", "Unbekannt")

    return render(
        request,
        "rechtApp/profilseite.html",
        {
            # ==============================
            # ALT: lokaler Benutzer
            # "benutzer": benutzer_daten,
            # ==============================

            # NEU
            "buerger_id": buerger_id,
            "beruf": beruf,
            "urteile": urteile_komplett
        }
    )




# Anzeigen-HTML
#S
#buerger_liste = [
#    {
#        "buerger_id": "4493ffb9-1513-42f9-b709-35ebdddc0296",
#        "vorname": "Simon",
#        "nachname_geburt": "Maier",
#        "geburtsdatum": "10.10.2004"
#    },
#]

#S
@csrf_exempt
def anzeigen(request):
    beruf = request.session.get("beruf")
    if beruf not in ["Richter", "Polizist"]:
        return HttpResponse("""
            <script>
                alert("Nur Richter und Polizisten dürfen diese Seite sehen.");
                window.history.back();
            </script>
        """)

    gesetze = ladeGesetze()

    if os.path.exists(anzeigenJsonPfad):
        with open(anzeigenJsonPfad, "r", encoding="utf-8") as f:
            try:
                anzeigen_liste = json.load(f)
            except:
                anzeigen_liste = []
    else:
        anzeigen_liste = []

    buerger_id = None

    if request.method == "POST":
        action = request.POST.get("action")

        # ==========================================
        # Bürger-Suche über Meldewesen (unverändert)
        # ==========================================
        if action == "suche_buerger":
            vorname = request.POST.get("vorname", "").strip()
            nachname = request.POST.get("nachname", "").strip()
            geburtsdatum = request.POST.get("geburtsdatum", "").strip()

            buerger_id = hole_buerger_id(vorname, nachname, geburtsdatum)

            return render(request, "rechtApp/anzeigen.html", {
                "anzeigen": anzeigen_liste,
                "beruf": beruf,
                "buerger_id": buerger_id
            })

        # ==========================================
        # Neue Anzeige anlegen (unverändert)
        # ==========================================
        if action == "neue_anzeige":
            anzeigen_liste.append({
                "buerger_id": request.POST.get("anzeige_buerger_id").strip(),
                "vorname": request.POST.get("vorname").strip(),
                "gesetz_id": request.POST.get("gesetz_id") or None,
                "gesetz_titel": request.POST.get("gesetz_titel") or None,
                "begruendung": request.POST.get("begruendung") or None
            })

            with open(anzeigenJsonPfad, "w", encoding="utf-8") as f:
                json.dump(anzeigen_liste, f, ensure_ascii=False, indent=4)

            return redirect("anzeigen")

        # ==========================================
        # Anzeige entscheiden
        # ==========================================
        if action in ["zustimmen", "ablehnen"]:
            anzeige_index = int(request.POST.get("anzeige_index", -1))

            # --------------------------------------------------
            # ALT: Richter über lokalen Benutzernamen
            # → obsolet, da Authentifizierung künftig über JWT
            # --------------------------------------------------
            # richter = request.session.get("benutzername", "Unbekannt")

            # --------------------------------------------------
            # NEU: Richter = Bürger-ID aus JWT-Session
            # --------------------------------------------------
            richter = request.session.get("user_id")

            if 0 <= anzeige_index < len(anzeigen_liste):
                anzeige = anzeigen_liste.pop(anzeige_index)

                if action == "zustimmen":
                    gesetz_daten = None
                    for g in gesetze:
                        if (
                            str(g.get("id")) == str(anzeige.get("gesetz_id"))
                            or g.get("titel") == anzeige.get("gesetz_titel")
                        ):
                            gesetz_daten = g
                            break

                    if gesetz_daten:
                        if os.path.exists(urteileJsonPfad):
                            with open(urteileJsonPfad, "r", encoding="utf-8") as f:
                                try:
                                    urteile_liste = json.load(f)
                                except:
                                    urteile_liste = []
                        else:
                            urteile_liste = []

                        if urteile_liste:
                            neue_id = urteile_liste[-1]["id"] + 1
                        else:
                            neue_id = 1

                        # --------------------------------------------------
                        # ALT: Urteil mit person = Vorname
                        # → obsolet, da Identifikation jetzt über buerger_id
                        # --------------------------------------------------
                        # urteile_liste.append({
                        #     "id": neue_id,
                        #     "buerger_id": anzeige["buerger_id"],
                        #     "person": anzeige["vorname"],
                        #     "richter": richter,
                        #     "gesetz": gesetz_daten["titel"],
                        #     "bussgeld": int(gesetz_daten["bussgeld"]) if gesetz_daten.get("bussgeld") else 0,
                        #     "strafe": int(gesetz_daten["strafe"]) if gesetz_daten.get("strafe") else 0
                        # })

                        bussgeld_betrag = int(gesetz_daten["bussgeld"]) if gesetz_daten.get("bussgeld") else 0
                        strafe_jahre = int(gesetz_daten["strafe"]) if gesetz_daten.get("strafe") else 0

                        # --------------------------------------------------
                        # NEU: Urteil eindeutig über buerger_id
                        # --------------------------------------------------
                        urteile_liste.append({
                            "id": neue_id,
                            "buerger_id": anzeige["buerger_id"],
                            "richter": richter,
                            "gesetz": gesetz_daten["titel"],
                            "bussgeld": bussgeld_betrag,
                            "strafe": strafe_jahre
                        })

                        with open(urteileJsonPfad, "w", encoding="utf-8") as f:
                            json.dump(urteile_liste, f, ensure_ascii=False, indent=4)

                        #A
                        if strafe_jahre > 0:
                            datum = date.today().isoformat()
                            fuege_vorstrafe_hinzu(
                                buerger_id=anzeige["buerger_id"],
                                gesetz_id=int(anzeige["gesetz_id"]),
                                datum_urteil=datum
                            )

                            sende_haftstatus_an_meldewesen(
                                buerger_id=anzeige["buerger_id"],
                                haft_status=True
                            )

                        if bussgeld_betrag > 0:
                            sende_bussgeld_an_bank(
                                buerger_id=anzeige["buerger_id"],
                                betrag=bussgeld_betrag,
                                gesetz_id=int(anzeige["gesetz_id"])
                                if anzeige.get("gesetz_id")
                                else int(gesetz_daten["id"]),
                                gesetz_titel=gesetz_daten["titel"],
                            )
                        #/A

                else:
                    # ==========================================
                    # Anzeige abgelehnt (unverändert)
                    # ==========================================
                    ablehnPfad = os.path.join(
                        os.path.dirname(anzeigenJsonPfad),
                        "anzeigeAbgelehnt.json"
                    )

                    if os.path.exists(ablehnPfad):
                        with open(ablehnPfad, "r", encoding="utf-8") as f:
                            try:
                                abgelehnt = json.load(f)
                            except:
                                abgelehnt = []
                    else:
                        abgelehnt = []

                    anzeige["richter"] = richter
                    abgelehnt.append(anzeige)

                    with open(ablehnPfad, "w", encoding="utf-8") as f:
                        json.dump(abgelehnt, f, ensure_ascii=False, indent=4)

                with open(anzeigenJsonPfad, "w", encoding="utf-8") as f:
                    json.dump(anzeigen_liste, f, ensure_ascii=False, indent=4)

            return redirect("anzeigen")

    return render(request, "rechtApp/anzeigen.html", {
        "anzeigen": anzeigen_liste,
        "beruf": beruf,
        "buerger_id": None
    })




# Bußgelder-HTML
# S
def bussgelder(request):
    beruf = request.session.get('beruf') 
    if beruf != "Polizist":
        return HttpResponse("""
                        <script>
                            alert("Schleich di, du bist kein Polizist!");
                            window.history.back();
                        </script>
                        """)
    return render(request, 'rechtApp/bussgelder.html')

# Urteile-HTML
#S
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

                #A
                anzahl_legislative = hole_anzahl_legislative()
                print(anzahl_legislative)
                benoetigte_stimmen = math.ceil(anzahl_legislative * 0.5) #ceiling = rundet Zahl auf

                if neue_zustimmung >= benoetigte_stimmen:
                #/A
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

#Obsolet durch jwt_login() über meldewesen
#A und S, quali wird über schnittstelle geholt
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

#                     # ID wird immer noch aus benutzer.json geholt
#                     benutzer_id = benutzer['id']
#                     print(benutzer_id)
#                     request.session['benutzer_id'] = benutzer_id
                    
#                     # benutzername in session speichern
#                     request.session['benutzername'] = benutzername

#                     # quali über schnittstelle
#                     beruf = hole_beruf_von_arbeit(benutzer_id)               
#                     request.session['beruf'] = beruf

#                     print("Beruf aus Arbeit-API:", request.session.get('beruf'))

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

#         return redirect('profilseite')

#     return render(request, 'rechtApp/login.html')

#A
def jwt_login(request):
    token = request.GET.get("token")
    logger.warning("JWT_LOGIN: raw token = %s", token)

    if not token:
        logger.warning("JWT_LOGIN: kein Token übergeben")
        return HttpResponse("Kein Token", status=400)

    try:
        daten = decode_jwt(token)
        logger.warning("JWT_LOGIN: decoded payload = %s", daten)
    except Exception as e:
        logger.error("JWT_LOGIN: decode fehlgeschlagen: %s", e)
        return HttpResponse("Ungültiges Token", status=401)

    buerger_id = daten.get("user_id")
    logger.warning("JWT_LOGIN: buerger_id = %s", buerger_id)

    request.session["user_id"] = buerger_id
    request.session.modified = True
    logger.warning("JWT_LOGIN: Session gesetzt")
    
    beruf = hole_beruf_von_arbeit(str(buerger_id))
    request.session["beruf"] = beruf

    return redirect("profilseite")



#TODO Logout sollte wieder zurück zum Meldewesen führen
def logout(request):
    return redirect('http://[2001:7c0:2320:2:f816:3eff:fef8:f5b9]:8000/einwohnermeldeamt/mainpage')

#A 
def vorstrafen_api(request, buerger_id):
    daten = lade_vorstrafen_daten()

    for akte in daten:
        if str(akte.get("buerger_id")) == str(buerger_id):
            vorstrafen = akte.get("vorstrafen", [])
            return JsonResponse({
                "buerger_id": str(buerger_id),
                "hat_vorstrafen": bool(vorstrafen),
                "vorstrafen": vorstrafen
            }, status=200)

    return JsonResponse({
        "buerger_id": str(buerger_id),
        "hat_vorstrafen": False,
        "vorstrafen": []
    }, status=200)

#A
def gesetz_api(request, gesetz_id):
    gesetze = ladeGesetze()

    for gesetz in gesetze:
        if gesetz["id"] == str(gesetz_id):
            return JsonResponse({
                "id": gesetz["id"],
                "titel": gesetz["titel"],
                "beschreibung": gesetz["beschreibung"],
                "api_relevant": gesetz["api_relevant"],
                "bussgeld": gesetz["bussgeld"],
                "strafe": gesetz["strafe"],
            }, status=200)

    return JsonResponse({
        "fehler": "Gesetz nicht gefunden",
        "gesetz_id": str(gesetz_id),
    }, status=404)

#A
def sende_haftstatus_an_meldewesen(buerger_id: str, haft_status: bool):
    payload = {
        "buerger_id": buerger_id,
        "haft_status": haft_status
    }

    try:
        response = requests.post(HAFTSTATUS_SETZEN_EINWOHNERMELDEAMT, json=payload, timeout=5)
        response.raise_for_status()
        print("MELDEWESEN ok:", response.status_code, response.text)
    except requests.RequestException as e:
        print("Fehler Meldewesen:", repr(e))


#F
BACKUP_ORDNER = {
    "static": (Path(settings.BASE_DIR) / "rechtApp" / "static").resolve(),              # Dateipfad für Backup angeben
}

def erstelle_zip_backup(dateipfad: Path) -> tuple[io.BytesIO, str]:
    if not dateipfad.exists() or not dateipfad.is_dir():                                # Dateipfad Check
        raise FileNotFoundError(f"folgender Ordner existiert nicht: {dateipfad}")

    mem = io.BytesIO()                                                                  # Zip wird in Ram gespeichert/erstellt
    timestamp = datetime.now().strftime("%Y_%m_%d")
    zip_dateiname = f"backup_{dateipfad.name}_{timestamp}.zip"

    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(dateipfad):                                    # Angegebener Dateipfad wird kontrolliert und durchlaufen
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                arcname = file_path.relative_to(dateipfad)
                zf.write(file_path, arcname)

    mem.seek(0)
    return mem, zip_dateiname                                                           # Zip als Antwort der Funktion zurückgegeben

#F
@csrf_exempt                                                                            # okay fürs Testen, später falls möglich Token Auth
def backup(request):
                                                                                        # Pi ruft /backup?backup=static auf Kann lokal getestet werden mit "http://127.0.0.1:8000/backup?backup=static"
    schluessel = request.GET.get("backup")
    if not schluessel:
        return JsonResponse({"status": "error", "message": "Parameter 'backup' fehlt"}, status=400)

    dateipfad = BACKUP_ORDNER.get(schluessel)
    if not dateipfad:
        return JsonResponse({
            "status": "error",
            "message": f"Unbekannter Ordner-Key '{schluessel}'. Erlaubt: {list(BACKUP_ORDNER.keys())}"
        }, status=400)

    try:
        mem, zip_dateiname = erstelle_zip_backup(dateipfad)

        response = HttpResponse(mem.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{zip_dateiname}"'     # Datei wird als Download gesendet/vom "Requester" runtergeladen
        return response

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

#A
def sende_bussgeld_an_bank(buerger_id: str, betrag: int, gesetz_id: int, gesetz_titel: str):
    payload = {
        "buerger_id": buerger_id,
        "betrag": str(int(betrag)),
        "gesetz_id": str(int(gesetz_id)),
        "gesetz_titel": gesetz_titel,
    }
    try:
        response = requests.post(BANK_API_URL, data=payload, timeout=5)
        response.raise_for_status()
        print("BANK ok:", response.status_code, response.text)
    except requests.RequestException as e:
        print("Fehler Bank:", repr(e))


#Test12

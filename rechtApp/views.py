from django.shortcuts import render, redirect
from django.http import HttpResponse
import os
import json
from django.http import JsonResponse
from django.conf import settings
from lxml import etree as ET
 
#Allgemeiner Datenbankpfad
allgemeinerPfad = os.path.join(settings.BASE_DIR, 'rechtApp', 'static', 'datenbank')

# Einzelne JSON-Dateien
gesetzeJsonPfad = os.path.join(allgemeinerPfad, 'gesetze.json')
bussgelderJsonPfad = os.path.join(allgemeinerPfad, 'bussgelder.json')
strafenJsonPfad = os.path.join(allgemeinerPfad, 'strafen.json')
urteileJsonPfad = os.path.join(allgemeinerPfad, 'urteile.json')
benutzerJsonPfad = os.path.join(allgemeinerPfad, 'benutzer.json')

#Einzelne XML-Datei
gesetzeXmlPfad = os.path.join(allgemeinerPfad,'gesetze.xml')

#Hilfsfunktionen
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
def test_views(request):
        return render(request, 'rechtApp/ztest.html')


#Hauptseite-HTML
def hauptseite(request):
    return render(request, 'rechtApp/hauptseite.html')


# Strafen-HTML
def strafen(request):
    data = ladeJson(strafenJsonPfad) #Beschreibung sollte aus GesetzID geholt werden bei der strafen.json
    return render(request, 'rechtApp/strafen.html', {'strafen': data})

# Bußgelder-HTML
# S und A
def bussgelder(request):
    qualifkation = request.session.get('qualifikation') 
    data = ladeJson(bussgelderJsonPfad)
    if not qualifkation == "Polizist":
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
    qualifkation = request.session.get('qualifikation') 
    data = ladeJson(urteileJsonPfad)
    if not qualifkation == "Richter":
        return HttpResponse("""
                        <script>
                            alert("Schleich di, du bist kein Richter!");
                            window.history.back();
                        </script>
                        """)
    return render(request, 'rechtApp/urteile.html', {'urteile': data})

# Gesetze-HTML
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

#S
def gesetzErlassen(request): 
    if request.method == "POST":
        titel = request.POST.get("titel")
        beschreibung = request.POST.get("beschreibung")
        bussgeld = request.POST.get("bussgeld")
        strafe = request.POST.get("strafe")

        tree = xmlStrukturierenGesetze()
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

        tree.write(gesetzeXmlPfad, encoding="utf-8", xml_declaration=True, pretty_print=True)

        return redirect("gesetzErlassen")

    gesetze_liste = ladeGesetze()
    return render(request, "rechtApp/gesetze.html", {"gesetze": gesetze_liste})

#S
def gesetze(request):
    gesetze_liste = ladeGesetze()
    return render(request, "rechtApp/gesetze.html", {"gesetze": gesetze_liste})


#Login-HTML
#S und A
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
                    qualifikation = benutzer["qualifikation"]
                    request.session['qualifikation'] = qualifikation
                    print(request.session.get('qualifikation'))
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



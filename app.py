import streamlit as st
from streamlit_oauth import OAuth2Component
from streamlit_cookies_controller import CookieController
import requests
from fpdf import FPDF
import csv
import io
import os
import re
import time
import json
import hmac
import hashlib
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from html import unescape
import PyPDF2
from PIL import Image, ImageChops
from streamlit_pdf_viewer import pdf_viewer

# ============================================================
# USTAWIENIA
# ============================================================
st.set_page_config(page_title="Generator Raportów", page_icon="📊", layout="wide")

st.markdown("""
<style>
/* Obramowanie dla niewypełnionych pól tekstowych */
div[data-testid="stTextInput"] input:placeholder-shown,
div[data-testid="stTextArea"] textarea:placeholder-shown {
    border: 2px solid #ff4b4b !important;
    border-radius: 6px;
    box-shadow: 0 0 4px rgba(255, 75, 75, 0.4) !important;
}
</style>
""", unsafe_allow_html=True)

font_file = "DejaVuSans.ttf"
font_bold_file = "DejaVuSans-Bold.ttf"

# ------------------------------------------------------------
# OSOBY KONTAKTOWE
# ------------------------------------------------------------
BRAK_OSOBY = "— wybierz osobę —"

OSOBY = {
    "Ewa Zuchora": {
        "email": "ewa.zuchora@budujemydom.pl", "telefon": "668 04 54 77",
        "stanowisko": "Specjalista ds. reklamy",
    },
    "Katarzyna Rosa": {
        "email": "katarzyna.rosa@budujemydom.pl", "telefon": "503 672 266",
        "stanowisko": "Specjalista ds. reklamy",
    },
    "Paulina Muniak": {
        "email": "paulina.muniak@budujemydom.pl", "telefon": "513 637 603",
        "stanowisko": "Specjalista ds. reklamy",
    },
    "Agnieszka Iwacyk": {
        "email": "agnieszka.iwacyk@budujemydom.pl", "telefon": "502 719 299",
        "stanowisko": "Specjalista ds. reklamy",
    },
    "Dorota Chrząszcz": {
        "email": "dorota.chrzaszcz@budujemydom.pl", "telefon": "606 887 927",
        "stanowisko": "Specjalista ds. reklamy",
    },
    "Iwona Fijewska": {
        "email": "iwona.fijewska@budujemydom.pl", "telefon": "605 078 601",
        "stanowisko": "Specjalista ds. reklamy",
    },
    "Izabela Konikowska": {
        "email": "izabela.konikowska@budujemydom.pl", "telefon": "507 970 743",
        "stanowisko": "Specjalista ds. reklamy",
    },
    "Tomasz Celmer": {
        "email": "tomasz.celmer@elektronik.com.pl",
        "stanowisko": "Redaktor",
    },
    "Anna Niedźwiedź": {
        "email": "anna.niedzwiedz@avt.pl",
        "stanowisko": "Redaktor",
    },
}

OSOBY_WG_MOTYWU = {
    "AutomatykaB2B": {
        "Katarzyna Gugała": {
            "email": "k.gugala@automatykaB2B.pl",
            "telefon": "22 257 84 64", "telefon_kom": "+48 601 131 953",
        },
        "Bożena Krzykawska": {
            "email": "b.krzykawska@automatykaB2B.pl",
            "telefon": "22 257 84 42",
        },
        "Grzegorz Krzykawski": {
            "email": "g.krzykawski@automatykaB2B.pl",
            "telefon": "22 257 84 60",
        },
    },
    "ElektronikaB2B": {
        "Bożena Krzykawska": {
            "email": "bozena.krzykawska@elektronik.com.pl",
            "telefon": "22 257 84 42",
        },
        "Katarzyna Gugała": {
            "email": "katarzyna.gugala@elektronik.com.pl",
            "telefon": "22 257 84 64",
        },
        "Grzegorz Krzykawski": {
            "email": "grzegorz.krzykawski@elektronik.com.pl",
            "telefon": "22 257 84 60",
        },
    },
}


def osoby_dla_motywu(nazwa_motywu):
    """Lista osób kontaktowych dla wybranej wersji raportu (własna lub ogólna)."""
    return OSOBY_WG_MOTYWU.get(nazwa_motywu, OSOBY)


# ------------------------------------------------------------
# SŁOWNICZEK POJĘĆ: domyślne teksty (PL i EN); w formularzu można je edytować
# ------------------------------------------------------------
SLOWNICZEK = {
    "discover": (
        "Google Discover",
        "Spersonalizowany strumień treści w aplikacji Google i na stronie głównej Google w telefonie. "
        "Pokazuje użytkownikowi artykuły dopasowane do jego zainteresowań, zanim cokolwiek wpisze w wyszukiwarkę. "
        "Odsłony to liczba wyświetleń materiału w tym strumieniu, a kliknięcia to liczba przejść na stronę z materiałem.",
    ),
    "wyniki": (
        "Wyniki wyszukiwania w wyszukiwarce Google",
        "Organiczne (niereklamowe) wyniki, które Google pokazuje w odpowiedzi na wpisaną frazę. "
        "Odsłony to liczba wyświetlonych linków do materiału w wynikach wyszukiwania, "
        "a kliknięcia to liczba przejść z wyników na stronę z materiałem.",
    ),
    "ai": (
        "Generatywna AI",
        "Odpowiedzi tworzone przez sztuczną inteligencję bezpośrednio w wyszukiwarce Google "
        "(np. podsumowania AI nad wynikami wyszukiwania), w których treść jest wykorzystywana jako źródło "
        "i podlinkowana. Wartość oznacza liczbę wyświetleń materiału w takich odpowiedziach.",
    ),
}

SLOWNICZEK_EN = {
    "discover": (
        "Google Discover",
        "A personalised content stream in the Google app and on the Google home page on mobile. "
        "It shows users articles matched to their interests before they type anything into the search engine. "
        "Impressions are the number of times the material was displayed in this stream, and clicks are the number "
        "of visits to the page with the material.",
    ),
    "wyniki": (
        "Google Search results",
        "Organic (non-advertising) results that Google displays in response to a typed query. "
        "Impressions are the number of times a link to the material was displayed in search results, "
        "and clicks are the number of visits to the page with the material from those results.",
    ),
    "ai": (
        "Generative AI",
        "Answers created by artificial intelligence directly in Google Search "
        "(e.g. AI summaries above search results) in which the content is used as a source "
        "and linked. The value is the number of times the material was displayed in such answers.",
    ),
}

SL_ID = ["discover", "wyniki", "ai"]
SLOWNICZEK_WG_JEZYKA = {"pl": SLOWNICZEK, "en": SLOWNICZEK_EN}


def sl_key(pojecie, lang, czesc):
    """Klucz w session_state: czesc = 't' (tytuł) albo 'd' (definicja)."""
    return f"sl_{pojecie}_{lang}_{czesc}"


def przywroc_slowniczek(lang):
    """Callback przycisku: przywraca domyślne teksty słowniczka dla danego języka."""
    for p in SL_ID:
        tytul, definicja = SLOWNICZEK_WG_JEZYKA[lang][p]
        st.session_state[sl_key(p, lang, "t")] = tytul
        st.session_state[sl_key(p, lang, "d")] = definicja


# ------------------------------------------------------------
# JĘZYK RAPORTU (tylko treści widoczne w PDF; interfejs zostaje po polsku)
# ------------------------------------------------------------
JEZYKI = {"Polski": "pl", "English": "en"}

TXT = {
    "pl": {
        "okres": "Okres", "przygotowal": "Przygotował(a)", "najwazniejsze": "Najważniejsze wyniki",
        "podsumowanie": "PODSUMOWANIE", "kliknij": "Kliknij wybraną pozycję, aby otworzyć materiał.",
        "slowniczek": "Słowniczek pojęć", "pytania": "MASZ PYTANIA? SKONTAKTUJ SIĘ Z MNĄ",
        "email": "E-mail", "tel": "Tel.", "tel_kom": "Tel. kom.",
        "data": "Data wykonania raportu", "strona": "Strona",
        "odslony": "Odsłony", "klikniecia": "Kliknięcia",
        "discover": "Google Discover", "wyniki": "Wyniki wyszukiwania w wyszukiwarce Google",
        "fb": "Facebook", "li": "LinkedIn",
    },
    "en": {
        "okres": "Period", "przygotowal": "Prepared by", "najwazniejsze": "Key results",
        "podsumowanie": "SUMMARY", "kliknij": "Click an item to open the material.",
        "slowniczek": "Glossary", "pytania": "QUESTIONS? CONTACT ME",
        "email": "E-mail", "tel": "Phone", "tel_kom": "Mobile",
        "data": "Report date", "strona": "Page",
        "odslony": "Impressions", "klikniecia": "Clicks",
        "discover": "Google Discover", "wyniki": "Google Search results",
        "fb": "Facebook", "li": "LinkedIn",
    },
}

# Klucze KPI zostają po polsku (używa ich CSV), tłumaczymy tylko etykiety w PDF
KPI_EN = {
    "Odsłony portalu": "Portal impressions",
    "Zdarzenia na portalu": "Portal events",
    "Zaangażowanie": "Engagement",
    "Widoczność artykułu w serwisie": "Article visibility on the website",
    "Odsłony w Google Discover": "Google Discover impressions",
    "Kliknięcia z Google Discover": "Google Discover clicks",
    "Odsłony w wyszukiwarce Google": "Google Search impressions",
    "Kliknięcia z wyszukiwarki Google": "Google Search clicks",
    "Generatywna AI": "Generative AI",
    "Zasięg na Facebooku": "Facebook reach",
    "Wyświetlenia na LinkedIn": "LinkedIn views",
}
STANOWISKA_EN = {"Specjalista ds. reklamy": "Advertising Specialist", "Redaktor": "Editor"}

DOMYSLNE_OPISY_EN = {
    "desc_portal": "The statistics reflect direct activity and the level of user engagement with the materials published on the portal.",
    "desc_disc": "The data show the visibility of the article and how well the content matches readers' interests in Google Discover.",
    "desc_wyniki": "The results show organic reach in traditional Google Search and in Generative AI modules.",
    "desc_fb": "The summary covers the reach generated on Facebook, supporting the main communication.",
    "desc_li": "The summary covers the reach of publications on LinkedIn, supporting the main communication.",
}

# ------------------------------------------------------------
# MOTYWY
# ------------------------------------------------------------
MOTYWY = {
    "Produkty i Firmy": {
        "portal": "Portal Produkty i Firmy",
        "main": (94, 66, 88), "accent": (255, 160, 0), "light": (247, 244, 248),
        "bar": (255, 160, 0), "line": (255, 160, 0), "label": (255, 160, 0),
        "loga": {
            "Produkty i Firmy": ("logo", 52, 34),
        },
    },
    "budujemydom.pl": {
        "portal": "Portal budujemydom.pl",
        "main": (100, 110, 117), "accent": (229, 38, 33), "light": (244, 245, 246),
        "bar": (100, 110, 117), "line": (229, 38, 33), "label": (229, 38, 33),
        "loga": {
            "Czerwone": ("logo-budujemydom-czerwone", 46, 30),
            "Szare": ("logo-budujemydom-szare", 46, 30),
        },
    },
    "Elportal": {
        "portal": "Elportal",
        "main": (100, 110, 117), "accent": (205, 23, 25), "light": (244, 245, 246),
        "bar": (100, 110, 117), "line": (205, 23, 25), "label": (205, 23, 25),
        "loga": {
            "Elportal": ("logo-elportal", 60, 40),
        },
    },
    "AutomatykaB2B": {
        "portal": "Portal AutomatykaB2B",
        "main": (104, 114, 128), "accent": (10, 105, 175), "light": (243, 246, 250),
        "bar": (104, 114, 128), "line": (10, 105, 175), "label": (10, 105, 175),
        "loga": {
            "AutomatykaB2B": ("logo-automatykab2b", 54, 36),
        },
    },
    "ElektronikaB2B": {
        "portal": "Portal ElektronikaB2B",
        "main": (104, 114, 128), "accent": (217, 80, 65), "light": (247, 245, 245),
        "bar": (104, 114, 128), "line": (217, 80, 65), "label": (217, 80, 65),
        "loga": {
            "ElektronikaB2B": ("logo-elektronikab2b", 54, 36),
        },
    },
}

UKLAD = ["1 w rzędzie", "2 kolumny"]
KPI_OPTIONS = [
    "Odsłony portalu", "Zdarzenia na portalu", "Zaangażowanie", "Widoczność artykułu w serwisie",
    "Odsłony w Google Discover", "Kliknięcia z Google Discover",
    "Odsłony w wyszukiwarce Google", "Kliknięcia z wyszukiwarki Google",
    "Generatywna AI", "Zasięg na Facebooku", "Wyświetlenia na LinkedIn",
]
DOMYSLNE_KPI = ["Odsłony portalu", "Odsłony w wyszukiwarce Google", "Odsłony w Google Discover", "Zaangażowanie"]
DOMYSLNY_UKLAD = {"u1": UKLAD[0], "u2": UKLAD[0], "u3": UKLAD[0], "u4": UKLAD[1], "u5": UKLAD[0]}
DOMYSLNE_OPISY = {
    "desc_portal": "Statystyki odzwierciedlają bezpośrednią aktywność oraz poziom zaangażowania użytkowników w materiały opublikowane na portalu.",
    "desc_disc": "Dane obrazują widoczność artykułu i trafność dopasowania treści do czytelników w kanale Google Discover.",
    "desc_wyniki": "Wyniki przedstawiają zasięg organiczny w tradycyjnej wyszukiwarce Google oraz w modułach Generatywnej AI.",
    "desc_fb": "Zestawienie obejmuje zasięg wygenerowany w serwisie Facebook, wspierający główną komunikację.",
    "desc_li": "Zestawienie obejmuje zasięg publikacji w serwisie LinkedIn, wspierający główną komunikację.",
}

POLA_CSV = [
    ("firma", "Raport dla firmy"),
    ("okres", "Okres kampanii"),
    ("zdarzenia", "Portal: liczba zdarzeń"),
    ("odslony", "Portal: odsłony"),
    ("zaangazowanie", "Portal: zaangażowanie"),
    ("zajawka", "Portal: widoczność artykułu w serwisie"),
    ("g_disc_odslony", "Google Discover: odsłony"),
    ("g_disc_klik", "Google Discover: kliknięcia"),
    ("g_wyniki_odslony", "Wyszukiwarka Google: odsłony"),
    ("g_wyniki_klik", "Wyszukiwarka Google: kliknięcia"),
    ("g_ai", "Wyszukiwarka Google: generatywna AI"),
    ("fb_zasieg", "Facebook: zasięg"),
    ("li_zasieg", "LinkedIn: wyświetlenia"),
    ("podsumowanie", "Podsumowanie / komentarz na okładce"),
    ("desc_portal", "Opis sekcji: Portal"),
    ("desc_disc", "Opis sekcji: Google Discover"),
    ("desc_wyniki", "Opis sekcji: wyszukiwarka Google"),
    ("desc_fb", "Opis sekcji: Facebook"),
    ("desc_li", "Opis sekcji: LinkedIn"),
    ("links_portal", "Linki: Portal"),
    ("links_disc", "Linki: Google Discover"),
    ("links_wyniki", "Linki: wyszukiwarka Google"),
    ("links_fb", "Linki: Facebook"),
    ("links_li", "Linki: LinkedIn"),
]
POLA_LICZBOWE = {"zdarzenia", "odslony", "g_disc_odslony", "g_disc_klik", "g_wyniki_odslony",
                 "g_wyniki_klik", "g_ai", "fb_zasieg", "li_zasieg"}
KLUCZE_TEKSTOWE = {k for k, _ in POLA_CSV}
USTAWIENIA_CSV = [
    ("bez_osoby", "Bez osoby kontaktowej w raporcie (TAK / NIE)"),
    ("osoba", "Osoba kontaktowa (imię i nazwisko z listy dla wybranej wersji raportu)"),
    ("kpi_wybrane", "Kafelki na okładce (rozdziel znakiem |)"),
    ("motyw", "Wersja raportu: " + " / ".join(MOTYWY.keys())),
    ("logo_wariant", "Logo (tylko budujemydom.pl): Czerwone / Szare"),
    ("jezyk", "Język raportu: " + " / ".join(JEZYKI.keys())),
    ("u1", "Układ grafik: Portal (" + " / ".join(UKLAD) + ")"),
    ("u2", "Układ grafik: Google Discover"),
    ("u3", "Układ grafik: wyszukiwarka Google"),
    ("u4", "Układ grafik: Facebook"),
    ("u5", "Układ grafik: LinkedIn"),
]


def znajdz_plik(baza):
    """Zwraca nazwę istniejącego pliku baza.png/.jpg/.jpeg albo None."""
    for ext in (".png", ".jpg", ".jpeg"):
        if os.path.exists(baza + ext):
            return baza + ext
    return None


def przygotuj_logo(sciezka):
    """Wczytuje logo i przycina puste (białe lub przezroczyste) marginesy."""
    try:
        im = Image.open(sciezka).convert("RGBA")
        na_bialym = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im).convert("RGB")
        roznica = ImageChops.difference(na_bialym, Image.new("RGB", na_bialym.size, (255, 255, 255)))
        maska = roznica.convert("L").point(lambda p: 255 if p > 12 else 0)
        ramka = maska.getbbox()
        if ramka:
            im = im.crop(ramka)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        buf.seek(0)
        return buf, im.height / im.width
    except Exception:
        return None, None


# ------------------------------------------------------------
# LINKI: parser wklejonej listy
# ------------------------------------------------------------
URL_RE = re.compile(r"https?://[^\s<>\"]+")
LINK_TEKST_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"]+", re.IGNORECASE)
SPOLECZNOSC = {"facebook.com": "fb", "fb.com": "fb", "linkedin.com": "li"}
DOZWOLONE_HOSTY_TYTULY = ("budujemydom.pl", "budownictwob2b.pl", "instalacjeb2b.pl")


def host_z_url(url):
    return re.sub(r"^https?://(www\.)?", "", url, flags=re.IGNORECASE).split("/")[0].split(":")[0].lower()


def host_dozwolony(url):
    host = host_z_url(url)
    return any(host == d or host.endswith("." + d) for d in DOZWOLONE_HOSTY_TYTULY)


def nazwa_z_url(url):
    path = re.sub(r"^https?://[^/]+", "", url).split("?")[0].split("#")[0]
    segs = [s for s in path.split("/") if s]
    if not segs:
        return host_z_url(url)
    slug = re.sub(r"^\d+-", "", segs[-1])
    nazwa = re.sub(r"[-_]+", " ", slug).strip()
    if not nazwa:
        return host_z_url(url)
    return nazwa[0].upper() + nazwa[1:]


def przygotuj_linki(raw):
    """Zwraca (lista krotek (typ, etykieta, url, rodzaj), liczba pominiętych duplikatów)."""
    wynik, widziane, duplikaty = [], set(), 0
    liczniki = {"fb": 0, "li": 0}
    for linia in str(raw or "").splitlines():
        s = linia.strip()
        if not s:
            continue
        m = URL_RE.search(s)
        if not m:
            wynik.append(("head", s.strip(" :,;"), "", ""))
            continue
        url = m.group(0).rstrip(",.;)")
        if url in widziane:
            duplikaty += 1
            continue
        widziane.add(url)
        etykieta = s[:m.start()].strip(" |-–:,;")
        if etykieta:
            rodzaj = "wlasna"
        else:
            host = host_z_url(url)
            typ = next((v for k, v in SPOLECZNOSC.items() if host.endswith(k)), None)
            if typ:
                liczniki[typ] += 1
                etykieta = f"Post {liczniki[typ]}"
                rodzaj = "post"
            else:
                etykieta = nazwa_z_url(url)
                rodzaj = "auto"
        wynik.append(("link", etykieta, url, rodzaj))
    return wynik, duplikaty


def info_o_linkach(raw):
    elementy, dup = przygotuj_linki(raw)
    n = sum(1 for e in elementy if e[0] == "link")
    if n:
        st.caption(f"Rozpoznano linków: {n}" + (f" (pominięto duplikaty: {dup})" if dup else ""))


def _pobierz_tytul(url):
    """Pobiera tytuł strony (og:title lub <title>). Tylko dozwolone domeny; przy błędzie zwraca ''."""
    try:
        if not host_dozwolony(url):
            return ""
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0 (GeneratorRaportow)"})
        if r.status_code != 200 or not host_dozwolony(r.url):
            return ""
        html = r.text[:250000]
        m = (re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html, re.I)
             or re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S))
        if not m:
            return ""
        t = unescape(re.sub(r"\s+", " ", m.group(1))).strip()
        t = re.split(r"\s+[\|–—]\s+", t)[0]
        t = re.sub(r"\s+-\s+(budujemydom\.pl|Budujemy Dom|budownictwob2b\.pl|Budownictwo B2B).*$", "", t, flags=re.I)
        return t.strip()
    except Exception:
        return ""


def pobierz_tytuly(urls):
    cache = st.session_state.setdefault("_tytuly", {})
    do_pobrania = [u for u in urls if u not in cache]
    if do_pobrania:
        with ThreadPoolExecutor(max_workers=8) as ex:
            wyniki = list(ex.map(_pobierz_tytul, do_pobrania))
        for u, t in zip(do_pobrania, wyniki):
            cache[u] = t
    return {u: cache.get(u, "") for u in urls}


def uzupelnij_tytuly(elementy):
    do_pobrania = [url for (typ, _l, url, rodzaj) in elementy
                   if typ == "link" and rodzaj == "auto" and host_dozwolony(url)]
    tytuly = pobierz_tytuly(do_pobrania) if do_pobrania else {}
    wynik = []
    for typ, lab, url, rodzaj in elementy:
        if typ == "link" and rodzaj == "auto" and tytuly.get(url):
            lab = tytuly[url]
        wynik.append((typ, lab, url, rodzaj))
    return wynik


# ------------------------------------------------------------
# CSV: eksport i import
# ------------------------------------------------------------
def formatuj_liczbe(v):
    v = v.strip()
    if re.fullmatch(r"\d{4,}", v):
        return f"{int(v):,}".replace(",", " ")
    return v


def csv_eksport():
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    w.writerow(["klucz", "opis", "wartosc"])
    for klucz, opis in POLA_CSV:
        w.writerow([klucz, opis, str(st.session_state.get(klucz, "") or "")])
    for klucz, opis in USTAWIENIA_CSV:
        if klucz == "kpi_wybrane":
            wartosc = " | ".join(st.session_state.get("kpi_wybrane", []) or [])
        elif klucz == "bez_osoby":
            wartosc = "TAK" if st.session_state.get("bez_osoby") else "NIE"
        elif klucz == "osoba":
            wartosc = st.session_state.get("osoba", "")
            wartosc = "" if wartosc == BRAK_OSOBY else wartosc
        else:
            wartosc = str(st.session_state.get(klucz, "") or "")
        w.writerow([klucz, opis, wartosc])
    return buf.getvalue().encode("utf-8-sig")


def csv_import(plik):
    """Wpisuje dane z CSV do session_state. Zwraca (liczba zastosowanych pól, lista pominiętych)."""
    tekst = plik.getvalue().decode("utf-8-sig", errors="replace")
    pierwsza = tekst.splitlines()[0] if tekst.strip() else ""
    sep = ";" if pierwsza.count(";") >= pierwsza.count(",") else ","
    reader = csv.DictReader(io.StringIO(tekst, newline=""), delimiter=sep)
    if reader.fieldnames:
        reader.fieldnames = [(f or "").strip().lower() for f in reader.fieldnames]

    wartosci = {}
    for row in reader:
        klucz = (row.get("klucz") or "").strip()
        if klucz:
            wartosci[klucz] = (row.get("wartosc") or "").replace("\r\n", "\n").replace("\r", "\n")

    zastosowano, pominiete = 0, []
    for klucz, val in wartosci.items():
        if klucz in KLUCZE_TEKSTOWE:
            st.session_state[klucz] = formatuj_liczbe(val) if klucz in POLA_LICZBOWE else val.strip()
            zastosowano += 1
        elif klucz == "kpi_wybrane":
            lista = [x.strip() for x in val.split("|") if x.strip()]
            poprawne = [x for x in lista if x in KPI_OPTIONS]
            for x in lista:
                if x not in KPI_OPTIONS:
                    pominiete.append(f"kafelek „{x}”")
            st.session_state["kpi_wybrane"] = poprawne
            zastosowano += 1
        elif klucz == "bez_osoby":
            st.session_state["bez_osoby"] = val.strip().lower() in ("tak", "true", "1", "yes")
            zastosowano += 1
        elif klucz == "motyw":
            if val.strip() in MOTYWY:
                st.session_state["motyw"] = val.strip()
                zastosowano += 1
            elif val.strip():
                pominiete.append(f"wersja raportu „{val.strip()}”")
        elif klucz == "jezyk":
            if val.strip() in JEZYKI:
                st.session_state["jezyk"] = val.strip()
                zastosowano += 1
            elif val.strip():
                pominiete.append(f"język „{val.strip()}”")
        elif klucz in ("logo_wariant", "osoba"):
            pass   # obsługiwane niżej, po ustaleniu motywu
        elif klucz in DOMYSLNY_UKLAD:
            if val.strip() in UKLAD:
                st.session_state[klucz] = val.strip()
                zastosowano += 1
            elif val.strip():
                pominiete.append(f"układ „{val.strip()}” ({klucz})")
        else:
            pominiete.append(f"nieznany klucz „{klucz}”")

    motyw_koncowy = st.session_state.get("motyw", list(MOTYWY.keys())[0])

    if "logo_wariant" in wartosci and wartosci["logo_wariant"].strip():
        dostepne = MOTYWY[motyw_koncowy]["loga"]
        if len(dostepne) > 1:
            if wartosci["logo_wariant"].strip() in dostepne:
                st.session_state["logo_wariant"] = wartosci["logo_wariant"].strip()
                zastosowano += 1
            else:
                pominiete.append(f"logo „{wartosci['logo_wariant'].strip()}”")

    if "osoba" in wartosci and wartosci["osoba"].strip():
        if wartosci["osoba"].strip() in osoby_dla_motywu(motyw_koncowy):
            st.session_state["osoba"] = wartosci["osoba"].strip()
            zastosowano += 1
        else:
            pominiete.append(f"osoba „{wartosci['osoba'].strip()}” (brak na liście dla wersji „{motyw_koncowy}”)")
    return zastosowano, pominiete


# Stałe niezależne od motywu
GREY = (100, 100, 100)
ML = 18
W = 174
LIMIT = 265
TOP2 = 32

# ============================================================
# LOGOWANIE OAUTH (Google Workspace) + ciasteczko na 30 dni
# ============================================================
DOZWOLONE_DOMENY = ("budujemydom.pl", "zielonyogrodek.pl", "ep.pl", "avt.pl", "elektronik.com.pl")

COOKIE_NAME = "gen_raportow_auth"
COOKIE_DNI = 30
COOKIE_SEKUNDY = COOKIE_DNI * 24 * 3600

try:
    _COOKIE_SECRET = st.secrets["google_oauth"]["cookie_secret"]
except Exception:
    _COOKIE_SECRET = st.secrets["google_oauth"]["client_secret"]   # zapasowo


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _podpis(payload):
    return hmac.new(_COOKIE_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def utworz_token(email, name):
    dane = {"e": email, "n": name, "x": int(time.time()) + COOKIE_SEKUNDY}
    payload = _b64(json.dumps(dane, ensure_ascii=False).encode("utf-8"))
    return f"{payload}.{_podpis(payload)}"


def sprawdz_token(token):
    """Zwraca (email, name) przy poprawnym, nieprzeterminowanym tokenie z dozwolonej domeny; inaczej None."""
    try:
        payload, sig = str(token).split(".", 1)
        if not hmac.compare_digest(sig, _podpis(payload)):
            return None
        dane = json.loads(_unb64(payload).decode("utf-8"))
        if int(dane.get("x", 0)) < time.time():
            return None
        email = str(dane.get("e", "")).strip().lower()
        domena = email.rsplit("@", 1)[-1] if "@" in email else ""
        if domena not in DOZWOLONE_DOMENY:
            return None
        return email, str(dane.get("n", ""))
    except Exception:
        return None


cookies = CookieController()


def cookie_get(nazwa):
    """Bezpieczny odczyt: None, gdy komponent ciasteczek jeszcze się nie załadował."""
    try:
        return cookies.get(nazwa)
    except Exception:
        return None


def cookie_set(nazwa, wartosc, max_age):
    try:
        cookies.set(nazwa, wartosc, max_age=max_age, same_site="lax")
        return True
    except Exception:
        return False


def cookie_remove(nazwa):
    try:
        cookies.remove(nazwa)
    except Exception:
        pass


oauth2 = OAuth2Component(
    client_id=st.secrets["google_oauth"]["client_id"],
    client_secret=st.secrets["google_oauth"]["client_secret"],
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke"
)

if "user_email" not in st.session_state:
    # 1) automatyczne logowanie z ciasteczka (chyba że użytkownik właśnie się wylogował)
    if not st.session_state.get("_wylogowany"):
        token_cookie = cookie_get(COOKIE_NAME)
        if token_cookie:
            ok = sprawdz_token(token_cookie)
            if ok:
                st.session_state.user_email, st.session_state.user_name = ok
                st.rerun()
        elif st.session_state.get("_cookie_proby", 0) < 2:
            # komponent ciasteczek potrzebuje chwili przy pierwszym uruchomieniu
            st.session_state["_cookie_proby"] = st.session_state.get("_cookie_proby", 0) + 1
            time.sleep(0.7)
            st.rerun()

    # 2) zwykłe logowanie Google
    st.title("Generator Raportów")
    st.subheader("Wymagane logowanie")
    st.write("Aby korzystać z aplikacji, zaloguj się firmowym kontem Google. "
             f"Logowanie zostanie zapamiętane w tej przeglądarce na {COOKIE_DNI} dni.")

    result = oauth2.authorize_button(
        name="🔐 Zaloguj przez Google",
        redirect_uri=st.secrets["google_oauth"]["redirect_uri"],
        scope="openid email profile"
    )

    if result and "token" in result:
        token = result["token"]["access_token"]
        user_info = requests.get("https://www.googleapis.com/oauth2/v3/userinfo",
                                 headers={"Authorization": f"Bearer {token}"}).json()

        login_email = user_info.get("email", "").strip().lower()
        domena = login_email.rsplit("@", 1)[-1] if "@" in login_email else ""
        if domena in DOZWOLONE_DOMENY and user_info.get("email_verified"):
            nazwa_usera = user_info.get("name", "")
            cookie_set(COOKIE_NAME, utworz_token(login_email, nazwa_usera), COOKIE_SEKUNDY)
            st.session_state.user_email = login_email
            st.session_state.user_name = nazwa_usera
            st.session_state.pop("_wylogowany", None)
            time.sleep(1)   # czas na zapisanie ciasteczka w przeglądarce przed przeładowaniem
            st.rerun()
        else:
            st.error("Dostęp tylko dla zweryfikowanych kont firmowych z domen: "
                     + ", ".join("@" + d for d in DOZWOLONE_DOMENY)
                     + f". Próba logowania z adresu: {login_email}")
    st.stop()

email_user = st.session_state.user_email

with st.sidebar:
    st.caption("Zalogowano jako")
    st.write(f"**{st.session_state.get('user_name', email_user)}**")
    st.caption(email_user)
    if st.button("Wyloguj"):
        cookie_remove(COOKIE_NAME)
        st.session_state.pop("user_email", None)
        st.session_state.pop("user_name", None)
        st.session_state["_wylogowany"] = True
        time.sleep(0.7)
        st.rerun()

st.markdown("### Generator Raportów Zasięgowych")

keys_to_init = [
    'firma', 'okres', 'zdarzenia', 'odslony', 'zaangazowanie',
    'zajawka', 'g_disc_odslony', 'g_disc_klik',
    'g_wyniki_odslony', 'g_wyniki_klik', 'g_ai', 'fb_zasieg', 'li_zasieg', 'podsumowanie',
    'links_portal', 'links_disc', 'links_wyniki', 'links_fb', 'links_li'
]
for k in keys_to_init:
    if k not in st.session_state:
        st.session_state[k] = ""

for k, v in DOMYSLNE_OPISY.items():
    if k not in st.session_state:
        st.session_state[k] = v
for k, v in DOMYSLNY_UKLAD.items():
    if k not in st.session_state:
        st.session_state[k] = v
if "kpi_wybrane" not in st.session_state:
    st.session_state["kpi_wybrane"] = list(DOMYSLNE_KPI)
if "motyw" not in st.session_state:
    st.session_state["motyw"] = list(MOTYWY.keys())[0]
if "jezyk" not in st.session_state:
    st.session_state["jezyk"] = "Polski"
if "osoba" not in st.session_state:
    st.session_state["osoba"] = BRAK_OSOBY
if "bez_osoby" not in st.session_state:
    st.session_state["bez_osoby"] = False

# Domyślne (edytowalne) teksty słowniczka
for _lang, _slownik in SLOWNICZEK_WG_JEZYKA.items():
    for _p in SL_ID:
        if sl_key(_p, _lang, "t") not in st.session_state:
            st.session_state[sl_key(_p, _lang, "t")] = _slownik[_p][0]
        if sl_key(_p, _lang, "d") not in st.session_state:
            st.session_state[sl_key(_p, _lang, "d")] = _slownik[_p][1]

# ============================================================
# PARSOWANIE PDF Z GOOGLE ANALYTICS
# ============================================================
NUM_CORE = r"(?:\d{1,3}(?:[ \u00a0]\d{3})+(?:,\d+)?%?|\d+(?:,\d+)?%?)"
NUM = r"(" + NUM_CORE + r")(?!\.)"

MONTH = r"[^\W\d_](?:\s*[^\W\d_]){2,8}"
DATE = (r"\d{1,2}\s+" + MONTH + r"\s+\d{4}\s*[-–—]\s*"
        r"\d{1,2}\s+" + MONTH + r"\s+\d{4}")


def label_re(label):
    return r"\s*".join(re.escape(c) for c in label if not c.isspace())


def get_value(text, label):
    m = re.search(label_re(label) + r"\s*" + NUM, text, re.IGNORECASE)
    return m.group(1).replace("\u00a0", " ").strip() if m else ""


def get_period(text):
    m = re.search(label_re("Odsłony z GA4") + r"\s*" + NUM_CORE + r"(?P<d>" + DATE + r")",
                  text, re.IGNORECASE)
    if not m:
        m = re.search(r"(?<!\d)(?P<d>" + DATE + r")", text, re.IGNORECASE)
    if not m:
        return ""
    d = m.group("d")
    d = re.sub(r"(?<=[^\W\d_])\s+(?=[^\W\d_])", "", d)
    d = re.sub(r"\s*[-–—]\s*", " - ", d)
    return re.sub(r"\s+", " ", d).strip()


# Miesiące PL -> EN: tłumaczenie pola „Okres kampanii” w wersji angielskiej
MIESIACE_EN = {
    "stycznia": "January", "styczeń": "January", "lutego": "February", "luty": "February",
    "marca": "March", "marzec": "March", "kwietnia": "April", "kwiecień": "April",
    "maja": "May", "maj": "May", "czerwca": "June", "czerwiec": "June",
    "lipca": "July", "lipiec": "July", "sierpnia": "August", "sierpień": "August",
    "września": "September", "wrzesień": "September", "października": "October", "październik": "October",
    "listopada": "November", "listopad": "November", "grudnia": "December", "grudzień": "December",
}


def okres_en(txt):
    def zamien(m):
        return MIESIACE_EN.get(m.group(0).lower(), m.group(0))
    return re.sub(r"[^\W\d_]+", zamien, txt)


st.info("💡 Możesz zautomatyzować wpisywanie danych, wgrywając poniżej surowy raport PDF z Google Analytics. System sam wyciągnie z niego liczby i daty.")
uploaded_ga_pdf = st.file_uploader("Wgraj raport PDF z Google Analytics (Opcjonalnie)", type=["pdf"])
debug_pdf = st.checkbox("Pokaż surowy tekst wyciągnięty z PDF (diagnostyka)")

if uploaded_ga_pdf is not None:
    try:
        reader = PyPDF2.PdfReader(uploaded_ga_pdf)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

        if debug_pdf:
            st.text_area("Surowy tekst z PDF", text, height=300)

        if not st.session_state.get(f'processed_{uploaded_ga_pdf.name}', False):
            firma_match = re.search(r'Produkty\s*i\s*Firmy\s*-\s*([^\n]+)', text, re.IGNORECASE)
            if firma_match:
                st.session_state.firma = firma_match.group(1).strip()

            okres_val = get_period(text)
            if okres_val:
                st.session_state.okres = okres_val

            mapa = {
                "zdarzenia":        "Zdarzenia",
                "odslony":          "Odsłony z GA4",
                "zaangazowanie":    "Zaangażowanie",
                "g_disc_klik":      "Kliknięcia z Discover",
                "g_disc_odslony":   "Odsłony z Discover",
                "g_wyniki_klik":    "Kliknięcia z Google",
                "g_wyniki_odslony": "Odsłony z Google",
            }
            brak = []
            for key, label in mapa.items():
                val = get_value(text, label)
                if val:
                    st.session_state[key] = val
                else:
                    brak.append(label)

            st.session_state[f'processed_{uploaded_ga_pdf.name}'] = True
            if brak:
                st.session_state["_brak_pdf"] = brak
            else:
                st.session_state.pop("_brak_pdf", None)
            st.rerun()
    except Exception as e:
        st.error(f"Wystąpił problem podczas odczytywania pliku: {e}")

if st.session_state.get("_brak_pdf"):
    st.warning("Nie udało się odczytać: " + ", ".join(st.session_state["_brak_pdf"]) +
               ". Zaznacz „Pokaż surowy tekst” i sprawdź, jak PDF zwraca te pola, albo wpisz je ręcznie.")

# ============================================================
# EKSPORT / IMPORT DANYCH RAPORTU (CSV)
# ============================================================
with st.expander("📄 Eksport i import danych raportu (CSV)"):
    st.caption("Pobierz dane raportu do pliku CSV, popraw je w Excelu lub Arkuszach Google (zmieniaj tylko kolumnę "
               "„wartosc”), a potem wczytaj z powrotem. CSV nie zawiera grafik, logo klienta ani edytowanego słowniczka.")
    nazwa_csv = re.sub(r"[^\w\-]+", "_", str(st.session_state.get("firma", "")).strip()) or "raport"
    st.download_button(
        "⬇️ Pobierz dane raportu (CSV)",
        data=csv_eksport(),
        file_name=f"dane_raportu_{nazwa_csv}.csv",
        mime="text/csv",
    )
    plik_csv = st.file_uploader("Wczytaj poprawiony plik CSV", type=["csv"], key="csv_import")
    if plik_csv is not None:
        if st.button("Zastosuj dane z pliku CSV"):
            zastosowano, pominiete = csv_import(plik_csv)
            st.success(f"Wczytano pól: {zastosowano}. Formularz poniżej został zaktualizowany.")
            if pominiete:
                st.warning("Pominięto: " + "; ".join(pominiete))

st.markdown("---")

# ============================================================
# WYGLĄD RAPORTU (kolorystyka + logo + język)
# ============================================================
st.markdown("#### Wygląd raportu")
wybor_motywu = st.radio("Wersja raportu (kolorystyka):", list(MOTYWY.keys()), horizontal=True, key="motyw")
motyw = MOTYWY[wybor_motywu]
loga = motyw["loga"]

if len(loga) > 1:
    wybor_logo = st.radio("Logo:", list(loga.keys()), horizontal=True, key="logo_wariant")
else:
    wybor_logo = list(loga.keys())[0]
logo_baza, w_cover, w_small = loga[wybor_logo]

wybor_jezyka = st.radio(
    "Język raportu (PDF):", list(JEZYKI.keys()), horizontal=True, key="jezyk",
    help="Zmienia stałe teksty raportu (nagłówki, etykiety, słowniczek, stopka, domyślne opisy sekcji). "
         "Teksty wpisane ręcznie (komentarz, własne opisy, nazwy linków, nazwa firmy) wpisz od razu w wybranym języku.",
)
LANG = JEZYKI[wybor_jezyka]
T = TXT[LANG]

logo_raport = znajdz_plik(logo_baza)
if logo_raport is None:
    st.warning(f"Nie znaleziono pliku logo „{logo_baza}” (.png/.jpg). "
               f"Dodaj go do repozytorium obok app.py. Na razie użyję logo Produkty i Firmy.")
    logo_raport = znajdz_plik("logo")
    w_cover, w_small = 52, 34
if logo_raport:
    st.image(logo_raport, width=170)

logo_buf, logo_ratio = przygotuj_logo(logo_raport) if logo_raport else (None, None)

MAIN = motyw["main"]
NAZWA_PORTALU = motyw["portal"]
ACCENT = motyw["accent"]
LIGHT = motyw["light"]
BAR = motyw["bar"]
LINE = motyw["line"]
LABEL = motyw["label"]

st.markdown("---")

# ============================================================
# FORMULARZ
# ============================================================
col_firma1, col_firma2, col_firma3 = st.columns([2, 2, 1.5])
with col_firma1:
    firma = st.text_input("Raport dla firmy:", key="firma", placeholder=" ")
with col_firma2:
    okres = st.text_input("Okres kampanii:", key="okres", placeholder=" ")
with col_firma3:
    logo_klienta = st.file_uploader("Wgraj logo klienta (opcjonalnie)", type=["png", "jpg", "jpeg"])

st.markdown("#### Osoba kontaktowa w raporcie")
dostepne_osoby = osoby_dla_motywu(wybor_motywu)
if st.session_state.get("osoba") not in ([BRAK_OSOBY] + list(dostepne_osoby.keys())):
    st.session_state["osoba"] = BRAK_OSOBY

bez_osoby = st.checkbox(
    "Nie pokazuj osoby kontaktowej w raporcie (bez karty „Masz pytania?” i bez linii „Przygotował(a)” na okładce)",
    key="bez_osoby",
)

co1, co2 = st.columns([3, 1.5])
wybrana_osoba = co1.selectbox(
    "Dla kogo przygotowujesz raport (jej dane trafią na okładkę i do stopki „Masz pytania?”; "
    "lista zależy od wybranej wersji raportu):",
    [BRAK_OSOBY] + list(dostepne_osoby.keys()),
    key="osoba",
    disabled=bez_osoby,
)
data_raportu = co2.date_input("Data wykonania raportu:", value=date.today())

if bez_osoby:
    autor = stanowisko = email = telefon = telefon_kom = ""
    co1.caption("Raport zostanie wygenerowany bez osoby kontaktowej.")
elif wybrana_osoba in dostepne_osoby:
    _dane_osoby = dostepne_osoby[wybrana_osoba]
    autor = wybrana_osoba
    stanowisko = _dane_osoby.get("stanowisko", "")
    email = _dane_osoby.get("email", "")
    telefon = _dane_osoby.get("telefon", "")
    telefon_kom = _dane_osoby.get("telefon_kom", "")
    co1.caption(" · ".join(x for x in [stanowisko, email, telefon, telefon_kom] if x))
else:
    autor = stanowisko = email = telefon = telefon_kom = ""

st.markdown("---")
st.subheader("Strona tytułowa: podsumowanie")
kpi_wybrane = st.multiselect(
    "Kafelki z najważniejszymi wynikami na pierwszej stronie (zalecane 3–4; puste wartości są pomijane):",
    KPI_OPTIONS,
    key="kpi_wybrane",
)
POMOC_TEKST = ("Adresy zaczynające się od https://, http:// lub www. są klikalne i zostają w takiej postaci, "
               "w jakiej je wpiszesz.")
podsumowanie = st.text_area("Komentarz / podsumowanie do raportu (opcjonalnie):", key="podsumowanie", height=90, help=POMOC_TEKST)

st.markdown("---")
st.subheader("Dane, opisy, linki i grafiki dla poszczególnych sekcji")
st.caption("Sekcje bez danych, linków i grafik nie pojawią się w raporcie. Adresy URL wpisane w opisach są klikalne.")
POMOC_LINKI = ("Jeden wiersz = jeden element. Adresy z Facebooka i LinkedIna dostają kafelki „Post 1”, „Post 2”… "
               "Pozostałe adresy trafiają na listę: dla budujemydom.pl, budownictwob2b.pl i instalacjeb2b.pl tytuły "
               "artykułów są pobierane automatycznie przy generowaniu raportu. Własną nazwę nadasz formatem "
               "„Nazwa | https://adres”. Wiersz bez adresu staje się podtytułem. Duplikaty są pomijane.")

# --- SEKCJA 1 ---
st.markdown(f"#### 1. {NAZWA_PORTALU}")
desc_portal = st.text_area("Opis sekcji (Portal):", key="desc_portal", height=70, placeholder=" ", help=POMOC_TEKST)
col1a, col1b = st.columns(2)
zdarzenia = col1a.text_input("Liczba zdarzeń na portalu:", key="zdarzenia", placeholder=" ")
odslony = col1b.text_input("Odsłony (Portal):", key="odslony", placeholder=" ")
col1c, col1d = st.columns(2)
zaangazowanie = col1c.text_input("Zaangażowanie:", key="zaangazowanie", placeholder=" ")
zajawka = col1d.text_input("Widoczność artykułu w serwisie:", key="zajawka", placeholder=" ")
links_portal = st.text_area("Linki do materiałów (opcjonalnie):", key="links_portal", height=100, help=POMOC_LINKI)
info_o_linkach(links_portal)
img_portal = st.file_uploader(f"Dodaj grafiki ({NAZWA_PORTALU})", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p1")
uklad_portal = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u1")
st.markdown("---")

# --- SEKCJA 2 ---
st.markdown("#### 2. Google Discover")
desc_disc = st.text_area("Opis sekcji (Discover):", key="desc_disc", height=70, placeholder=" ", help=POMOC_TEKST)
col2a, col2b = st.columns(2)
g_disc_odslony = col2a.text_input("Google Discover - odsłony:", key="g_disc_odslony", placeholder=" ")
g_disc_klik = col2b.text_input("Google Discover - kliknięcia:", key="g_disc_klik", placeholder=" ")
links_disc = st.text_area("Linki (opcjonalnie):", key="links_disc", height=80, help=POMOC_LINKI)
info_o_linkach(links_disc)
img_disc = st.file_uploader("Dodaj grafiki (Google Discover)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p2")
uklad_disc = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u2")
st.markdown("---")

# --- SEKCJA 3 ---
st.markdown("#### 3. Wyniki wyszukiwania w wyszukiwarce Google")
desc_wyniki = st.text_area("Opis sekcji (Wyszukiwarka):", key="desc_wyniki", height=70, placeholder=" ", help=POMOC_TEKST)
col3a, col3b, col3c = st.columns(3)
g_wyniki_odslony = col3a.text_input("Google wyniki - odsłony:", key="g_wyniki_odslony", placeholder=" ")
g_wyniki_klik = col3b.text_input("Google wyniki - kliknięcia:", key="g_wyniki_klik", placeholder=" ")
g_ai = col3c.text_input("Generatywna AI:", key="g_ai", placeholder=" ")
links_wyniki = st.text_area("Linki (opcjonalnie):", key="links_wyniki", height=80, help=POMOC_LINKI)
info_o_linkach(links_wyniki)
img_wyniki = st.file_uploader("Dodaj grafiki (Wyniki Wyszukiwania i AI)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p3")
uklad_wyniki = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u3")
st.markdown("---")

# --- SEKCJA 4: FACEBOOK ---
st.markdown("#### 4. Facebook")
desc_fb = st.text_area("Opis sekcji (Facebook):", key="desc_fb", height=70, placeholder=" ", help=POMOC_TEKST)
fb_zasieg = st.text_input("Zasięgi na FB:", key="fb_zasieg", placeholder=" ")
links_fb = st.text_area("Linki do postów (opcjonalnie):", key="links_fb", height=120, help=POMOC_LINKI)
info_o_linkach(links_fb)
img_fb = st.file_uploader("Dodaj grafiki (Facebook)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p4")
uklad_fb = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u4")
st.markdown("---")

# --- SEKCJA 5: LINKEDIN ---
st.markdown("#### 5. LinkedIn")
desc_li = st.text_area("Opis sekcji (LinkedIn):", key="desc_li", height=70, placeholder=" ", help=POMOC_TEKST)
li_zasieg = st.text_input("Wyświetlenia na LinkedIn:", key="li_zasieg", placeholder=" ")
links_li = st.text_area("Linki do postów (opcjonalnie):", key="links_li", height=80, help=POMOC_LINKI)
info_o_linkach(links_li)
img_li = st.file_uploader("Dodaj grafiki (LinkedIn)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p5")
uklad_li = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u5")
st.markdown("---")

# --- SŁOWNICZEK (edytowalny) ---
st.markdown("#### Słowniczek pojęć")
slowniczek_wlaczony = st.checkbox(
    "Dodaj słowniczek pojęć na końcu raportu",
    value=True,
    key="slowniczek",
    help="Słowniczek zawiera tylko te pojęcia, których dotyczą wypełnione pola: Google Discover, "
         "wyniki wyszukiwania w Google, generatywna AI. Poniżej możesz edytować tytuły i treść definicji.",
)

_pojecie_uzyte = {
    "discover": bool(str(g_disc_odslony).strip() or str(g_disc_klik).strip()),
    "wyniki": bool(str(g_wyniki_odslony).strip() or str(g_wyniki_klik).strip()),
    "ai": bool(str(g_ai).strip()),
}

if slowniczek_wlaczony:
    _widoczne = [st.session_state[sl_key(p, LANG, "t")] for p in SL_ID if _pojecie_uzyte[p]]
    if _widoczne:
        st.caption("W raporcie pojawią się definicje: " + "; ".join(_widoczne) + ".")
    else:
        st.caption("Żadne z powiązanych pól nie jest wypełnione, więc słowniczek nie pojawi się w raporcie.")

    with st.expander(f"✏️ Edytuj słowniczek (język raportu: {wybor_jezyka})"):
        st.caption("Zmiany dotyczą bieżącego raportu i wybranego języka. Pojęcie bez wypełnionych pól "
                   "nie trafi do raportu, nawet jeśli jest tu edytowane. Pusta definicja = pojęcie pominięte. "
                   "Adresy zaczynające się od https:// lub www. będą klikalne.")
        for p in SL_ID:
            nota = "" if _pojecie_uzyte[p] else "  *(nie pojawi się: brak danych w powiązanych polach)*"
            st.markdown(f"**{SLOWNICZEK_WG_JEZYKA[LANG][p][0]}**{nota}")
            st.text_input("Tytuł pojęcia:", key=sl_key(p, LANG, "t"))
            st.text_area("Definicja:", key=sl_key(p, LANG, "d"), height=120)
            st.markdown("---")
        st.button("↩️ Przywróć domyślne teksty słowniczka",
                  on_click=przywroc_slowniczek, args=(LANG,))

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# GENERATOR PDF
# ============================================================
if st.button("Generuj nowoczesny PDF z grafikami", type="primary", use_container_width=True):

    if not os.path.exists(font_file):
        st.error(f"Brak pliku {font_file} w folderze aplikacji. Bez niego polskie znaki nie zadziałają.")
        st.stop()

    if not bez_osoby and wybrana_osoba not in dostepne_osoby:
        st.error("Wybierz z listy osobę kontaktową albo zaznacz „Nie pokazuj osoby kontaktowej w raporcie”.")
        st.stop()

    FONT = 'DejaVu'
    LINKCOL = (0, 90, 200)

    # ---------- teksty zależne od języka ----------
    if LANG == "en":
        if NAZWA_PORTALU.startswith("Portal "):
            nazwa_portalu_pdf = NAZWA_PORTALU[len("Portal "):] + " portal"
        else:
            nazwa_portalu_pdf = NAZWA_PORTALU
        okres_pdf = okres_en(okres)
        stanowisko_pdf = STANOWISKA_EN.get(stanowisko, stanowisko)
    else:
        nazwa_portalu_pdf = NAZWA_PORTALU
        okres_pdf = okres
        stanowisko_pdf = stanowisko

    def opis_pdf(klucz, wartosc):
        """Nieedytowany opis domyślny -> wersja angielska; własny tekst zostaje bez zmian."""
        if LANG == "en" and wartosc.strip() == DOMYSLNE_OPISY[klucz]:
            return DOMYSLNE_OPISY_EN[klucz]
        return wartosc

    def kpi_lab(n):
        return KPI_EN.get(n, n) if LANG == "en" else n

    class ReportPDF(FPDF):
        firma_txt = ""
        okres_txt = ""
        data_txt = ""
        stopka_txt = ("AVT-Korporacja sp. z o.o. | Leszczynowa 11, 03-197 Warszawa\n"
                      "NIP: 5270200177 | KRS: 0000035930")

        def header(self):
            self.set_fill_color(*BAR)
            self.rect(0, 0, 210, 6, 'F')
            if self.page_no() == 1:
                if logo_buf:
                    logo_buf.seek(0)
                    self.image(logo_buf, x=ML, y=12, w=w_cover)
                self.set_y(36)
            else:
                if logo_buf:
                    logo_buf.seek(0)
                    self.image(logo_buf, x=ML, y=10, w=w_small)
                self.set_xy(ML + 80, 12)
                self.set_font(FONT, '', 8)
                self.set_text_color(140, 140, 140)
                naglowek = " | ".join(x for x in [self.firma_txt, self.okres_txt] if x)
                self.cell(W - 80, 5, naglowek, align='R')
                self.set_draw_color(225, 225, 225)
                self.set_line_width(0.2)
                self.line(ML, 24, ML + W, 24)
                self.set_y(TOP2)

        def footer(self):
            self.set_draw_color(*LINE)
            self.set_line_width(0.5)
            self.line(ML, 271, ML + W, 271)
            self.set_font(FONT, '', 8.5)
            self.set_text_color(120, 120, 120)
            self.set_xy(ML, 274)
            self.multi_cell(100, 4.5, self.stopka_txt, align='L')
            self.set_xy(ML + W - 70, 274)
            self.cell(70, 4.5, f"{T['data']}: {self.data_txt}", align='R')
            self.set_xy(ML + W - 70, 278.5)
            self.cell(70, 4.5, f"{T['strona']} {self.page_no()}/{{nb}}", align='R')

    pdf = ReportPDF()
    pdf.firma_txt = firma
    pdf.okres_txt = okres_pdf
    pdf.data_txt = data_raportu.strftime('%d.%m.%Y')
    pdf.alias_nb_pages()
    pdf.set_margins(ML, 10, ML)
    pdf.set_auto_page_break(False)
    pdf.add_font('DejaVu', '', font_file)
    pdf.add_font('DejaVu', 'B', font_bold_file if os.path.exists(font_bold_file) else font_file)

    def new_page():
        pdf.add_page()
        pdf.set_y(TOP2)

    def ensure_space(h):
        if pdf.get_y() + h > LIMIT:
            new_page()

    # ---------- tekst z klikalnymi linkami ----------
    def rich_pieces(raw):
        m = LINK_TEKST_RE.search(raw)
        if not m:
            return [(raw, None)]
        pre = raw[:m.start()]
        u = m.group(0)
        core = u.rstrip(",.;:!?)'\"»")
        if not core:
            return [(raw, None)]
        tail = u[len(core):]
        target = core if core.lower().startswith("http") else "https://" + core
        out = []
        if pre:
            out.append((pre, None))
        out.append((core, target))
        if tail:
            out.append((tail, None))
        return out

    def wrap_rich(txt, width, size=9.5):
        pdf.set_font(FONT, '', size)
        maxw = width - 1

        def tw(s):
            return pdf.get_string_width(s)

        sp_w = tw(" ")
        lines = []
        for para in str(txt).split("\n"):
            if not para.strip():
                lines.append([])
                continue
            cur, cur_w = [], 0.0
            for raw in para.split():
                pieces = rich_pieces(raw)
                tok_w = sum(tw(t) for t, _u in pieces)
                gap = sp_w if cur else 0
                if cur and cur_w + gap + tok_w > maxw:
                    lines.append(cur)
                    cur, cur_w, gap = [], 0.0, 0
                if tok_w <= maxw:
                    if gap:
                        cur.append((" ", None))
                    cur.extend(pieces)
                    cur_w += gap + tok_w
                else:
                    for t, u in pieces:
                        while t:
                            avail = maxw - cur_w
                            k = len(t)
                            while k > 0 and tw(t[:k]) > avail:
                                k -= 1
                            if k == 0:
                                if cur:
                                    lines.append(cur)
                                    cur, cur_w = [], 0.0
                                    continue
                                k = 1
                            cur.append((t[:k], u))
                            cur_w += tw(t[:k])
                            t = t[k:]
                            if t:
                                lines.append(cur)
                                cur, cur_w = [], 0.0
            lines.append(cur)
        return lines

    def draw_rich_line(segs, x, y, lh, size, color):
        old_margin = pdf.c_margin
        pdf.c_margin = 0
        cx = x
        for text, url in segs:
            pdf.set_font(FONT, 'U' if url else '', size)
            pdf.set_text_color(*(LINKCOL if url else color))
            w = pdf.get_string_width(text)
            pdf.set_xy(cx, y)
            pdf.cell(w, lh, text, link=url or "")
            cx += w
        pdf.c_margin = old_margin

    def draw_rich_lines(lines, x, lh, size, color):
        for segs in lines:
            ensure_space(lh)
            y = pdf.get_y()
            if segs:
                draw_rich_line(segs, x, y, lh, size, color)
            pdf.set_y(y + lh)

    def prep_images(files):
        out = []
        for f in files or []:
            try:
                f.seek(0)
                im = Image.open(f)
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGBA")
                    bg = Image.new("RGB", im.size, (255, 255, 255))
                    bg.paste(im, mask=im.split()[-1])
                    im = bg
                else:
                    im = im.convert("RGB")
                if im.width > 1800:
                    im = im.resize((1800, int(im.height * 1800 / im.width)), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=90)
                buf.seek(0)
                out.append({"buf": buf, "ratio": im.height / im.width})
            except Exception:
                continue
        return out

    def draw_cards(items, dark=False):
        gap, ch = 4, 25
        for start in range(0, len(items), 4):
            row = items[start:start + 4]
            n = len(row)
            cw = min((W - gap * (n - 1)) / n, 58)
            ensure_space(ch)
            y = pdf.get_y()
            for i, (label, value) in enumerate(row):
                x = ML + i * (cw + gap)
                pdf.set_fill_color(*(MAIN if dark else LIGHT))
                pdf.rect(x, y, cw, ch, 'F')
                pdf.set_fill_color(*ACCENT)
                pdf.rect(x, y, cw, 1.2, 'F')
                pdf.set_xy(x, y + 4)
                pdf.set_font(FONT, 'B', 17)
                pdf.set_text_color(*((255, 255, 255) if dark else MAIN))
                pdf.cell(cw, 9, value, align='C')
                pdf.set_xy(x + 2, y + 14)
                pdf.set_font(FONT, '', 8.5)
                pdf.set_text_color(*((240, 240, 240) if dark else GREY))
                pdf.multi_cell(cw - 4, 4, label, align='C')
            pdf.set_y(y + ch + 4)

    def draw_link_chips(run):
        ch, gap_x, gap_y, pad = 6.5, 3, 2.5, 4
        ensure_space(ch + 3)
        x = ML
        y = pdf.get_y()
        for (_t, lab, url, _r) in run:
            pdf.set_font(FONT, '', 8.5)
            w = min(max(18, pdf.get_string_width(lab) + 2 * pad), W)
            if x + w > ML + W + 0.01:
                y += ch + gap_y
                x = ML
                if y + ch > LIMIT:
                    new_page()
                    y = pdf.get_y()
            pdf.set_fill_color(*LIGHT)
            pdf.set_draw_color(225, 225, 225)
            pdf.set_line_width(0.2)
            pdf.rect(x, y, w, ch, 'DF')
            pdf.set_fill_color(*ACCENT)
            pdf.rect(x, y + ch - 0.6, w, 0.6, 'F')
            pdf.set_xy(x, y)
            pdf.set_font(FONT, '', 8.5)
            pdf.set_text_color(*MAIN)
            pdf.cell(w, ch, lab, align='C', link=url)
            x += w + gap_x
        pdf.set_y(y + ch + 3)

    def draw_link_list(run):
        maxw = W - 12
        for (_t, lab, url, _r) in run:
            ensure_space(7)
            y = pdf.get_y()
            pdf.set_font(FONT, '', 9)
            txt = lab
            if pdf.get_string_width(txt) > maxw:
                while len(txt) > 4 and pdf.get_string_width(txt + "…") > maxw:
                    txt = txt[:-1]
                txt = txt.rstrip() + "…"
            pdf.set_fill_color(*ACCENT)
            pdf.rect(ML + 2, y + 2.3, 1.8, 1.8, 'F')
            pdf.set_xy(ML + 7, y)
            pdf.set_font(FONT, '', 9)
            pdf.set_text_color(*MAIN)
            pdf.cell(W - 8, 6, txt, link=url)
            pdf.set_draw_color(232, 232, 232)
            pdf.set_line_width(0.2)
            pdf.line(ML + 1, y + 6.2, ML + W - 1, y + 6.2)
            pdf.set_y(y + 6.6)
        pdf.set_y(pdf.get_y() + 1.5)

    def render_links(elementy):
        i = 0
        while i < len(elementy):
            typ, lab, url, rodzaj = elementy[i]
            if typ == "head":
                ensure_space(16)
                y = pdf.get_y() + 1
                pdf.set_xy(ML + 1, y)
                pdf.set_font(FONT, 'B', 10)
                pdf.set_text_color(*MAIN)
                pdf.cell(W - 2, 6, lab)
                pdf.set_y(y + 7.5)
                i += 1
            else:
                chip = (rodzaj == "post")
                run = []
                while (i < len(elementy) and elementy[i][0] == "link"
                       and (elementy[i][3] == "post") == chip):
                    run.append(elementy[i])
                    i += 1
                if chip:
                    draw_link_chips(run)
                else:
                    draw_link_list(run)
        ensure_space(6)
        y = pdf.get_y()
        pdf.set_xy(ML + 1, y)
        pdf.set_font(FONT, '', 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(W - 2, 5, T["kliknij"])
        pdf.set_y(y + 7)

    def place_row(items, col_w, centers, max_h):
        sizes = []
        for it in items:
            w, h = col_w, col_w * it["ratio"]
            if h > max_h:
                w, h = max_h / it["ratio"], max_h
            sizes.append((w, h))
        row_h = max(h for _, h in sizes)
        s = 1.0
        avail = LIMIT - pdf.get_y()
        if row_h > avail:
            if avail / row_h >= 0.7 and avail >= 50:
                s = avail / row_h
            else:
                new_page()
                avail = LIMIT - pdf.get_y()
                if row_h > avail:
                    s = avail / row_h
        y = pdf.get_y()
        for it, (w, h), cx in zip(items, sizes, centers):
            w, h = w * s, h * s
            x = cx - w / 2
            it["buf"].seek(0)
            pdf.image(it["buf"], x=x, y=y, w=w, h=h)
            pdf.set_draw_color(220, 220, 220)
            pdf.set_line_width(0.2)
            pdf.rect(x, y, w, h)
        pdf.set_y(y + row_h * s + 6)

    def render_section(title, desc, kpis, files, two_cols, links_raw=""):
        kpis = [(l, str(v).strip()) for l, v in kpis if str(v).strip()]
        imgs = prep_images(files)
        linki, _dup = przygotuj_linki(links_raw)
        if not kpis and not imgs and not linki:
            return
        if any(e[0] == "link" and e[3] == "auto" and host_dozwolony(e[2]) for e in linki):
            with st.spinner(f"Pobieram tytuły artykułów ({title})…"):
                linki = uzupelnij_tytuly(linki)

        desc_lines = wrap_rich(desc.strip(), W - 2, 9.5) if desc.strip() else []

        need = 13
        if desc_lines:
            need += len(desc_lines) * 4.8 + 4
        if kpis:
            need += ((len(kpis) + 3) // 4) * 29
        if linki:
            need += 16
        if imgs:
            col_w = 83 if two_cols else 170
            need += min(col_w * imgs[0]["ratio"], 60)
        ensure_space(min(need, 120))

        y = pdf.get_y()
        pdf.set_fill_color(*MAIN)
        pdf.rect(ML, y, W, 9, 'F')
        pdf.set_fill_color(*ACCENT)
        pdf.rect(ML, y, 3, 9, 'F')
        pdf.set_xy(ML + 7, y)
        pdf.set_font(FONT, 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(W - 10, 9, title)
        pdf.set_y(y + 13)

        if desc_lines:
            draw_rich_lines(desc_lines, ML + 1, 4.8, 9.5, GREY)
            pdf.set_y(pdf.get_y() + 4)

        if kpis:
            draw_cards(kpis)

        if linki:
            render_links(linki)

        if imgs:
            pdf.set_y(pdf.get_y() + 2)
            if two_cols:
                for i in range(0, len(imgs), 2):
                    row = imgs[i:i + 2]
                    centers = [ML + 41.5, ML + W - 41.5][:len(row)]
                    place_row(row, 83, centers, 150)
            else:
                for it in imgs:
                    place_row([it], 170, [105], 200)

        pdf.set_y(pdf.get_y() + 8)

    def render_slowniczek(wpisy):
        if not wpisy:
            return
        pierwsze_linie = len(wrap_rich(wpisy[0][1], W - 2, 9.5))
        ensure_space(13 + 7 + min(pierwsze_linie, 3) * 4.8)

        y = pdf.get_y()
        pdf.set_fill_color(*MAIN)
        pdf.rect(ML, y, W, 9, 'F')
        pdf.set_fill_color(*ACCENT)
        pdf.rect(ML, y, 3, 9, 'F')
        pdf.set_xy(ML + 7, y)
        pdf.set_font(FONT, 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(W - 10, 9, T["slowniczek"])
        pdf.set_y(y + 13)

        for termin, definicja in wpisy:
            linie = wrap_rich(definicja, W - 2, 9.5)
            ensure_space(7 + min(len(linie), 3) * 4.8)
            y0 = pdf.get_y()
            pdf.set_fill_color(*ACCENT)
            pdf.rect(ML + 1, y0 + 2.2, 1.8, 1.8, 'F')
            pdf.set_xy(ML + 6, y0)
            pdf.set_font(FONT, 'B', 10)
            pdf.set_text_color(*MAIN)
            pdf.cell(W - 7, 6, termin)
            pdf.set_y(y0 + 6.5)
            draw_rich_lines(linie, ML + 1, 4.8, 9.5, GREY)
            pdf.set_y(pdf.get_y() + 4)
        pdf.set_y(pdf.get_y() + 2)

    # ---------- STRONA TYTUŁOWA ----------
    pdf.add_page()

    pf_h = w_cover * logo_ratio if logo_ratio else 11.0
    pf_top, pf_bottom = 12, 12 + pf_h
    cy = pf_top + pf_h / 2

    right_bottom = pf_bottom
    drawn = False
    if logo_klienta:
        try:
            logo_klienta.seek(0)
            lim = Image.open(logo_klienta).convert("RGBA")
            lb = io.BytesIO()
            lim.save(lb, "PNG")
            lb.seek(0)
            ratio = lim.height / lim.width
            lw, lh = 55, 55 * ratio
            if lh > 14:
                lh, lw = 14, 14 / ratio
            ly = cy - lh / 2
            pdf.image(lb, x=ML + W - lw, y=ly, w=lw, h=lh)
            right_bottom = max(pf_bottom, ly + lh)
            drawn = True
        except Exception:
            drawn = False
    if not drawn and firma.strip():
        pdf.set_font(FONT, 'B', 15)
        pdf.set_text_color(*MAIN)
        pdf.set_xy(ML + W - 90, cy - 3.5)
        pdf.multi_cell(90, 7, firma.strip(), align='R')
        right_bottom = max(pf_bottom, pdf.get_y())

    if okres_pdf.strip():
        pdf.set_xy(ML, right_bottom + 2.5)
        pdf.set_font(FONT, '', 10)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(W, 5, f"{T['okres']}: {okres_pdf.strip()}", align='R')
        right_bottom = right_bottom + 2.5 + 5

    y = right_bottom + 6

    pdf.set_draw_color(225, 225, 225)
    pdf.set_line_width(0.3)
    pdf.line(ML, y, ML + W, y)

    meta_txt = ""
    if autor.strip():
        meta_txt = f"{T['przygotowal']}: {autor.strip()}"
        if stanowisko_pdf.strip():
            meta_txt += f", {stanowisko_pdf.strip()}"

    if meta_txt:
        pdf.set_xy(ML, y + 3)
        pdf.set_font(FONT, '', 9)
        pdf.set_text_color(*GREY)
        pdf.cell(W, 5, meta_txt)
        pdf.set_y(y + 14)
    else:
        pdf.set_y(y + 6)

    wartosci = {
        "Odsłony portalu": odslony, "Zdarzenia na portalu": zdarzenia,
        "Zaangażowanie": zaangazowanie, "Widoczność artykułu w serwisie": zajawka,
        "Odsłony w Google Discover": g_disc_odslony, "Kliknięcia z Google Discover": g_disc_klik,
        "Odsłony w wyszukiwarce Google": g_wyniki_odslony,
        "Kliknięcia z wyszukiwarki Google": g_wyniki_klik,
        "Generatywna AI": g_ai, "Zasięg na Facebooku": fb_zasieg,
        "Wyświetlenia na LinkedIn": li_zasieg,
    }
    kpi_cover = [(kpi_lab(n), str(wartosci[n]).strip()) for n in kpi_wybrane if str(wartosci.get(n, "")).strip()]
    if kpi_cover:
        pdf.set_font(FONT, 'B', 11)
        pdf.set_text_color(*MAIN)
        pdf.set_x(ML)
        pdf.cell(W, 6, T["najwazniejsze"])
        pdf.set_y(pdf.get_y() + 9)
        draw_cards(kpi_cover, dark=True)

    if podsumowanie.strip():
        lines_p = wrap_rich(podsumowanie.strip(), W - 12, 10)
        bh = len(lines_p) * 5 + 15
        ensure_space(bh)
        y = pdf.get_y()
        pdf.set_fill_color(*LIGHT)
        pdf.rect(ML, y, W, bh, 'F')
        pdf.set_fill_color(*ACCENT)
        pdf.rect(ML, y, 2.5, bh, 'F')
        pdf.set_xy(ML + 7, y + 3.5)
        pdf.set_font(FONT, 'B', 8.5)
        pdf.set_text_color(*LABEL)
        pdf.cell(60, 4, T["podsumowanie"])
        for i, segs in enumerate(lines_p):
            if segs:
                draw_rich_line(segs, ML + 7, y + 9 + i * 5, 5, 10, (70, 70, 70))
        pdf.set_y(y + bh + 4)

    pdf.set_y(pdf.get_y() + 6)

    # ---------- SEKCJE ----------
    render_section(nazwa_portalu_pdf, opis_pdf("desc_portal", desc_portal), [
        (kpi_lab("Zdarzenia na portalu"), zdarzenia),
        (T["odslony"], odslony),
        (kpi_lab("Zaangażowanie"), zaangazowanie),
        (kpi_lab("Widoczność artykułu w serwisie"), zajawka),
    ], img_portal, uklad_portal == UKLAD[1], links_portal)

    render_section(T["discover"], opis_pdf("desc_disc", desc_disc), [
        (T["odslony"], g_disc_odslony),
        (T["klikniecia"], g_disc_klik),
    ], img_disc, uklad_disc == UKLAD[1], links_disc)

    render_section(T["wyniki"], opis_pdf("desc_wyniki", desc_wyniki), [
        (T["odslony"], g_wyniki_odslony),
        (T["klikniecia"], g_wyniki_klik),
        (kpi_lab("Generatywna AI"), g_ai),
    ], img_wyniki, uklad_wyniki == UKLAD[1], links_wyniki)

    render_section(T["fb"], opis_pdf("desc_fb", desc_fb), [
        (kpi_lab("Zasięg na Facebooku"), fb_zasieg),
    ], img_fb, uklad_fb == UKLAD[1], links_fb)

    render_section(T["li"], opis_pdf("desc_li", desc_li), [
        (kpi_lab("Wyświetlenia na LinkedIn"), li_zasieg),
    ], img_li, uklad_li == UKLAD[1], links_li)

    # ---------- SŁOWNICZEK POJĘĆ (z edytowalnych pól) ----------
    if slowniczek_wlaczony:
        wpisy_slowniczka = []
        for p in SL_ID:
            if not _pojecie_uzyte[p]:
                continue
            tytul = st.session_state.get(sl_key(p, LANG, "t"), "").strip()
            definicja = st.session_state.get(sl_key(p, LANG, "d"), "").strip()
            if tytul and definicja:
                wpisy_slowniczka.append((tytul, definicja))
        render_slowniczek(wpisy_slowniczka)

    # ---------- KARTA KONTAKTOWA ----------
    if autor.strip() or email.strip() or telefon.strip() or telefon_kom.strip():
        czesci_kontaktu = []
        if email.strip():
            czesci_kontaktu.append(f"{T['email']}: {email.strip()}")
        if telefon.strip():
            czesci_kontaktu.append(f"{T['tel']}: {telefon.strip()}")
        if telefon_kom.strip():
            czesci_kontaktu.append(f"{T['tel_kom']}: {telefon_kom.strip()}")

        separator = "      "
        pdf.set_font(FONT, '', 9.5)
        linie_kontaktu = []
        if czesci_kontaktu:
            jedna_linia = separator.join(czesci_kontaktu)
            if pdf.get_string_width(jedna_linia) <= W - 14:
                linie_kontaktu = [jedna_linia]
            else:
                mail_czesci = [c for c in czesci_kontaktu if c.startswith(T["email"])]
                tel_czesci = [c for c in czesci_kontaktu if not c.startswith(T["email"])]
                linie_kontaktu = [x for x in [separator.join(mail_czesci), separator.join(tel_czesci)] if x]

        kursor = 9.5
        if autor.strip():
            kursor = 17.0
        stanowisko_y = None
        if stanowisko_pdf.strip():
            stanowisko_y = kursor
            kursor += 6.5
        kontakt_y = kursor
        wysokosc_karty = max(31.0, kontakt_y + len(linie_kontaktu) * 5.5 + 2.5)

        ensure_space(wysokosc_karty + 5)
        y = pdf.get_y() + 2
        pdf.set_fill_color(*LIGHT)
        pdf.rect(ML, y, W, wysokosc_karty, 'F')
        pdf.set_fill_color(*ACCENT)
        pdf.rect(ML, y, 2.5, wysokosc_karty, 'F')
        pdf.set_xy(ML + 8, y + 3.5)
        pdf.set_font(FONT, 'B', 8.5)
        pdf.set_text_color(*LABEL)
        pdf.cell(W - 12, 4, T["pytania"])
        if autor.strip():
            pdf.set_xy(ML + 8, y + 9.5)
            pdf.set_font(FONT, 'B', 13)
            pdf.set_text_color(*MAIN)
            pdf.cell(W - 12, 7, autor.strip())
        if stanowisko_y is not None:
            pdf.set_xy(ML + 8, y + stanowisko_y)
            pdf.set_font(FONT, '', 10)
            pdf.set_text_color(*GREY)
            pdf.cell(W - 12, 5, stanowisko_pdf.strip())
        for i, linia in enumerate(linie_kontaktu):
            pdf.set_xy(ML + 8, y + kontakt_y + i * 5.5)
            pdf.set_font(FONT, '', 9.5)
            pdf.set_text_color(70, 70, 70)
            pdf.cell(W - 12, 5, linia)
        pdf.set_y(y + wysokosc_karty + 4)

    # ---------- WYNIK ----------
    try:
        pdf_bytes = bytes(pdf.output())
        st.success("✨ Raport PDF został wygenerowany pomyślnie!")

        st.markdown("### Podgląd raportu")
        pdf_viewer(input=pdf_bytes, width=700)

        st.markdown("<br>", unsafe_allow_html=True)
        nazwa_pliku = re.sub(r"[^\w\-]+", "_", firma.strip()) or "raport"
        st.download_button(
            label="Pobierz Raport PDF 📥",
            data=pdf_bytes,
            file_name=f"Raport_{nazwa_pliku}{'_EN' if LANG == 'en' else ''}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania: {e}")

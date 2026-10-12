import streamlit as st
from streamlit_oauth import OAuth2Component
import requests
from fpdf import FPDF
import io
import os
import re
from datetime import date
import PyPDF2
from PIL import Image
from streamlit_pdf_viewer import pdf_viewer

# ============================================================
# USTAWIENIA
# ============================================================
st.set_page_config(page_title="Generator Raportów - Produkty i Firmy", page_icon="📊", layout="wide")

# Wstrzykiwany CSS - czerwona ramka dla pustych pól (z ukrytym placeholderem)
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
logo_svg = "logo-irbj-new.svg"
logo_png = "logo.png"

# ------------------------------------------------------------
# MOTYWY: kolorystyka raportu (RGB) + dostępne logo
#   main   - górny pasek, nagłówki sekcji, ciemne kafelki, tytuły, wartości
#   accent - paski akcentowe na kafelkach i nagłówkach
#   light  - tło jasnych kafelków i ramek
#   bar    - górny pasek strony
#   line   - linia w stopce
#   label  - małe napisy akcentowe (np. PODSUMOWANIE)
#   loga   - {nazwa w menu: (nazwa pliku BEZ rozszerzenia, szerokość na okładce mm, szerokość na kolejnych stronach mm)}
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
}


def znajdz_plik(baza):
    """Zwraca nazwę istniejącego pliku baza.png/.jpg/.jpeg albo None."""
    for ext in (".png", ".jpg", ".jpeg"):
        if os.path.exists(baza + ext):
            return baza + ext
    return None


# ------------------------------------------------------------
# LINKI: parser wklejonej listy (jeden wiersz = jeden element)
#   - wiersz bez adresu URL        -> podtytuł
#   - "Nazwa | https://..."        -> wiersz z własną nazwą
#   - samo "https://facebook..."   -> kafelek "Post N"
#   - inny adres                   -> wiersz ze skróconą nazwą
# ------------------------------------------------------------
URL_RE = re.compile(r"https?://[^\s<>\"]+")
SPOLECZNOSC = {"facebook.com": "fb", "fb.com": "fb", "linkedin.com": "li"}


def host_z_url(url):
    return re.sub(r"^https?://(www\.)?", "", url, flags=re.IGNORECASE).split("/")[0].lower()


def krotka_nazwa_url(url):
    host = host_z_url(url)
    path = re.sub(r"^https?://[^/]+", "", url).split("?")[0].split("#")[0]
    segs = [s for s in path.split("/") if s]
    if len(segs) >= 3:
        return f"{host}/…/{segs[-2]}/{segs[-1]}"
    return host + ("/" + "/".join(segs) if segs else "")


def przygotuj_linki(raw):
    """Zwraca (lista krotek (typ, etykieta, url, kafelek), liczba pominiętych duplikatów)."""
    wynik, widziane, duplikaty = [], set(), 0
    liczniki = {"fb": 0, "li": 0}
    for linia in str(raw or "").splitlines():
        s = linia.strip()
        if not s:
            continue
        m = URL_RE.search(s)
        if not m:
            wynik.append(("head", s.strip(" :,;"), "", False))
            continue
        url = m.group(0).rstrip(",.;)")
        if url in widziane:
            duplikaty += 1
            continue
        widziane.add(url)
        etykieta = s[:m.start()].strip(" |-–:,;")
        kafelek = False
        if not etykieta:
            host = host_z_url(url)
            typ = next((v for k, v in SPOLECZNOSC.items() if host.endswith(k)), None)
            if typ:
                liczniki[typ] += 1
                etykieta = f"Post {liczniki[typ]}"
                kafelek = True
            else:
                etykieta = krotka_nazwa_url(url)
        wynik.append(("link", etykieta, url, kafelek))
    return wynik, duplikaty


def info_o_linkach(raw):
    elementy, dup = przygotuj_linki(raw)
    n = sum(1 for e in elementy if e[0] == "link")
    if n:
        st.caption(f"Rozpoznano linków: {n}" + (f" (pominięto duplikaty: {dup})" if dup else ""))


# Stałe niezależne od motywu
GREY = (100, 100, 100)
ML = 18            # margines lewy/prawy
W = 174            # szerokość treści (210 - 2*18)
LIMIT = 265        # dolna granica treści (nad stopką)
TOP2 = 32          # początek treści na stronach 2+

# ============================================================
# LOGOWANIE OAUTH (Google Workspace)
# ============================================================
DOZWOLONA_DOMENA = "budujemydom.pl"

oauth2 = OAuth2Component(
    client_id=st.secrets["google_oauth"]["client_id"],
    client_secret=st.secrets["google_oauth"]["client_secret"],
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke"
)

if "user_email" not in st.session_state:
    if os.path.exists(logo_svg):
        st.image(logo_svg, width=250)
    elif os.path.exists(logo_png):
        st.image(logo_png, width=250)
    else:
        st.title("Produkty i Firmy")

    st.subheader("Wymagane logowanie")
    st.write("Aby korzystać z aplikacji, zaloguj się firmowym kontem Google.")

    result = oauth2.authorize_button(
        name="🔐 Zaloguj przez Google",
        redirect_uri=st.secrets["google_oauth"]["redirect_uri"],
        scope="openid email profile"
    )

    if result and "token" in result:
        token = result["token"]["access_token"]
        user_info = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {token}"}).json()

        email = user_info.get("email", "").lower()
        if email.endswith("@" + DOZWOLONA_DOMENA) and user_info.get("email_verified"):
            st.session_state.user_email = email
            st.session_state.user_name = user_info.get("name", "")
            st.rerun()
        else:
            st.error(f"Dostęp tylko dla zweryfikowanych kont @{DOZWOLONA_DOMENA}. Próba logowania z adresu: {email}")
    st.stop()

email_user = st.session_state.user_email

with st.sidebar:
    st.caption("Zalogowano jako")
    st.write(f"**{st.session_state.get('user_name', email_user)}**")
    st.caption(email_user)
    if st.button("Wyloguj"):
        st.session_state.pop("user_email", None)
        st.session_state.pop("user_name", None)
        st.rerun()

# ============================================================
# LOGO W INTERFEJSIE
# ============================================================
if os.path.exists(logo_svg):
    st.image(logo_svg, width=250)
elif os.path.exists(logo_png):
    st.image(logo_png, width=250)
else:
    st.title("Produkty i Firmy")

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


def pobierz_profil(email_adres):
    wpis = {}
    try:
        surowy = st.secrets["uzytkownicy"].get(email_adres)
        if surowy:
            wpis = dict(surowy)
    except Exception:
        pass
    return {
        "autor": wpis.get("imie_nazwisko") or st.session_state.get("user_name") or "",
        "stanowisko": wpis.get("stanowisko", ""),
        "email": email_adres,
        "telefon": wpis.get("telefon", ""),
    }


if st.session_state.get("_profil_dla") != email_user:
    for k, v in pobierz_profil(email_user).items():
        st.session_state[k] = v
    st.session_state["_profil_dla"] = email_user

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

st.markdown("---")

# ============================================================
# WYGLĄD RAPORTU (kolorystyka + logo)
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

logo_raport = znajdz_plik(logo_baza)
if logo_raport is None:
    st.warning(f"Nie znaleziono pliku logo „{logo_baza}” (.png/.jpg). "
               f"Dodaj go do repozytorium obok app.py. Na razie użyję logo Produkty i Firmy.")
    logo_raport = znajdz_plik("logo")
    w_cover, w_small = 52, 34
if logo_raport:
    st.image(logo_raport, width=170)

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
    # Dodany placeholder=" " uaktywnia ramkę CSS, gdy pole jest puste
    firma = st.text_input("Raport dla firmy:", key="firma", placeholder=" ")
with col_firma2:
    okres = st.text_input("Okres kampanii:", key="okres", placeholder=" ")
with col_firma3:
    logo_klienta = st.file_uploader("Wgraj logo klienta (opcjonalnie)", type=["png", "jpg", "jpeg"])

st.markdown("#### Autor raportu")
ca1, ca2, ca3, ca4, ca5 = st.columns([2, 2, 2, 1.5, 1.5])
autor = ca1.text_input("Imię i nazwisko:", key="autor", placeholder=" ")
stanowisko = ca2.text_input("Stanowisko:", key="stanowisko", placeholder=" ")
email = ca3.text_input("E-mail:", key="email", placeholder=" ")
telefon = ca4.text_input("Telefon:", key="telefon", placeholder=" ")
data_raportu = ca5.date_input("Data wykonania raportu:", value=date.today())

st.markdown("---")
st.subheader("Strona tytułowa: podsumowanie")
KPI_OPTIONS = [
    "Odsłony portalu", "Zdarzenia na portalu", "Zaangażowanie", "Widoczność artykułu w serwisie",
    "Odsłony w Google Discover", "Kliknięcia z Google Discover",
    "Odsłony w wyszukiwarce Google", "Kliknięcia z wyszukiwarki Google",
    "Generatywna AI", "Zasięg na Facebooku", "Wyświetlenia na LinkedIn",
]
kpi_wybrane = st.multiselect(
    "Kafelki z najważniejszymi wynikami na pierwszej stronie (zalecane 3–4; puste wartości są pomijane):",
    KPI_OPTIONS,
    default=["Odsłony portalu", "Odsłony w wyszukiwarce Google", "Odsłony w Google Discover", "Zaangażowanie"],
)
# Komentarz jest opcjonalny, brak atrybutu placeholder=" " uchroni go przed czerwoną ramką
podsumowanie = st.text_area("Komentarz / podsumowanie do raportu (opcjonalnie):", key="podsumowanie", height=90)
if "http" in podsumowanie.lower():
    st.warning("W podsumowaniu są adresy URL. Wstaw je lepiej w polach „Linki” w odpowiednich sekcjach poniżej: "
               "tam są skracane, klikalne i nie rwą się w połowie słowa.")

st.markdown("---")
st.subheader("Dane, opisy, linki i grafiki dla poszczególnych sekcji")
st.caption("Sekcje bez danych, linków i grafik nie pojawią się w raporcie.")
UKLAD = ["1 w rzędzie", "2 kolumny"]
POMOC_LINKI = ("Jeden wiersz = jeden element. Wiersz bez adresu staje się podtytułem. "
               "Format „Nazwa | https://adres” nadaje własną nazwę. "
               "Adresy z Facebooka i LinkedIna bez nazwy stają się kafelkami „Post 1”, „Post 2”… Duplikaty są pomijane.")

# --- SEKCJA 1 ---
st.markdown(f"#### 1. {NAZWA_PORTALU}")
desc_portal = st.text_area("Opis sekcji (Portal):", value="Statystyki odzwierciedlają bezpośrednią aktywność oraz poziom zaangażowania użytkowników w materiały opublikowane na portalu.", height=70, placeholder=" ")
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
desc_disc = st.text_area("Opis sekcji (Discover):", value="Dane obrazują widoczność artykułu i trafność dopasowania treści do czytelników w kanale Google Discover.", height=70, placeholder=" ")
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
desc_wyniki = st.text_area("Opis sekcji (Wyszukiwarka):", value="Wyniki przedstawiają zasięg organiczny w tradycyjnej wyszukiwarce Google oraz w modułach Generatywnej AI.", height=70, placeholder=" ")
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
desc_fb = st.text_area("Opis sekcji (Facebook):", value="Zestawienie obejmuje zasięg wygenerowany w serwisie Facebook, wspierający główną komunikację.", height=70, placeholder=" ")
fb_zasieg = st.text_input("Zasięgi na FB:", key="fb_zasieg", placeholder=" ")
links_fb = st.text_area("Linki do postów (opcjonalnie):", key="links_fb", height=120, help=POMOC_LINKI)
info_o_linkach(links_fb)
img_fb = st.file_uploader("Dodaj grafiki (Facebook)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p4")
uklad_fb = st.radio("Układ grafik:", UKLAD, horizontal=True, index=1, key="u4")
st.markdown("---")

# --- SEKCJA 5: LINKEDIN ---
st.markdown("#### 5. LinkedIn")
desc_li = st.text_area("Opis sekcji (LinkedIn):", value="Zestawienie obejmuje zasięg publikacji w serwisie LinkedIn, wspierający główną komunikację.", height=70, placeholder=" ")
li_zasieg = st.text_input("Wyświetlenia na LinkedIn:", key="li_zasieg", placeholder=" ")
links_li = st.text_area("Linki do postów (opcjonalnie):", key="links_li", height=80, help=POMOC_LINKI)
info_o_linkach(links_li)
img_li = st.file_uploader("Dodaj grafiki (LinkedIn)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p5")
uklad_li = st.radio("Układ grafik:", UKLAD, horizontal=True, index=0, key="u5")

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# GENERATOR PDF
# ============================================================
if st.button("Generuj nowoczesny PDF z grafikami", type="primary", use_container_width=True):

    if not os.path.exists(font_file):
        st.error(f"Brak pliku {font_file} w folderze aplikacji. Bez niego polskie znaki nie zadziałają.")
        st.stop()

    FONT = 'DejaVu'

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
                if logo_raport:
                    self.image(logo_raport, x=ML, y=12, w=w_cover)
                self.set_y(36)
            else:
                if logo_raport:
                    self.image(logo_raport, x=ML, y=10, w=w_small)
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
            self.cell(70, 4.5, f"Data wykonania raportu: {self.data_txt}", align='R')
            self.set_xy(ML + W - 70, 278.5)
            self.cell(70, 4.5, f"Strona {self.page_no()}/{{nb}}", align='R')

    pdf = ReportPDF()
    pdf.firma_txt = firma
    pdf.okres_txt = okres
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

    def wrap_text(txt, width, size=9.5, style=''):
        """Zawija tekst do podanej szerokości; długie ciągi (np. URL) łamie w razie potrzeby."""
        pdf.set_font(FONT, style, size)
        maxw = width - 2
        lines = []
        for para in str(txt).split("\n"):
            if not para.strip():
                lines.append("")
                continue
            line = ""
            for wd in para.split():
                while pdf.get_string_width(wd) > maxw:
                    cut = len(wd)
                    while cut > 1 and pdf.get_string_width(wd[:cut]) > maxw:
                        cut -= 1
                    if line:
                        lines.append(line)
                        line = ""
                    lines.append(wd[:cut])
                    wd = wd[cut:]
                t = (line + " " + wd).strip()
                if pdf.get_string_width(t) <= maxw:
                    line = t
                else:
                    lines.append(line)
                    line = wd
            lines.append(line)
        return lines

    def count_lines(txt, width, size=9.5):
        return len(wrap_text(txt, width, size))

    def draw_lines(lines, x, w, lh, size, color, style=''):
        """Rysuje linie tekstu, przechodząc na nową stronę, gdy brakuje miejsca."""
        for ln in lines:
            ensure_space(lh)
            y = pdf.get_y()
            pdf.set_xy(x, y)
            pdf.set_font(FONT, style, size)
            pdf.set_text_color(*color)
            pdf.cell(w, lh, ln)
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
        """Kafelki 'Post N' (klikalne), po 6 w rzędzie."""
        per_row, gap, ch = 6, 3, 6.5
        cw = (W - gap * (per_row - 1)) / per_row
        for start in range(0, len(run), per_row):
            ensure_space(ch + 3)
            y = pdf.get_y()
            for j, (_t, lab, url, _k) in enumerate(run[start:start + per_row]):
                x = ML + j * (cw + gap)
                pdf.set_fill_color(*LIGHT)
                pdf.rect(x, y, cw, ch, 'F')
                pdf.set_fill_color(*ACCENT)
                pdf.rect(x, y + ch - 0.6, cw, 0.6, 'F')
                pdf.set_xy(x, y)
                pdf.set_font(FONT, '', 8.5)
                pdf.set_text_color(*MAIN)
                pdf.cell(cw, ch, lab, align='C', link=url)
            pdf.set_y(y + ch + 2.5)

    def draw_link_row(lab, url):
        """Wiersz z klikalną (skróconą w razie potrzeby) nazwą."""
        pdf.set_font(FONT, '', 9.5)
        maxw = W - 9
        if pdf.get_string_width(lab) > maxw:
            while len(lab) > 4 and pdf.get_string_width(lab + "…") > maxw:
                lab = lab[:-1]
            lab += "…"
        ensure_space(7)
        y = pdf.get_y()
        pdf.set_fill_color(*ACCENT)
        pdf.rect(ML + 1, y + 2.2, 1.8, 1.8, 'F')
        pdf.set_xy(ML + 5, y)
        pdf.set_font(FONT, '', 9.5)
        pdf.set_text_color(*MAIN)
        pdf.cell(W - 6, 6, lab, link=url)
        pdf.set_y(y + 6.5)

    def render_links(elementy):
        i = 0
        while i < len(elementy):
            typ, lab, url, kafelek = elementy[i]
            if typ == "head":
                ensure_space(16)
                y = pdf.get_y() + 1
                pdf.set_xy(ML + 1, y)
                pdf.set_font(FONT, 'B', 10)
                pdf.set_text_color(*MAIN)
                pdf.cell(W - 2, 6, lab)
                pdf.set_y(y + 7.5)
                i += 1
            elif kafelek:
                run = []
                while i < len(elementy) and elementy[i][0] == "link" and elementy[i][3]:
                    run.append(elementy[i])
                    i += 1
                draw_link_chips(run)
            else:
                draw_link_row(lab, url)
                i += 1
        pdf.set_y(pdf.get_y() + 3)

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

        desc_lines = wrap_text(desc.strip(), W - 2, 9.5) if desc.strip() else []

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
            draw_lines(desc_lines, ML + 1, W - 2, 4.8, 9.5, GREY)
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

    # ---------- STRONA TYTUŁOWA ----------
    pdf.add_page()

    # Wysokość logo raportu -> wyznacza oś, na której ląduje logo klienta
    pf_h = 11.0
    try:
        with Image.open(logo_raport) as pim:
            pf_h = w_cover * pim.height / pim.width
    except Exception:
        pass
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

    if okres.strip():
        pdf.set_xy(ML, right_bottom + 2.5)
        pdf.set_font(FONT, '', 10)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(W, 5, f"Okres: {okres.strip()}", align='R')
        right_bottom = right_bottom + 2.5 + 5

    y = right_bottom + 6

    pdf.set_draw_color(225, 225, 225)
    pdf.set_line_width(0.3)
    pdf.line(ML, y, ML + W, y)

    meta_txt = ""
    if autor.strip():
        meta_txt = f"Przygotował(a): {autor.strip()}"
        if stanowisko.strip():
            meta_txt += f", {stanowisko.strip()}"

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
    kpi_cover = [(n, str(wartosci[n]).strip()) for n in kpi_wybrane if str(wartosci.get(n, "")).strip()]
    if kpi_cover:
        pdf.set_font(FONT, 'B', 11)
        pdf.set_text_color(*MAIN)
        pdf.set_x(ML)
        pdf.cell(W, 6, "Najważniejsze wyniki")
        pdf.set_y(pdf.get_y() + 9)
        draw_cards(kpi_cover, dark=True)

    if podsumowanie.strip():
        lines_p = wrap_text(podsumowanie.strip(), W - 12, 10)
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
        pdf.cell(60, 4, "PODSUMOWANIE")
        pdf.set_font(FONT, '', 10)
        pdf.set_text_color(70, 70, 70)
        for i, ln in enumerate(lines_p):
            pdf.set_xy(ML + 7, y + 9 + i * 5)
            pdf.cell(W - 12, 5, ln)
        pdf.set_y(y + bh + 4)

    pdf.set_y(pdf.get_y() + 6)

    # ---------- SEKCJE ----------
    render_section(NAZWA_PORTALU, desc_portal, [
        ("Zdarzenia na portalu", zdarzenia),
        ("Odsłony", odslony),
        ("Zaangażowanie", zaangazowanie),
        ("Widoczność artykułu w serwisie", zajawka),
    ], img_portal, uklad_portal == UKLAD[1], links_portal)

    render_section("Google Discover", desc_disc, [
        ("Odsłony", g_disc_odslony),
        ("Kliknięcia", g_disc_klik),
    ], img_disc, uklad_disc == UKLAD[1], links_disc)

    render_section("Wyniki wyszukiwania w wyszukiwarce Google", desc_wyniki, [
        ("Odsłony", g_wyniki_odslony),
        ("Kliknięcia", g_wyniki_klik),
        ("Generatywna AI", g_ai),
    ], img_wyniki, uklad_wyniki == UKLAD[1], links_wyniki)

    render_section("Facebook", desc_fb, [
        ("Zasięg na Facebooku", fb_zasieg),
    ], img_fb, uklad_fb == UKLAD[1], links_fb)

    render_section("LinkedIn", desc_li, [
        ("Wyświetlenia na LinkedIn", li_zasieg),
    ], img_li, uklad_li == UKLAD[1], links_li)

    # ---------- KARTA KONTAKTOWA ----------
    if autor.strip() or email.strip() or telefon.strip():
        ensure_space(36)
        y = pdf.get_y() + 2
        pdf.set_fill_color(*LIGHT)
        pdf.rect(ML, y, W, 31, 'F')
        pdf.set_fill_color(*ACCENT)
        pdf.rect(ML, y, 2.5, 31, 'F')
        pdf.set_xy(ML + 8, y + 3.5)
        pdf.set_font(FONT, 'B', 8.5)
        pdf.set_text_color(*LABEL)
        pdf.cell(W - 12, 4, "MASZ PYTANIA? SKONTAKTUJ SIĘ Z MNĄ")
        if autor.strip():
            pdf.set_xy(ML + 8, y + 9.5)
            pdf.set_font(FONT, 'B', 13)
            pdf.set_text_color(*MAIN)
            pdf.cell(W - 12, 7, autor.strip())
        if stanowisko.strip():
            pdf.set_xy(ML + 8, y + 17)
            pdf.set_font(FONT, '', 10)
            pdf.set_text_color(*GREY)
            pdf.cell(W - 12, 5, stanowisko.strip())
        kontakt = []
        if email.strip():
            kontakt.append(f"E-mail: {email.strip()}")
        if telefon.strip():
            kontakt.append(f"Tel.: {telefon.strip()}")
        if kontakt:
            pdf.set_xy(ML + 8, y + 23.5)
            pdf.set_font(FONT, '', 9.5)
            pdf.set_text_color(70, 70, 70)
            pdf.cell(W - 12, 5, "      ".join(kontakt))
        pdf.set_y(y + 35)

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
            file_name=f"Raport_{nazwa_pliku}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania: {e}")

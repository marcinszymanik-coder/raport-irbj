import streamlit as st
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

font_file = "DejaVuSans.ttf"
font_bold_file = "DejaVuSans-Bold.ttf"   # opcjonalnie: prawdziwy pogrubiony krój
logo_svg = "logo-irbj-new.svg"
logo_png = "logo.png"

# Domyślne dane autora (uzupełnij raz, a będą wstawiane automatycznie)
DOMYSLNY_AUTOR = ""
DOMYSLNE_STANOWISKO = ""
DOMYSLNY_EMAIL = ""
DOMYSLNY_TELEFON = ""

# Kolory i wymiary raportu (mm)
PURPLE = (94, 66, 88)
ORANGE = (255, 160, 0)
LIGHT = (247, 244, 248)
GREY = (100, 100, 100)
ML = 18            # margines lewy/prawy
W = 174            # szerokość treści (210 - 2*18)
LIMIT = 265        # dolna granica treści (nad stopką)
TOP2 = 32          # początek treści na stronach 2+

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

# Inicjalizacja zmiennych sesyjnych
keys_to_init = [
    'firma', 'okres', 'zdarzenia', 'odslony', 'zaangazowanie',
    'zajawka', 'g_disc_odslony', 'g_disc_klik',
    'g_wyniki_odslony', 'g_wyniki_klik', 'g_ai', 'fb_zasieg', 'podsumowanie'
]
for k in keys_to_init:
    if k not in st.session_state:
        st.session_state[k] = ""
for k, v in {"autor": DOMYSLNY_AUTOR, "stanowisko": DOMYSLNE_STANOWISKO,
             "email": DOMYSLNY_EMAIL, "telefon": DOMYSLNY_TELEFON}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# PARSOWANIE PDF Z GOOGLE ANALYTICS
# ============================================================
# Liczba: grupy tysięcy dokładnie po 3 cyfry, przecinek, opcjonalnie %
NUM_CORE = r"(?:\d{1,3}(?:[ \u00a0]\d{3})+(?:,\d+)?%?|\d+(?:,\d+)?%?)"
NUM = r"(" + NUM_CORE + r")(?!\.)"   # (?!\.) odrzuca numerację tabeli "1."

# Miesiąc z ewentualnymi spacjami między literami (PyPDF2 robi np. "pa ź")
MONTH = r"[^\W\d_](?:\s*[^\W\d_]){2,8}"
DATE = (r"\d{1,2}\s+" + MONTH + r"\s+\d{4}\s*[-–—]\s*"
        r"\d{1,2}\s+" + MONTH + r"\s+\d{4}")


def label_re(label):
    """Etykieta, w której między znakami mogą być dowolne białe znaki."""
    return r"\s*".join(re.escape(c) for c in label if not c.isspace())


def get_value(text, label):
    m = re.search(label_re(label) + r"\s*" + NUM, text, re.IGNORECASE)
    return m.group(1).replace("\u00a0", " ").strip() if m else ""


def get_period(text):
    # 1) data sklejona z wartością GA4: "14 0511 sty 2026 - 8 pa ź  2026"
    m = re.search(label_re("Odsłony z GA4") + r"\s*" + NUM_CORE + r"(?P<d>" + DATE + r")",
                  text, re.IGNORECASE)
    # 2) zwykła data
    if not m:
        m = re.search(r"(?<!\d)(?P<d>" + DATE + r")", text, re.IGNORECASE)
    if not m:
        return ""
    d = m.group("d")
    d = re.sub(r"(?<=[^\W\d_])\s+(?=[^\W\d_])", "", d)   # "pa ź" -> "paź"
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
# FORMULARZ
# ============================================================
col_firma1, col_firma2, col_firma3 = st.columns([2, 2, 1.5])
with col_firma1:
    firma = st.text_input("Raport dla firmy:", key="firma")
with col_firma2:
    okres = st.text_input("Okres kampanii:", key="okres")
with col_firma3:
    logo_klienta = st.file_uploader("Wgraj logo klienta (opcjonalnie)", type=["png", "jpg", "jpeg"])

st.markdown("#### Autor raportu")
ca1, ca2, ca3, ca4, ca5 = st.columns([2, 2, 2, 1.5, 1.5])
autor = ca1.text_input("Imię i nazwisko:", key="autor")
stanowisko = ca2.text_input("Stanowisko:", key="stanowisko")
email = ca3.text_input("E-mail:", key="email")
telefon = ca4.text_input("Telefon:", key="telefon")
data_raportu = ca5.date_input("Data raportu:", value=date.today())

st.markdown("---")
st.subheader("Strona tytułowa: podsumowanie")
KPI_OPTIONS = [
    "Odsłony portalu", "Zdarzenia na portalu", "Zaangażowanie", "Wyświetlenia zajawki",
    "Odsłony w Google Discover", "Kliknięcia z Google Discover",
    "Odsłony w wyszukiwarce Google", "Kliknięcia z wyszukiwarki Google",
    "Generatywna AI", "Zasięg na Facebooku",
]
kpi_wybrane = st.multiselect(
    "Kafelki z najważniejszymi wynikami na pierwszej stronie (zalecane 3–4; puste wartości są pomijane):",
    KPI_OPTIONS,
    default=["Odsłony portalu", "Odsłony w wyszukiwarce Google", "Odsłony w Google Discover", "Zaangażowanie"],
)
podsumowanie = st.text_area("Komentarz / podsumowanie do raportu (opcjonalnie):", key="podsumowanie", height=90)

st.markdown("---")
st.subheader("Dane, opisy i grafiki dla poszczególnych sekcji")
st.caption("Sekcje bez danych i bez grafik nie pojawią się w raporcie.")
UKLAD = ["1 w rzędzie", "2 kolumny"]

# --- SEKCJA 1 ---
st.markdown("#### 1. Portal Produkty i Firmy")
desc_portal = st.text_area("Opis sekcji (Portal):", "Statystyki odzwierciedlają bezpośrednią aktywność oraz poziom zaangażowania użytkowników w materiały opublikowane na portalu.", height=70)
col1a, col1b = st.columns(2)
zdarzenia = col1a.text_input("Liczba zdarzeń na portalu:", key="zdarzenia")
odslony = col1b.text_input("Odsłony (Portal):", key="odslony")
col1c, col1d = st.columns(2)
zaangazowanie = col1c.text_input("Zaangażowanie:", key="zaangazowanie")
zajawka = col1d.text_input("Wyświetlenia zajawki o artykule:", key="zajawka")
img_portal = st.file_uploader("Dodaj grafiki (Portal Produkty i Firmy)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p1")
uklad_portal = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u1")
st.markdown("---")

# --- SEKCJA 2 ---
st.markdown("#### 2. Google Discover")
desc_disc = st.text_area("Opis sekcji (Discover):", "Dane obrazują widoczność artykułu i trafność dopasowania treści do czytelników w kanale Google Discover.", height=70)
col2a, col2b = st.columns(2)
g_disc_odslony = col2a.text_input("Google Discover - odsłony:", key="g_disc_odslony")
g_disc_klik = col2b.text_input("Google Discover - kliknięcia:", key="g_disc_klik")
img_disc = st.file_uploader("Dodaj grafiki (Google Discover)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p2")
uklad_disc = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u2")
st.markdown("---")

# --- SEKCJA 3 ---
st.markdown("#### 3. Wyniki wyszukiwania w wyszukiwarce Google")
desc_wyniki = st.text_area("Opis sekcji (Wyszukiwarka):", "Wyniki przedstawiają zasięg organiczny w tradycyjnej wyszukiwarce Google oraz w modułach Generatywnej AI.", height=70)
col3a, col3b, col3c = st.columns(3)
g_wyniki_odslony = col3a.text_input("Google wyniki - odsłony:", key="g_wyniki_odslony")
g_wyniki_klik = col3b.text_input("Google wyniki - kliknięcia:", key="g_wyniki_klik")
g_ai = col3c.text_input("Generatywna AI:", key="g_ai")
img_wyniki = st.file_uploader("Dodaj grafiki (Wyniki Wyszukiwania i AI)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p3")
uklad_wyniki = st.radio("Układ grafik:", UKLAD, horizontal=True, key="u3")
st.markdown("---")

# --- SEKCJA 4 ---
st.markdown("#### 4. Media społecznościowe")
desc_inne = st.text_area("Opis sekcji (Social Media):", "Zestawienie obejmuje zasięg wygenerowany poprzez media społecznościowe (głównie Facebook), wspierający główną komunikację.", height=70)
fb_zasieg = st.text_input("Zasięgi na FB:", key="fb_zasieg")
img_inne = st.file_uploader("Dodaj grafiki (Media społecznościowe)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p4")
uklad_inne = st.radio("Układ grafik:", UKLAD, horizontal=True, index=1, key="u4")

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
        stopka_txt = ("AVT-Korporacja sp. z o.o. | Leszczynowa 11, 03-197 Warszawa\n"
                      "NIP: 5270200177 | KRS: 0000035930")

        def header(self):
            self.set_fill_color(*ORANGE)
            self.rect(0, 0, 210, 6, 'F')
            if self.page_no() == 1:
                if os.path.exists(logo_png):
                    self.image(logo_png, x=ML, y=12, w=52)
                self.set_y(36)
            else:
                if os.path.exists(logo_png):
                    self.image(logo_png, x=ML, y=10, w=34)
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
            self.set_draw_color(*ORANGE)
            self.set_line_width(0.5)
            self.line(ML, 271, ML + W, 271)
            self.set_font(FONT, '', 8.5)
            self.set_text_color(120, 120, 120)
            self.set_xy(ML, 274)
            self.multi_cell(130, 4.5, self.stopka_txt, align='L')
            self.set_xy(ML + W - 40, 274)
            self.cell(40, 4.5, f"Strona {self.page_no()}/{{nb}}", align='R')

    pdf = ReportPDF()
    pdf.firma_txt = firma
    pdf.okres_txt = okres
    pdf.alias_nb_pages()
    pdf.set_margins(ML, 10, ML)
    pdf.set_auto_page_break(False)
    pdf.add_font('DejaVu', '', font_file)
    pdf.add_font('DejaVu', 'B', font_bold_file if os.path.exists(font_bold_file) else font_file)

    # ---------- narzędzia ----------
    def new_page():
        pdf.add_page()
        pdf.set_y(TOP2)

    def ensure_space(h):
        if pdf.get_y() + h > LIMIT:
            new_page()

    def count_lines(txt, width, size=9.5):
        pdf.set_font(FONT, '', size)
        total = 0
        for para in str(txt).split("\n"):
            line, n = "", 1
            for wd in para.split():
                t = (line + " " + wd).strip()
                if pdf.get_string_width(t) <= width - 2:
                    line = t
                else:
                    n += 1
                    line = wd
            total += n
        return total

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
                pdf.set_fill_color(*(PURPLE if dark else LIGHT))
                pdf.rect(x, y, cw, ch, 'F')
                pdf.set_fill_color(*ORANGE)
                pdf.rect(x, y, cw, 1.2, 'F')
                pdf.set_xy(x, y + 4)
                pdf.set_font(FONT, 'B', 17)
                pdf.set_text_color(*((255, 255, 255) if dark else PURPLE))
                pdf.cell(cw, 9, value, align='C')
                pdf.set_xy(x + 2, y + 14)
                pdf.set_font(FONT, '', 8.5)
                pdf.set_text_color(*((235, 228, 236) if dark else GREY))
                pdf.multi_cell(cw - 4, 4, label, align='C')
            pdf.set_y(y + ch + 4)

    def place_row(items, col_w, centers, max_h):
        """Umieszcza rząd grafik; skaluje do miejsca albo przenosi na nową stronę."""
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

    def render_section(title, desc, kpis, files, two_cols):
        kpis = [(l, str(v).strip()) for l, v in kpis if str(v).strip()]
        imgs = prep_images(files)
        if not kpis and not imgs:
            return

        # Ile miejsca potrzebuje początek sekcji (nagłówek + opis + kafelki + zalążek grafiki)?
        need = 13
        if desc.strip():
            need += count_lines(desc, W - 2) * 4.8 + 4
        if kpis:
            need += ((len(kpis) + 3) // 4) * 29
        if imgs:
            col_w = 83 if two_cols else 170
            need += min(col_w * imgs[0]["ratio"], 60)
        ensure_space(need)

        # Nagłówek sekcji
        y = pdf.get_y()
        pdf.set_fill_color(*PURPLE)
        pdf.rect(ML, y, W, 9, 'F')
        pdf.set_fill_color(*ORANGE)
        pdf.rect(ML, y, 3, 9, 'F')
        pdf.set_xy(ML + 7, y)
        pdf.set_font(FONT, 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(W - 10, 9, title)
        pdf.set_y(y + 13)

        # Opis
        if desc.strip():
            pdf.set_x(ML + 1)
            pdf.set_font(FONT, '', 9.5)
            pdf.set_text_color(*GREY)
            pdf.multi_cell(W - 2, 4.8, desc.strip(), align='L')
            pdf.set_y(pdf.get_y() + 4)

        # Kafelki
        if kpis:
            draw_cards(kpis)

        # Grafiki
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
    pdf.add_page()   # header ustawia y = 36
    y0 = 36

    # Logo klienta (prawy górny róg)
    logo_bottom = y0
    if logo_klienta:
        try:
            logo_klienta.seek(0)
            lim = Image.open(logo_klienta).convert("RGBA")
            lb = io.BytesIO()
            lim.save(lb, "PNG")
            lb.seek(0)
            ratio = lim.height / lim.width
            lw, lh = 52, 52 * ratio
            if lh > 20:
                lh, lw = 20, 20 / ratio
            pdf.image(lb, x=ML + W - lw, y=y0, w=lw, h=lh)
            logo_bottom = y0 + lh
        except Exception:
            pass

    pdf.set_xy(ML, y0)
    pdf.set_font(FONT, 'B', 9)
    pdf.set_text_color(*ORANGE)
    pdf.cell(110, 5, "RAPORT Z DZIAŁAŃ")
    pdf.set_xy(ML, y0 + 6)
    pdf.set_font(FONT, 'B', 24)
    pdf.set_text_color(*PURPLE)
    pdf.multi_cell(115, 11, firma if firma.strip() else "—", align='L')
    y = pdf.get_y()
    if okres:
        pdf.set_xy(ML, y + 1)
        pdf.set_font(FONT, '', 11)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(115, 7, f"Okres: {okres}")
        y = pdf.get_y() + 7
    y = max(y, logo_bottom) + 4

    # Linia rozdzielająca + autor/data
    pdf.set_draw_color(225, 225, 225)
    pdf.set_line_width(0.3)
    pdf.line(ML, y, ML + W, y)
    meta = []
    if autor.strip():
        a = f"Przygotował(a): {autor.strip()}"
        if stanowisko.strip():
            a += f", {stanowisko.strip()}"
        meta.append(a)
    meta.append(f"Data raportu: {data_raportu.strftime('%d.%m.%Y')}")
    pdf.set_xy(ML, y + 3)
    pdf.set_font(FONT, '', 9)
    pdf.set_text_color(*GREY)
    pdf.cell(W, 5, "   ·   ".join(meta))
    pdf.set_y(y + 14)

    # Kafelki podsumowania
    wartosci = {
        "Odsłony portalu": odslony, "Zdarzenia na portalu": zdarzenia,
        "Zaangażowanie": zaangazowanie, "Wyświetlenia zajawki": zajawka,
        "Odsłony w Google Discover": g_disc_odslony, "Kliknięcia z Google Discover": g_disc_klik,
        "Odsłony w wyszukiwarce Google": g_wyniki_odslony,
        "Kliknięcia z wyszukiwarki Google": g_wyniki_klik,
        "Generatywna AI": g_ai, "Zasięg na Facebooku": fb_zasieg,
    }
    kpi_cover = [(n, str(wartosci[n]).strip()) for n in kpi_wybrane if str(wartosci.get(n, "")).strip()]
    if kpi_cover:
        pdf.set_font(FONT, 'B', 11)
        pdf.set_text_color(*PURPLE)
        pdf.set_x(ML)
        pdf.cell(W, 6, "Najważniejsze wyniki")
        pdf.set_y(pdf.get_y() + 9)
        draw_cards(kpi_cover, dark=True)

    # Komentarz / podsumowanie
    if podsumowanie.strip():
        lines = count_lines(podsumowanie, W - 12, 10)
        bh = lines * 5 + 15
        ensure_space(bh)
        y = pdf.get_y()
        pdf.set_fill_color(*LIGHT)
        pdf.rect(ML, y, W, bh, 'F')
        pdf.set_fill_color(*ORANGE)
        pdf.rect(ML, y, 2.5, bh, 'F')
        pdf.set_xy(ML + 7, y + 3.5)
        pdf.set_font(FONT, 'B', 8.5)
        pdf.set_text_color(*ORANGE)
        pdf.cell(60, 4, "PODSUMOWANIE")
        pdf.set_xy(ML + 7, y + 9)
        pdf.set_font(FONT, '', 10)
        pdf.set_text_color(70, 70, 70)
        pdf.multi_cell(W - 12, 5, podsumowanie.strip(), align='L')
        pdf.set_y(y + bh + 4)

    pdf.set_y(pdf.get_y() + 6)

    # ---------- SEKCJE ----------
    render_section("Portal Produkty i Firmy", desc_portal, [
        ("Zdarzenia na portalu", zdarzenia),
        ("Odsłony", odslony),
        ("Zaangażowanie", zaangazowanie),
        ("Wyświetlenia zajawki artykułu", zajawka),
    ], img_portal, uklad_portal == UKLAD[1])

    render_section("Google Discover", desc_disc, [
        ("Odsłony", g_disc_odslony),
        ("Kliknięcia", g_disc_klik),
    ], img_disc, uklad_disc == UKLAD[1])

    render_section("Wyniki wyszukiwania w wyszukiwarce Google", desc_wyniki, [
        ("Odsłony", g_wyniki_odslony),
        ("Kliknięcia", g_wyniki_klik),
        ("Generatywna AI", g_ai),
    ], img_wyniki, uklad_wyniki == UKLAD[1])

    render_section("Media społecznościowe", desc_inne, [
        ("Zasięg na Facebooku", fb_zasieg),
    ], img_inne, uklad_inne == UKLAD[1])

    # ---------- KARTA KONTAKTOWA ----------
    if autor.strip() or email.strip() or telefon.strip():
        ensure_space(36)
        y = pdf.get_y() + 2
        pdf.set_fill_color(*LIGHT)
        pdf.rect(ML, y, W, 31, 'F')
        pdf.set_fill_color(*ORANGE)
        pdf.rect(ML, y, 2.5, 31, 'F')
        pdf.set_xy(ML + 8, y + 3.5)
        pdf.set_font(FONT, 'B', 8.5)
        pdf.set_text_color(*ORANGE)
        pdf.cell(W - 12, 4, "MASZ PYTANIA? SKONTAKTUJ SIĘ Z NAMI")
        if autor.strip():
            pdf.set_xy(ML + 8, y + 9.5)
            pdf.set_font(FONT, 'B', 13)
            pdf.set_text_color(*PURPLE)
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

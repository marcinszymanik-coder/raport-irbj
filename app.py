import streamlit as st
from fpdf import FPDF
import tempfile
import os
import re
import PyPDF2
from PIL import Image
from streamlit_pdf_viewer import pdf_viewer

# Konfiguracja strony
st.set_page_config(page_title="Generator Raportów - Produkty i Firmy", page_icon="📊", layout="wide")

font_file = "DejaVuSans.ttf"
logo_svg = "logo-irbj-new.svg"
logo_png = "logo.png"

# Wyświetlanie logo w interfejsie webowym
if os.path.exists(logo_svg):
    st.image(logo_svg, width=250)
elif os.path.exists(logo_png):
    st.image(logo_png, width=250)
else:
    st.title("Produkty i Firmy")

st.markdown("### Generator Raportów Zasięgowych")

# Inicjalizacja pustych zmiennych sesyjnych
keys_to_init = [
    'firma', 'okres', 'zdarzenia', 'odslony', 'zaangazowanie', 
    'zajawka', 'g_disc_odslony', 'g_disc_klik', 
    'g_wyniki_odslony', 'g_wyniki_klik', 'g_ai', 'fb_zasieg'
]
for k in keys_to_init:
    if k not in st.session_state:
        st.session_state[k] = ""

# --- AUTOMATYCZNE ZACZYTYWANIE Z PDF ---
st.info("💡 Możesz zautomatyzować wpisywanie danych, wgrywając poniżej surowy raport PDF z Google Analytics. System sam wyciągnie z niego liczby i daty.")
uploaded_ga_pdf = st.file_uploader("Wgraj raport PDF z Google Analytics (Opcjonalnie)", type=["pdf"])

if uploaded_ga_pdf is not None:
    if not st.session_state.get(f'processed_{uploaded_ga_pdf.name}', False):
        try:
            reader = PyPDF2.PdfReader(uploaded_ga_pdf)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + " "
            
            # Zastąpienie nowych linii spacja - ZAPOBIEGA sklejaniu się liczb (np. 14 051 z datą)
            text = re.sub(r'\s+', ' ', text)
            
            # Wyszukiwanie firmy
            firma_match = re.search(r'Produkty i Firmy\s*-\s*([^\s]+)', text, re.IGNORECASE)
            if firma_match: st.session_state.firma = firma_match.group(1).strip()
            
            # Wyszukiwanie daty (odporne na polskie znaki, szuka schematu DD MMM YYYY - DD MMM YYYY)
            date_match = re.search(r'(\d{1,2}\s+[a-zżźćńółęąś]{3,5}\s+\d{4}\s*-\s*\d{1,2}\s+[a-zżźćńółęąś]{3,5}\s+\d{4})', text, re.IGNORECASE)
            if date_match: st.session_state.okres = date_match.group(1).strip()
            
            # --- NIEZAWODNA METODA CZYTANIA WARTOŚCI ---
            def find_val(keyword, txt, is_pct=False):
                # Szukamy wystąpień słowa kluczowego
                for match in re.finditer(keyword, txt, re.IGNORECASE):
                    # Pobieramy 30 znaków znajdujących się BEZPOŚREDNIO za szukanym słowem
                    after_str = txt[match.end():match.end()+30].strip()
                    if is_pct:
                        # Szukamy pierwszej liczby zakończonej procentem (np. 99,52%)
                        m = re.search(r'^([\d,]+%)', after_str)
                        if m: return m.group(1)
                    else:
                        # Szukamy pierwszego ciągu cyfr i spacji (np. 14 051)
                        m = re.search(r'^([\d\s]+)', after_str)
                        if m:
                            val = m.group(1).replace(' ', '')
                            if val.isdigit():
                                # Formatuje np. 152936 na 152 936
                                if len(val) >= 4:
                                    return f"{int(val):,}".replace(",", " ")
                                return val
                return ""

            st.session_state.zdarzenia = find_val(r'Zdarzenia', text)
            st.session_state.odslony = find_val(r'GA4', text) # Koniec z błędami Odsłony vs Odsłony z GA4
            st.session_state.zaangazowanie = find_val(r'Zaanga\S*owanie', text, is_pct=True) # \S* ignoruje błędne kodowanie polskich liter
            
            st.session_state.g_disc_klik = find_val(r'Klikni\S*cia z Discover', text)
            st.session_state.g_disc_odslony = find_val(r'Ods\S*ony z Discover', text)
            
            st.session_state.g_wyniki_klik = find_val(r'Klikni\S*cia z Google', text)
            st.session_state.g_wyniki_odslony = find_val(r'Ods\S*ony z Google', text)

            st.session_state[f'processed_{uploaded_ga_pdf.name}'] = True
            st.rerun() 
        except Exception as e:
            st.error(f"Wystąpił problem podczas odczytywania pliku: {e}")

st.markdown("---")

# Sekcja dla klienta
col_firma1, col_firma2, col_firma3 = st.columns([2, 2, 1.5])
with col_firma1:
    firma = st.text_input("Raport dla firmy:", key="firma")
with col_firma2:
    okres = st.text_input("Okres kampanii:", key="okres")
with col_firma3:
    logo_klienta = st.file_uploader("Wgraj logo klienta (opcjonalnie)", type=["png", "jpg", "jpeg"])

st.markdown("---")
st.subheader("Wprowadź dane, opisy i grafiki dla poszczególnych sekcji")
st.caption("Każda sekcja posiada domyślny, krótki opis, który możesz edytować. Puste pola nie pojawią się w raporcie.")

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
st.markdown("---")

# --- SEKCJA 2 ---
st.markdown("#### 2. Google Discover")
desc_disc = st.text_area("Opis sekcji (Discover):", "Dane obrazują widoczność artykułu i trafność dopasowania treści do czytelników w kanale Google Discover.", height=70)
col2a, col2b = st.columns(2)
g_disc_odslony = col2a.text_input("Google Discover - odsłony:", key="g_disc_odslony")
g_disc_klik = col2b.text_input("Google Discover - kliknięcia:", key="g_disc_klik")
img_disc

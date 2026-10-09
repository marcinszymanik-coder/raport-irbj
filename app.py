import streamlit as st
from fpdf import FPDF
import tempfile
import os
from PIL import Image

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

# Pole dla nazwy firmy (zajmuje główną część)
firma = st.text_input("Raport wygenerowany dla (nazwa firmy):", "Wpisz nazwę firmy...", help="Ta nazwa pojawi się na stronie tytułowej dokumentu.")
st.markdown("---")

st.subheader("Wprowadź dane i grafiki dla poszczególnych sekcji")
st.caption("Pod każdą sekcją możesz opcjonalnie wgrać dedykowane zrzuty ekranu, wykresy lub zdjęcia postów z FB.")

# --- SEKCJA 1 ---
st.markdown("#### 1. Portal Produkty i Firmy")
col1a, col1b, col1c = st.columns(3)
zdarzenia = col1a.text_input("Liczba zdarzeń na portalu:", "46 963")
odslony = col1b.text_input("Odsłony (Portal):", "14 097")
zaangazowanie = col1c.text_input("Zaangażowanie:", "99,53%")
img_portal = st.file_uploader("Dodaj grafiki (Portal Produkty i Firmy)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p1")
st.markdown("---")

# --- SEKCJA 2 ---
st.markdown("#### 2. Google Discover")
col2a, col2b = st.columns(2)
g_disc_odslony = col2a.text_input("Google Discover - odsłony:", "44 733")
g_disc_klik = col2b.text_input("Google Discover - kliknięcia:", "696")
img_disc = st.file_uploader("Dodaj grafiki (Google Discover)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p2")
st.markdown("---")

# --- SEKCJA 3 ---
st.markdown("#### 3. Google Wyniki Wyszukiwania")
col3a, col3b, col3c = st.columns(3)
g_wyniki_odslony = col3a.text_input("Google wyniki - odsłony:", "152 936")
g_wyniki_klik = col3b.text_input("Google wyniki - kliknięcia:", "1418")
g_ai = col3c.text_input("Generatywna AI:", "15 300 od 18 maja")
img_wyniki = st.file_uploader("Dodaj grafiki (Wyniki Wyszukiwania i AI)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p3")
st.markdown("---")

# --- SEKCJA 4 ---
st.markdown("#### 4. Inne źródła (Media Społecznościowe)")
col4a, col4b = st.columns(2)
zajawka = col4a.text_input("Wyświetlenia zajawki o artykule:", "1000")
fb_zasieg = col4b.text_input("Zasięgi na FB:", "ponad 160 000 wyświetleń")
img_inne = st.file_uploader("Dodaj grafiki (Social Media / FB)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p4")

st.markdown("<br>", unsafe_allow_html=True)

# GENERATOR PDF
if st.button("Generuj nowoczesny PDF z grafikami", type="primary", use_container_width=True):
    class ReportPDF(FPDF):
        def header(self):
            # Pomarańczowy pasek dekoracyjny
            self.set_fill_color(255, 160, 0)
            self.rect(0, 0, 210, 6, 'F')
            
            # Wstawienie logo (jeśli plik logo.png istnieje na GitHubie)
            if os.path.exists(logo_png):
                self.image(logo_png, x=15, y=10, w=50)
            
            # Tytuł na dokumencie
            self.set_y(18)
            self.set_font('DejaVu', 'B', 20)
            self.set_text_color(94, 66, 88)
            self.cell(0, 10, "RAPORT Z KAMPANII", border=0, ln=1, align='R')
            
            self.set_font('DejaVu', '', 11)
            self.set_text_color(120, 120, 120)
            self.cell(0, 6, "Zasięgi i statystyki", border=0, ln=1, align='R')
            self.ln(12)

        def footer(self):
            self.set_y(-30)
            # Subtelna linia
            self.set_draw_color(255, 160, 0)
            self.set_line_width(0.5)
            self.line(20, self.get_y(), 190, self.get_y())
            
            self.set_y(-25)
            self.set_font('DejaVu', '', 9)
            self.set_text_color(120, 120, 120)
            stopka = (
                "AVT-Korporacja sp. z o.o. | Leszczynowa 11, 03-197 Warszawa\n"
                "NIP: 5270200177 | KRS: 0000035930"
            )
            self.multi_cell(0, 5, stopka, align='C')
            
    pdf = ReportPDF()
    
    # Wczytywanie czcionek
    if os.path.exists(font_file):
        pdf.add_font('DejaVu', '', font_file, uni=True)
        pdf.add_font('DejaVu', 'B', font_file, uni=True)
        pdf.set_font('DejaVu', '', 12)
    else:
        st.warning("Brak pliku DejaVuSans.ttf. Polskie znaki mogą nie działać prawidłowo.")
        pdf.set_font('Arial', '', 12)
        
    pdf.add_page()
    
    # --- Elegancka ramka z nazwą firmy na pierwszej stronie ---
    pdf.set_fill_color(248, 248, 250)
    pdf.set_draw_color(94, 66, 88)
    pdf.set_line_width(0.5)
    
    pdf.set_font('DejaVu', '', 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 7, "  Przygotowano dla:", border='LTR', ln=1, align='L', fill=True)
    
    pdf.set_font('DejaVu', 'B', 15)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, f"  {firma}", border='LBR', ln=1, align='L', fill=True)
    pdf.ln(10)
    
    # --- Funkcja pomocnicza budująca blok danych i dodająca pod nim obrazki ---
    def add_section_with_images(title, data_dict, uploaded_files):
        # Sprawdzanie czy mamy miejsce na nagłówek tabeli
        if pdf.get_y() > 220:
            pdf.add_page()
            
        # Nagłówek sekcji
        pdf.set_fill_color(94, 66, 88)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 10, f"  {title}", ln=1, fill=True)
        
        # Wiersze z danymi
        pdf.set_fill_color(252, 252, 252)
        pdf.set_draw_color(230, 230, 230)
        pdf.set_line_width(0.2)
        pdf.set_text_color(70, 70, 70)
        
        for label, value in data_dict.items():
            pdf.set_font('DejaVu', '', 11)
            pdf.cell(120, 10, f"   {label}", border='B', fill=True)
            pdf.set_font('DejaVu', 'B', 11)
            pdf.cell(70, 10, f"{value}  ", border='B', ln=1, align='R', fill=True)
        pdf.ln(5)
        
        # Wyświetlanie załączonych obrazków dla tej konkretnej sekcji
        if uploaded_files:
            for file in uploaded_files:
                try:
                    img = Image.open(file)
                    img = img.convert('RGB')
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                        img.save(tmpfile.name, "JPEG")
                        temp_path = tmpfile.name
                    
                    # Automatyczne skalowanie i centrowanie obrazka
                    max_w = 170
                    max_h = 220
                    img_w, img_h = img.size
                    ratio = img_h / img_w
                    
                    calc_w = max_w
                    calc_h = calc_w * ratio
                    
                    # Jeśli obrazek jest bardzo wysoki (np. zrzut całego posta), skaluj do maks. wysokości
                    if calc_h > max_h:
                        calc_h = max_h
                        calc_w = calc_h / ratio
                        
                    # Jeżeli grafika nie zmieści się na tej stronie, wymuś nową
                    if pdf.get_y() + calc_h > 260:
                        pdf.add_page()
                        
                    # Wyśrodkowanie
                    x_pos = (210 - calc_w) / 2
                    pdf.image(temp_path, x=x_pos, w=calc_w, h=calc_h)
                    pdf.ln(8) # Odstęp pod obrazkiem
                except Exception as e:
                    pass
        pdf.ln(5) # Odstęp po całej sekcji

    # --- Uzupełnianie raportu danymi z formularzy ---
    add_section_with_images("Portal Produkty i Firmy", {
        "Liczba zdarzeń na portalu": zdarzenia,
        "Odsłony": odslony,
        "Zaangażowanie": zaangazowanie
    }, img_portal)
    
    add_section_with_images("Google Discover", {
        "Odsłony": g_disc_odslony,
        "Kliknięcia": g_disc_klik
    }, img_disc)
    
    add_section_with_images("Google Wyniki Wyszukiwania", {
        "Odsłony": g_wyniki_odslony,
        "Kliknięcia": g_wyniki_klik,
        "Generatywna AI": g_ai
    }, img_wyniki)
    
    add_section_with_images("Inne źródła (Media Społecznościowe)", {
        "Liczba wyświetleń zajawki o artykule": zajawka,
        "Zasięgi na FB": fb_zasieg
    }, img_inne)

    # --- Generowanie pliku ---
    try:
        pdf_bytes = pdf.output()
        st.success("✨ Raport PDF został wygenerowany pomyślnie!")
        st.download_button(
            label="Pobierz Raport PDF 📥",
            data=bytes(pdf_bytes),
            file_name=f"Raport_{firma.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania: {e}")

import streamlit as st
from fpdf import FPDF
import tempfile
import os
from PIL import Image

# Konfiguracja strony
st.set_page_config(page_title="Generator Raportów - Produkty i Firmy", page_icon="📊", layout="centered")

font_file = "DejaVuSans.ttf"

# Wyświetlanie logo (korzysta z dostarczonego pliku SVG)
if os.path.exists("logo-irbj-new.svg"):
    st.image("logo-irbj-new.svg", width=300)
else:
    st.title("Produkty i Firmy")

st.markdown("### Generator Raportów Zasięgowych")

# Pole dla nazwy firmy
firma = st.text_input("Raport wygenerowany dla (nazwa firmy):", "Wpisz nazwę firmy...")

st.markdown("---")
st.subheader("Wprowadź dane do raportu")

col1, col2 = st.columns(2)

with col1:
    zdarzenia = st.text_input("Liczba zdarzeń na portalu:", "46 963")
    odslony = st.text_input("Odsłony:", "14 097")
    zaangazowanie = st.text_input("Zaangażowanie:", "99,53%")
    zajawka = st.text_input("Wyświetlenia zajawki o artykule:", "1000")
    fb_zasieg = st.text_input("Zasięgi na FB:", "ponad 160 000 wyświetleń")

with col2:
    g_disc_odslony = st.text_input("Google Discover - odsłony:", "44 733")
    g_disc_klik = st.text_input("Google Discover - kliknięcia:", "696")
    g_wyniki_odslony = st.text_input("Google wyniki - odsłony:", "152 936")
    g_wyniki_klik = st.text_input("Google wyniki - kliknięcia:", "1418")
    g_ai = st.text_input("Google wyniki (generatywna AI):", "15 300 od 18 maja")

st.markdown("---")
st.subheader("Grafiki i Wykresy")
uploaded_images = st.file_uploader("Wgraj zrzuty ekranu, posty FB lub wykresy", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if st.button("Generuj nowoczesny PDF", type="primary"):
    class ReportPDF(FPDF):
        def header(self):
            # Pomarańczowy pasek dekoracyjny na samej górze
            self.set_fill_color(255, 160, 0) # Kolor pomarańczowy
            self.rect(0, 0, 210, 6, 'F')
            
            self.set_y(15)
            # Główny tytuł
            self.set_font('DejaVu', 'B', 24)
            self.set_text_color(94, 66, 88) # Kolor ciemnofioletowy (z logo)
            self.cell(0, 12, "RAPORT Z KAMPANII", border=0, ln=1, align='C')
            
            # Podtytuł
            self.set_font('DejaVu', '', 12)
            self.set_text_color(120, 120, 120)
            self.cell(0, 6, "Portal Produkty i Firmy", border=0, ln=1, align='C')
            self.ln(10)

        def footer(self):
            self.set_y(-30)
            # Subtelna linia oddzielająca stopkę
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
    
    # Wczytywanie czcionki
    if os.path.exists(font_file):
        pdf.add_font('DejaVu', '', font_file, uni=True)
        pdf.add_font('DejaVu', 'B', font_file, uni=True)
        pdf.set_font('DejaVu', '', 12)
    else:
        st.warning("Brak pliku DejaVuSans.ttf. Polskie znaki mogą nie działać.")
        pdf.set_font('Arial', '', 12)
        
    pdf.add_page()
    
    # --- Elegancka ramka z nazwą firmy ---
    pdf.set_fill_color(248, 248, 250) # Bardzo jasny szary
    pdf.set_draw_color(94, 66, 88) # Fioletowe obramowanie
    pdf.set_line_width(0.5)
    pdf.set_font('DejaVu', '', 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "  Przygotowano dla:", border='LTR', ln=1, align='L', fill=True)
    
    pdf.set_font('DejaVu', 'B', 16)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 12, f"  {firma}", border='LBR', ln=1, align='L', fill=True)
    pdf.ln(10)
    
    # --- Funkcja pomocnicza do rysowania nowoczesnych tabel ---
    def add_section(title, data_dict):
        # Nagłówek sekcji (Ciemnofioletowe tło, biały tekst)
        pdf.set_fill_color(94, 66, 88)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 10, f"  {title}", ln=1, fill=True)
        
        # Wiersze z danymi (Zebra - jasne tło)
        pdf.set_fill_color(252, 252, 252)
        pdf.set_draw_color(230, 230, 230)
        pdf.set_line_width(0.2)
        pdf.set_text_color(70, 70, 70)
        
        for label, value in data_dict.items():
            pdf.set_font('DejaVu', '', 11)
            pdf.cell(120, 10, f"   {label}", border='B', fill=True)
            pdf.set_font('DejaVu', 'B', 11)
            pdf.cell(70, 10, f"{value}  ", border='B', ln=1, align='R', fill=True)
        pdf.ln(8)
        
    # --- Generowanie bloków danych ---
    add_section("Portal Produkty i Firmy", {
        "Liczba zdarzeń na portalu": zdarzenia,
        "Odsłony": odslony,
        "Zaangażowanie": zaangazowanie
    })
    
    add_section("Google Discover", {
        "Odsłony": g_disc_odslony,
        "Kliknięcia": g_disc_klik
    })
    
    add_section("Google Wyniki Wyszukiwania", {
        "Odsłony": g_wyniki_odslony,
        "Kliknięcia": g_wyniki_klik,
        "Generatywna AI": g_ai
    })
    
    add_section("Inne źródła (Media Społecznościowe)", {
        "Liczba wyświetleń zajawki o artykule": zajawka,
        "Zasięgi na FB": fb_zasieg
    })

    # --- Sekcja ze wgranymi grafikami ---
    if uploaded_images:
        pdf.add_page()
        # Nagłówek dla sekcji z grafikami
        pdf.set_fill_color(94, 66, 88)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('DejaVu', 'B', 14)
        pdf.cell(0, 12, "  Załączone materiały graficzne", ln=1, fill=True)
        pdf.ln(8)
        
        for file in uploaded_images:
            try:
                img = Image.open(file)
                img = img.convert('RGB')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                    img.save(tmpfile.name, "JPEG")
                    temp_path = tmpfile.name
                # Wyśrodkowanie i marginesy dla obrazka
                pdf.image(temp_path, x=20, w=170)
                pdf.ln(10)
            except Exception as e:
                pass

    try:
        pdf_bytes = pdf.output()
        st.success("Nowoczesny Raport PDF został wygenerowany pomyślnie!")
        st.download_button(
            label="Pobierz Raport PDF 📥",
            data=bytes(pdf_bytes),  # Poprawione pod najnowszą wersję fpdf2
            file_name=f"Raport_{firma.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania: {e}")

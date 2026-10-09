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

if st.button("Generuj dokument PDF", type="primary"):
    class ReportPDF(FPDF):
        def header(self):
            self.set_font('DejaVu', 'B', 16)
            self.cell(0, 15, "Raport Kampanii - Produkty i Firmy", border=0, ln=1, align='R')
            self.ln(10)

        def footer(self):
            self.set_y(-30)
            self.set_font('DejaVu', '', 9)
            self.set_text_color(100, 100, 100)
            stopka = (
                "AVT-Korporacja sp. z o.o.\n"
                "Leszczynowa 11, 03-197 Warszawa\n"
                "NIP: 5270200177 | KRS: 0000035930"
            )
            self.multi_cell(0, 5, stopka, align='C')
            
    pdf = ReportPDF()
    
    # Dodawanie czcionki z obsługą polskich znaków
    if os.path.exists(font_file):
        pdf.add_font('DejaVu', '', font_file, uni=True)
        pdf.add_font('DejaVu', 'B', font_file, uni=True)
        pdf.set_font('DejaVu', '', 12)
    else:
        st.warning("Brak pliku DejaVuSans.ttf w repozytorium. Polskie znaki mogą nie działać.")
        pdf.set_font('Arial', '', 12)
        
    pdf.add_page()
    
    pdf.set_font('DejaVu', 'B', 14)
    pdf.cell(0, 10, f"Raport wygenerowany dla: {firma}", ln=1)
    pdf.ln(5)
    
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(0, 8, "Portal Produkty i Firmy:", ln=1)
    pdf.set_font('DejaVu', '', 11)
    pdf.cell(0, 7, f"- Liczba zdarzeń na portalu: {zdarzenia}", ln=1)
    pdf.cell(0, 7, f"- Odsłony: {odslony}", ln=1)
    pdf.cell(0, 7, f"- Zaangażowanie: {zaangazowanie}", ln=1)
    pdf.ln(5)
    
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(0, 8, "Google Discover:", ln=1)
    pdf.set_font('DejaVu', '', 11)
    pdf.cell(0, 7, f"- Odsłony: {g_disc_odslony}", ln=1)
    pdf.cell(0, 7, f"- Kliknięcia: {g_disc_klik}", ln=1)
    pdf.ln(5)
    
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(0, 8, "Google Wyniki Wyszukiwania:", ln=1)
    pdf.set_font('DejaVu', '', 11)
    pdf.cell(0, 7, f"- Odsłony: {g_wyniki_odslony}", ln=1)
    pdf.cell(0, 7, f"- Kliknięcia: {g_wyniki_klik}", ln=1)
    pdf.cell(0, 7, f"- Generatywna AI: {g_ai}", ln=1)
    pdf.ln(5)
    
    pdf.set_font('DejaVu', 'B', 12)
    pdf.cell(0, 8, "Inne źródła (Media Społecznościowe):", ln=1)
    pdf.set_font('DejaVu', '', 11)
    pdf.cell(0, 7, f"- Liczba wyświetleń zajawki o artykule: {zajawka}", ln=1)
    pdf.cell(0, 7, f"- Zasięgi na FB: {fb_zasieg}", ln=1)
    pdf.ln(10)

    if uploaded_images:
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 14)
        pdf.cell(0, 10, "Załączone grafiki z wynikami:", ln=1)
        pdf.ln(5)
        
        for file in uploaded_images:
            try:
                img = Image.open(file)
                img = img.convert('RGB')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                    img.save(tmpfile.name, "JPEG")
                    temp_path = tmpfile.name
                pdf.image(temp_path, x=20, w=170)
                pdf.ln(10)
            except Exception as e:
                pass

    try:
        pdf_bytes = pdf.output()
        st.success("Raport PDF został wygenerowany pomyślnie!")
        st.download_button(
            label="Pobierz Raport PDF 📥",
            data=pdf_bytes,
            file_name=f"Raport_{firma.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania: {e}")

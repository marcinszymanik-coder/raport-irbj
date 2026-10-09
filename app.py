import streamlit as st
from fpdf import FPDF
import tempfile
import os
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

# Sekcja dla klienta
col_firma1, col_firma2, col_firma3 = st.columns([2, 2, 1.5])
with col_firma1:
    firma = st.text_input("Raport dla firmy:", "FAKRO")
with col_firma2:
    okres = st.text_input("Okres kampanii:", "wrzesień 2026")
with col_firma3:
    logo_klienta = st.file_uploader("Wgraj logo klienta (opcjonalnie)", type=["png", "jpg", "jpeg"])

st.markdown("---")
st.subheader("Wprowadź dane, opisy i grafiki dla poszczególnych sekcji")
st.caption("Każda sekcja posiada domyślny opis, który możesz edytować. **Puste pola nie pojawią się w raporcie.**")

# --- SEKCJA 1 ---
st.markdown("#### 1. Portal Produkty i Firmy")
desc_portal = st.text_area("Opis sekcji (Portal):", "Statystyki odzwierciedlają aktywność użytkowników bezpośrednio na portalu Produkty i Firmy. Ukazują one liczbę interakcji (zdarzeń) oraz ogólny poziom zaangażowania w opublikowane treści.", height=70)
col1a, col1b = st.columns(2)
zdarzenia = col1a.text_input("Liczba zdarzeń na portalu:", "46 963")
odslony = col1b.text_input("Odsłony (Portal):", "14 097")

col1c, col1d = st.columns(2)
zaangazowanie = col1c.text_input("Zaangażowanie:", "99,53%")
zajawka = col1d.text_input("Wyświetlenia zajawki o artykule:", "1000")
img_portal = st.file_uploader("Dodaj grafiki (Portal Produkty i Firmy)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p1")
st.markdown("---")

# --- SEKCJA 2 ---
st.markdown("#### 2. Google Discover")
desc_disc = st.text_area("Opis sekcji (Discover):", "Poniższe dane pokazują widoczność artykułu w spersonalizowanym kanale Google Discover na urządzeniach mobilnych. Wysoka liczba kliknięć świadczy o trafnym dopasowaniu treści do zainteresowań czytelników.", height=70)
col2a, col2b = st.columns(2)
g_disc_odslony = col2a.text_input("Google Discover - odsłony:", "44 733")
g_disc_klik = col2b.text_input("Google Discover - kliknięcia:", "696")
img_disc = st.file_uploader("Dodaj grafiki (Google Discover)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p2")
st.markdown("---")

# --- SEKCJA 3 ---
st.markdown("#### 3. Wyniki wyszukiwania w wyszukiwarce Google")
desc_wyniki = st.text_area("Opis sekcji (Wyszukiwarka):", "Prezentowane wyniki obrazują zasięg organiczny materiałów w tradycyjnej wyszukiwarce Google oraz w modułach Generatywnej AI. Odzwierciedlają one, jak często użytkownicy poszukiwali informacji powiązanych z marką.", height=70)
col3a, col3b, col3c = st.columns(3)
g_wyniki_odslony = col3a.text_input("Google wyniki - odsłony:", "152 936")
g_wyniki_klik = col3b.text_input("Google wyniki - kliknięcia:", "1418")
g_ai = col3c.text_input("Generatywna AI:", "15 300 od 18 maja")
img_wyniki = st.file_uploader("Dodaj grafiki (Wyniki Wyszukiwania i AI)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p3")
st.markdown("---")

# --- SEKCJA 4 ---
st.markdown("#### 4. Media społecznościowe")
desc_inne = st.text_area("Opis sekcji (Social Media):", "Zestawienie obejmuje dodatkowy zasięg wygenerowany poprzez media społecznościowe, ze szczególnym uwzględnieniem Facebooka. Pokazuje ono skuteczność komunikacji w przyciąganiu uwagi poza głównym portalem.", height=70)
fb_zasieg = st.text_input("Zasięgi na FB:", "ponad 160 000 wyświetleń")
img_inne = st.file_uploader("Dodaj grafiki (Media społecznościowe) - automatyczny układ 2 kolumn", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p4")

st.markdown("<br>", unsafe_allow_html=True)

# GENERATOR PDF
if st.button("Generuj nowoczesny PDF z grafikami", type="primary", use_container_width=True):
    class ReportPDF(FPDF):
        def header(self):
            self.set_fill_color(255, 160, 0)
            self.rect(0, 0, 210, 6, 'F')
            
            if os.path.exists(logo_png):
                self.image(logo_png, x=15, y=10, w=50)
            
            self.ln(20)

        def footer(self):
            self.set_y(-30)
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
    
    if os.path.exists(font_file):
        pdf.add_font('DejaVu', '', font_file, uni=True)
        pdf.add_font('DejaVu', 'B', font_file, uni=True)
        pdf.set_font('DejaVu', '', 12)
    else:
        st.warning("Brak pliku DejaVuSans.ttf. Polskie znaki mogą nie działać prawidłowo.")
        pdf.set_font('Arial', '', 12)
        
    pdf.add_page()
    
    # --- NAGŁÓWEK RAPORTU ---
    pdf.set_y(35) 
    
    pdf.set_font('DejaVu', 'B', 20)
    pdf.set_text_color(94, 66, 88)
    pdf.cell(120, 10, f"Raport kampanii dla {firma}", ln=1)
    
    if okres:
        pdf.set_font('DejaVu', '', 12)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(120, 8, f"Okres: {okres}", ln=1)
        
    if logo_klienta:
        try:
            img = Image.open(logo_klienta)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                img.save(tmpfile.name, "PNG")
                client_logo_path = tmpfile.name
            
            max_w, max_h = 50, 18
            img_w, img_h = img.size
            ratio = img_h / img_w
            
            calc_w = max_w
            calc_h = calc_w * ratio
            
            if calc_h > max_h:
                calc_h = max_h
                calc_w = calc_h / ratio
                
            logo_x = 195 - calc_w
            pdf.image(client_logo_path, x=logo_x, y=35, w=calc_w, h=calc_h)
        except Exception as e:
            pass

    pdf.ln(12) 
    
    # --- Funkcja budująca blok danych i dodająca pod nim obrazki ---
    def add_section_with_images(title, description, data_dict, uploaded_files, two_columns=False):
        # Filtrowanie pustych danych
        filtered_data = {label: value for label, value in data_dict.items() if str(value).strip() != ""}

        if pdf.get_y() > 220:
            pdf.add_page()
            
        # Nagłówek sekcji
        pdf.set_fill_color(94, 66, 88)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 10, f"  {title}", ln=1, fill=True)
        
        # Opis sekcji
        if description.strip():
            pdf.set_font('DejaVu', '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.set_x(12)
            pdf.multi_cell(186, 6, description.strip(), align='L')
            pdf.ln(2)
        
        # Wiersze z danymi
        if filtered_data:
            pdf.set_fill_color(252, 252, 252)
            pdf.set_draw_color(230, 230, 230)
            pdf.set_line_width(0.2)
            pdf.set_text_color(70, 70, 70)
            
            for label, value in filtered_data.items():
                pdf.set_font('DejaVu', '', 11)
                pdf.cell(120, 10, f"   {label}", border='B', fill=True)
                pdf.set_font('DejaVu', 'B', 11)
                pdf.cell(70, 10, f"{value}  ", border='B', ln=1, align='R', fill=True)
            pdf.ln(5)
        
        # Wyświetlanie załączonych obrazków
        if uploaded_files:
            if not two_columns:
                # Klasyczny układ - jeden duży obrazek na wiersz
                for file in uploaded_files:
                    try:
                        img = Image.open(file)
                        img = img.convert('RGB')
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                            img.save(tmpfile.name, "JPEG")
                            temp_path = tmpfile.name
                        
                        max_w, max_h = 170, 220
                        img_w, img_h = img.size
                        ratio = img_h / img_w
                        
                        calc_w = max_w
                        calc_h = calc_w * ratio
                        
                        if calc_h > max_h:
                            calc_h = max_h
                            calc_w = calc_h / ratio
                            
                        if pdf.get_y() + calc_h > 260:
                            pdf.add_page()
                            
                        x_pos = (210 - calc_w) / 2
                        pdf.image(temp_path, x=x_pos, w=calc_w, h=calc_h)
                        pdf.set_y(pdf.get_y() + calc_h + 8)
                    except Exception as e:
                        pass
            else:
                # Układ dwukolumnowy
                for i in range(0, len(uploaded_files), 2):
                    try:
                        file1 = uploaded_files[i]
                        file2 = uploaded_files[i+1] if i+1 < len(uploaded_files) else None
                        
                        def process_img(f):
                            img = Image.open(f).convert('RGB')
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                                img.save(tmpfile.name, "JPEG")
                                return tmpfile.name, img.size
                        
                        path1, (w1, h1) = process_img(file1)
                        
                        max_w_col = 80
                        max_h_col = 150
                        
                        calc_w1 = max_w_col
                        calc_h1 = calc_w1 * (h1 / w1)
                        if calc_h1 > max_h_col:
                            calc_h1 = max_h_col
                            calc_w1 = calc_h1 / (h1 / w1)
                            
                        calc_h2 = 0
                        if file2:
                            path2, (w2, h2) = process_img(file2)
                            calc_w2 = max_w_col
                            calc_h2 = calc_w2 * (h2 / w2)
                            if calc_h2 > max_h_col:
                                calc_h2 = max_h_col
                                calc_w2 = calc_h2 / (h2 / w2)
                        
                        row_h = max(calc_h1, calc_h2)
                        
                        if pdf.get_y() + row_h > 260:
                            pdf.add_page()
                            
                        current_y = pdf.get_y()
                        
                        # Lewa kolumna (środek lewej połowy strony to 52.5)
                        x_pos1 = 52.5 - (calc_w1 / 2)
                        pdf.image(path1, x=x_pos1, y=current_y, w=calc_w1, h=calc_h1)
                        
                        # Prawa kolumna (środek prawej połowy strony to 157.5)
                        if file2:
                            x_pos2 = 157.5 - (calc_w2 / 2)
                            pdf.image(path2, x=x_pos2, y=current_y, w=calc_w2, h=calc_h2)
                            
                        pdf.set_y(current_y + row_h + 8)
                    except Exception as e:
                        pass
        pdf.ln(5)

    add_section_with_images("Portal Produkty i Firmy", desc_portal, {
        "Liczba zdarzeń na portalu": zdarzenia,
        "Odsłony": odslony,
        "Zaangażowanie": zaangazowanie,
        "Liczba wyświetleń zajawki o artykule": zajawka
    }, img_portal)
    
    add_section_with_images("Google Discover", desc_disc, {
        "Odsłony": g_disc_odslony,
        "Kliknięcia": g_disc_klik
    }, img_disc)
    
    add_section_with_images("Wyniki wyszukiwania w wyszukiwarce Google", desc_wyniki, {
        "Odsłony": g_wyniki_odslony,
        "Kliknięcia": g_wyniki_klik,
        "Generatywna AI": g_ai
    }, img_wyniki)
    
    # Przełącznik two_columns=True włączony dla ostatniej sekcji
    add_section_with_images("Media społecznościowe", desc_inne, {
        "Zasięgi na FB": fb_zasieg
    }, img_inne, two_columns=True)

    try:
        pdf_bytes = bytes(pdf.output())
        st.success("✨ Raport PDF został wygenerowany pomyślnie!")
        
        st.markdown("### Podgląd raportu")
        pdf_viewer(input=pdf_bytes, width=700)

        st.markdown("<br>", unsafe_allow_html=True)
        
        st.download_button(
            label="Pobierz Raport PDF 📥",
            data=pdf_bytes,
            file_name=f"Raport_{firma.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania: {e}")

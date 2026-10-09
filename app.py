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

# Inicjalizacja zmiennych sesyjnych dla automatycznego uzupełniania pól
if 'firma' not in st.session_state: st.session_state.firma = ""
if 'okres' not in st.session_state: st.session_state.okres = ""
if 'zdarzenia' not in st.session_state: st.session_state.zdarzenia = ""
if 'odslony' not in st.session_state: st.session_state.odslony = ""
if 'zaangazowanie' not in st.session_state: st.session_state.zaangazowanie = ""
if 'g_disc_odslony' not in st.session_state: st.session_state.g_disc_odslony = ""
if 'g_disc_klik' not in st.session_state: st.session_state.g_disc_klik = ""
if 'g_wyniki_odslony' not in st.session_state: st.session_state.g_wyniki_odslony = ""
if 'g_wyniki_klik' not in st.session_state: st.session_state.g_wyniki_klik = ""

# --- AUTOMATYCZNE ZACZYTYWANIE Z PDF ---
st.info("💡 Możesz zautomatyzować wpisywanie danych, wgrywając poniżej surowy raport PDF z Google Analytics. System sam wyciągnie z niego liczby i daty.")
uploaded_ga_pdf = st.file_uploader("Wgraj raport PDF z Google Analytics (Opcjonalnie)", type=["pdf"])

if uploaded_ga_pdf is not None:
    # Zabezpieczenie przed ciągłym przeładowywaniem tego samego pliku
    if not st.session_state.get(f'processed_{uploaded_ga_pdf.name}', False):
        try:
            reader = PyPDF2.PdfReader(uploaded_ga_pdf)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            # Ekstrakcja danych przy pomocy wyrażeń regularnych
            firma_match = re.search(r'Raport pakiet Produkty i Firmy\s*-\s*(.*)', text)
            if firma_match: st.session_state.firma = firma_match.group(1).strip()
            
            date_match = re.search(r'(\d{1,2}\s+[a-zżźćńółęąś]+\s+\d{4}\s*-\s*\d{1,2}\s+[a-zżźćńółęąś]+\s+\d{4})', text, re.IGNORECASE)
            if date_match: st.session_state.okres = date_match.group(1).strip()
            
            def extract_val(pattern):
                match = re.search(pattern, text)
                return match.group(1).strip() if match else None

            val = extract_val(r'Zdarzenia\s*([\d\s]+)')
            if val: st.session_state.zdarzenia = val
            
            val = extract_val(r'Odsłony z GA4\s*([\d\s]+)')
            if val: st.session_state.odslony = val
            
            val = extract_val(r'Zaangażowanie\s*([\d,%]+)')
            if val: st.session_state.zaangazowanie = val
            
            val = extract_val(r'Kliknięcia z Discover\s*([\d\s]+)')
            if val: st.session_state.g_disc_klik = val
            
            val = extract_val(r'Odsłony z Discover\s*([\d\s]+)')
            if val: st.session_state.g_disc_odslony = val
            
            val = extract_val(r'Kliknięcia z Google\s*([\d\s]+)')
            if val: st.session_state.g_wyniki_klik = val
            
            val = extract_val(r'Odsłony z Google\s*([\d\s]+)')
            if val: st.session_state.g_wyniki_odslony = val

            st.session_state[f'processed_{uploaded_ga_pdf.name}'] = True
            st.rerun() # Odśwież aplikację, aby pola formularza pobrały wczytane zmienne
        except Exception as e:
            st.error(f"Wystąpił problem podczas odczytywania pliku: {e}")

st.markdown("---")

# Sekcja dla klienta (korzysta z kluczy session_state do wyświetlania wczytanych danych)
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
zajawka = col1d.text_input("Wyświetlenia zajawki o artykule:", value="1000") # To pole nie zaczytuje się z PDF, zostaje domyślne
img_portal = st.file_uploader("Dodaj grafiki (Portal Produkty i Firmy)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p1")
st.markdown("---")

# --- SEKCJA 2 ---
st.markdown("#### 2. Google Discover")
desc_disc = st.text_area("Opis sekcji (Discover):", "Dane obrazują widoczność artykułu i trafność dopasowania treści do czytelników w kanale Google Discover.", height=70)
col2a, col2b = st.columns(2)
g_disc_odslony = col2a.text_input("Google Discover - odsłony:", key="g_disc_odslony")
g_disc_klik = col2b.text_input("Google Discover - kliknięcia:", key="g_disc_klik")
img_disc = st.file_uploader("Dodaj grafiki (Google Discover)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p2")
st.markdown("---")

# --- SEKCJA 3 ---
st.markdown("#### 3. Wyniki wyszukiwania w wyszukiwarce Google")
desc_wyniki = st.text_area("Opis sekcji (Wyszukiwarka):", "Wyniki przedstawiają zasięg organiczny w tradycyjnej wyszukiwarce Google oraz w modułach Generatywnej AI.", height=70)
col3a, col3b, col3c = st.columns(3)
g_wyniki_odslony = col3a.text_input("Google wyniki - odsłony:", key="g_wyniki_odslony")
g_wyniki_klik = col3b.text_input("Google wyniki - kliknięcia:", key="g_wyniki_klik")
g_ai = col3c.text_input("Generatywna AI:", value="15 300 od 18 maja") # To pole nie zaczytuje się z PDF
img_wyniki = st.file_uploader("Dodaj grafiki (Wyniki Wyszukiwania i AI)", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="p3")
st.markdown("---")

# --- SEKCJA 4 ---
st.markdown("#### 4. Media społecznościowe")
desc_inne = st.text_area("Opis sekcji (Social Media):", "Zestawienie obejmuje zasięg wygenerowany poprzez media społecznościowe (głównie Facebook), wspierający główną komunikację.", height=70)
fb_zasieg = st.text_input("Zasięgi na FB:", value="ponad 160 000 wyświetleń") # To pole nie zaczytuje się z PDF
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
            
            self.set_y(-15)
            self.set_font('DejaVu', '', 8)
            self.cell(0, 5, f"Strona {self.page_no()}/{{nb}}", align='R')
            
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=35) 
    
    if os.path.exists(font_file):
        pdf.add_font('DejaVu', '', font_file, uni=True)
        pdf.add_font('DejaVu', 'B', font_file, uni=True)
        pdf.set_font('DejaVu', '', 12)
    else:
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
    
    def add_section_with_images(title, description, data_dict, uploaded_files, two_columns=False):
        filtered_data = {label: value for label, value in data_dict.items() if str(value).strip() != ""}

        if pdf.get_y() > 230:
            pdf.add_page()
            
        pdf.set_fill_color(94, 66, 88)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 10, f"  {title}", ln=1, fill=True)
        
        if description.strip():
            pdf.ln(3) 
            pdf.set_font('DejaVu', '', 10)
            pdf.set_text_color(100, 100, 100)
            pdf.set_x(12)
            pdf.multi_cell(186, 5, description.strip(), align='L')
            pdf.ln(4) 
        else:
             pdf.ln(2)
        
        if filtered_data:
            height_needed = len(filtered_data) * 10
            if pdf.get_y() + height_needed > 260:
                 pdf.add_page()
                 
            pdf.set_fill_color(252, 252, 252)
            pdf.set_draw_color(230, 230, 230)
            pdf.set_line_width(0.2)
            pdf.set_text_color(70, 70, 70)
            
            for label, value in filtered_data.items():
                pdf.set_font('DejaVu', '', 11)
                pdf.cell(120, 10, f"   {label}", border='B', fill=True)
                pdf.set_font('DejaVu', 'B', 11)
                pdf.cell(70, 10, f"{value}  ", border='B', ln=1, align='R', fill=True)
            pdf.ln(6)
        
        if uploaded_files:
            if not two_columns:
                for file in uploaded_files:
                    try:
                        img = Image.open(file)
                        img = img.convert('RGB')
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                            img.save(tmpfile.name, "JPEG")
                            temp_path = tmpfile.name
                        
                        max_w, max_h = 170, 200 
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
                        
                        x_pos1 = 52.5 - (calc_w1 / 2)
                        pdf.image(path1, x=x_pos1, y=current_y, w=calc_w1, h=calc_h1)
                        
                        if file2:
                            x_pos2 = 157.5 - (calc_w2 / 2)
                            pdf.image(path2, x=x_pos2, y=current_y, w=calc_w2, h=calc_h2)
                            
                        pdf.set_y(current_y + row_h + 8)
                    except Exception as e:
                        pass
        pdf.ln(6) 

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

import streamlit as st
from google import genai
from google.genai import types
import pypdf
from streamlit_calendar import calendar
from datetime import datetime
import re
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 1. Sayfa Ayarları
st.set_page_config(page_title="EduAI Pro | Akıllı Akademik Asistan", page_icon="🎓", layout="wide")

# 🎨 MODERN DASHBOARD CSS
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%); }
    h1 { color: #1e3a8a !important; font-family: 'Poppins', sans-serif; font-weight: 700; }
    h2, h3 { color: #0f766e !important; font-family: 'Poppins', sans-serif; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; box-shadow: 2px 0px 15px rgba(0,0,0,0.05); border-right: 1px solid #e2e8f0; }
    .edu-card { background-color: #ffffff; padding: 24px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border-left: 5px solid #3b82f6; margin-bottom: 15px; }
    .yt-button { display: inline-flex; align-items: center; justify-content: center; background-color: #ff0000; color: white !important; padding: 12px 24px; font-weight: bold; text-decoration: none; border-radius: 8px; margin: 8px 0; }
    .yt-button:hover { background-color: #cc0000; }
    </style>
""", unsafe_allow_html=True)

# 2. Sol Menü (Navigasyon)
st.sidebar.markdown("<h2 style='text-align: center; color: #3b82f6;'>🚀 EduAI Panel</h2>", unsafe_allow_html=True)
sayfa = st.sidebar.radio("Gitmek İstediğiniz Sayfa:", ["📚 Yapay Zekâ Asistanı", "📅 Ajanda & Takvim"])

st.sidebar.divider()
st.sidebar.markdown("### 🔑 API Ayarları")
api_key = st.sidebar.text_input("Gemini API Key Giriniz:", type="password")

# Session State Yönetimi (Revizeler ve verilerin hafızada kalması için)
if "events" not in st.session_state: st.session_state["events"] = []
if "ai_results" not in st.session_state: st.session_state["ai_results"] = None
if "full_raw_output" not in st.session_state: st.session_state["full_raw_output"] = ""
if "current_material" not in st.session_state: st.session_state["current_material"] = ""

# SİSTEM TALİMATI
SYSTEM_INSTRUCTION = """
Sen uzman bir Akademik Asistan ve AI Eğitmensin. 
Sana verilen öğrenme materyallerini veya revize isteklerini işleyip, MUTLAKA aşağıdaki yapıda, Türkçe ve temiz bir Markdown formatında yanıt vermelisin.

Her ana bölümü tam olarak belirtilen bu başlıklarla başlat:
### [KONU_ANLATIMI_BASLANGIC]
### [OZET_BASLANGIC]
### [SORULAR_BASLANGIC]
### [YOUTUBE_BASLANGIC]
### [CEVAP_ANAHTARI_BASLANGIC]

İçerik kuralları:
- Konu anlatımında detaylı açıklamalar ve pratik örnekler ver.
- Özet kısmında en önemli noktaları maddeler halinde yaz.
- Sorular kısmında en az 5 test, 3 açık uçlu soru hazırla.
- YouTube kısmında önerileri tam olarak şu formatta yaz: [YT_SUGGESTION: Anahtar Kelime]
- Cevap anahtarına çözümleri ekle.
"""

# PDF Okuma ve Düzenleme Yardımcı Fonksiyonları
def extract_text_from_pdf(uploaded_file):
    pdf_reader = pypdf.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text_content = page.extract_text()
        if text_content: text += text_content + "\n"
    return text

def format_youtube_links(text):
    pattern = r'\[YT_SUGGESTION:\s*(.*?)\]'
    def replace_with_link(match):
        keyword = match.group(1).strip()
        search_url = f"https://www.youtube.com/results?search_query={keyword.replace(' ', '+')}"
        return f'<a href="{search_url}" target="_blank" class="yt-button">📺 YouTube\'da Ara: {keyword}</a>'
    return re.sub(pattern, replace_with_link, text)

def parse_ai_response(text):
    sections = {"konu": "İçerik üretilemedi.", "ozet": "Özet üretilemedi.", "sorular": "Sorular üretilemedi.", "youtube": "Öneri bulunamadı.", "cevaplar": "Cevap anahtarı bulunamadı."}
    try:
        konu_match = re.search(r'\[KONU_ANLATIMI_BASLANGIC\](.*?)### \[OZET_BASLANGIC\]', text, re.DOTALL)
        ozet_match = re.search(r'\[OZET_BASLANGIC\](.*?)### \[SORULAR_BASLANGIC\]', text, re.DOTALL)
        sorular_match = re.search(r'\[SORULAR_BASLANGIC\](.*?)### \[YOUTUBE_BASLANGIC\]', text, re.DOTALL)
        youtube_match = re.search(r'\[YOUTUBE_BASLANGIC\](.*?)### \[CEVAP_ANAHTARI_BASLANGIC\]', text, re.DOTALL)
        cevap_match = re.search(r'\[CEVAP_ANAHTARI_BASLANGIC\](.*)', text, re.DOTALL)
        
        if konu_match: sections["konu"] = konu_match.group(1).strip()
        if ozet_match: sections["ozet"] = ozet_match.group(1).strip()
        if sorular_match: sections["sorular"] = sorular_match.group(1).strip()
        if youtube_match: sections["youtube"] = format_youtube_links(youtube_match.group(1).strip())
        if cevap_match: sections["cevaplar"] = cevap_match.group(1).strip()
    except: pass
    return sections

# 📄 TÜRKÇE KARAKTER UYUMLU ŞIK PDF ÜRETME MOTORU
def generate_pdf(raw_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Markdown temizleme (PDF içinde ham etiketler çirkin durmasın diye)
    clean_text = re.sub(r'### \[(.*?)\]', '', raw_text)
    clean_text = clean_text.replace("**", "").replace("*", "")
    
    story = []
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, spaceAfter=15, textColor='#1e3a8a')
    body_style = ParagraphStyle('BodyStyle', parent=styles['BodyText'], fontSize=11, leading=16, spaceAfter=10)
    
    story.append(Paragraph("EduAI Akademik Çalışma Raporu", title_style))
    story.append(Spacer(1, 10))
    
    # Satır satır PDF'e ekleme
    for line in clean_text.split('\n'):
        if line.strip():
            story.append(Paragraph(line, body_style))
        else:
            story.append(Spacer(1, 6))
            
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# SAYFA 1: YAPAY ZEKÂ ASİSTANI
# ==========================================
if sayfa == "📚 Yapay Zekâ Asistanı":
    st.title("📚 Yapay Zekâ Destekli Ders Asistanı")
    st.markdown("<p style='color: #64748b;'>Materyallerinizi yükleyin, bölümlere ayrılmış akıllı panelleriniz hazırlansın.</p>", unsafe_allow_html=True)
    st.divider()

    if not api_key:
        st.info("Lütfen sol menüden Gemini API anahtarınızı girin.", icon="ℹ️")
    else:
        client = genai.Client(api_key=api_key)

        # ÜST SEKMELER (YAN YANA GİRİŞ)
        input_tab1, input_tab2 = st.tabs(["📄 PDF Yükleme Alanı", "✍️ Düz Metin Yapıştırma Alanı"])
        
        with input_tab1:
            uploaded_file = st.file_uploader("Ders notunu veya makaleyi bırakın (PDF)", type=["pdf"])
            if uploaded_file is not None:
                with st.spinner("PDF okunuyor..."):
                    st.session_state["current_material"] = extract_text_from_pdf(uploaded_file)
                st.success("PDF okundu, işlenmeye hazır!")

        with input_tab2:
            user_text = st.text_area("Notları buraya girin:", height=100)
            if user_text: st.session_state["current_material"] = user_text

        if st.session_state["current_material"]:
            if st.button("✨ Materyali Analiz Et ve Panelleri Oluştur", type="primary"):
                with st.spinner("Gemini 2.5-flash ilk analizi yapıyor..."):
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=st.session_state["current_material"],
                        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.3)
                    )
                    st.session_state["full_raw_output"] = response.text
                    st.session_state["ai_results"] = parse_ai_response(response.text)

        # ALT SEKMELER (SONUÇ VE İNTERAKTİF REVİZE ALANI)
        if st.session_state["ai_results"] is not None:
            st.divider()
            st.markdown("## 📊 Çalışma Masanız")
            
            res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs(["📖 Konu Anlatımı", "📝 Özet Bilgiler", "❓ Sınav Soruları", "📺 Görüntülü Öğrenme"])
            results = st.session_state["ai_results"]
            
            with res_tab1:
                st.markdown(f'<div class="edu-card"><h3>📖 Detaylı Konu Anlatımı</h3><br>{results["konu"]}</div>', unsafe_allow_html=True)
            with res_tab2:
                st.markdown(f'<div class="edu-card"><h3>📝 Hap Özet Bilgiler</h3><br>{results["ozet"]}</div>', unsafe_allow_html=True)
            with res_tab3:
                st.markdown(f'<div class="edu-card"><h3>❓ Sınav Hazırlık Soruları</h3><br>{results["sorular"]}</div>', unsafe_allow_html=True)
                with st.expander("🔑 Cevap Anahtarını Göster / Gizle"):
                    st.markdown(results["cevaplar"])
            with res_tab4:
                st.markdown('### 📺 Önerilen Eğitim Videoları')
                st.markdown(results["youtube"], unsafe_allow_html=True)
            
            # ✍️ YAPAY ZEKÂYA YORUM / REVİZE EKLEME ALANI
            st.markdown("### 🔄 Notları Özelleştir veya Yorum Yap")
            revize_istegi = st.text_input("Notların değiştirilmesini istediğiniz kısımlarını veya ekstra yorumunuzu buraya yazın:", placeholder="Örn: Konu anlatımına pratik bir kod örneği ekle veya özeti daha kısa yap.")
            
            if st.button("💬 Notları Yorumuma Göre Güncelle"):
                if revize_istegi:
                    with st.spinner("Gemini dökümanı yorumunuza göre yeniden şekillendiriyor..."):
                        # Mevcut dökümanı ve kullanıcının ekstra yorumunu modele besliyoruz
                        revize_prompt = f"Mevcut Döküman:\n{st.session_state['full_raw_output']}\n\nKullanıcı Yorumu/İsteği:\n{revize_istegi}\n\nLütfen mevcut dökümanı bu doğrultuda güncelleyerek bana aynı formatta teslim et."
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=revize_prompt,
                            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.3)
                        )
                        st.session_state["full_raw_output"] = response.text
                        st.session_state["ai_results"] = parse_ai_response(response.text)
                        st.success("Notlar yorumunuza göre başarıyla güncellendi!")
                        st.rerun()

            st.divider()
            # 📄 GELİŞMİŞ ÖZELLİK: GERÇEK PDF OLARAK İNDİRME BUTONU
            pdf_data = generate_pdf(st.session_state["full_raw_output"])
            st.download_button(
                label="📥 Tüm Çalışma Notlarını PDF Olarak İndir",
                data=pdf_data,
                file_name="EduAI_Akademik_Notlar.pdf",
                mime="application/pdf"
            )

# ==========================================
# SAYFA 2: AJANDA & TAKVİM
# ==========================================
elif sayfa == "📅 Ajanda & Takvim":
    st.title("📅 Akademik Ajanda")
    st.divider()
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### ➕ Yeni Görev Ekle")
        with st.form("etkinlik_formu", clear_on_submit=True):
            görev_adi = st.text_input("Etkinlik / Görev Adı:")
            tarih = st.date_input("Tarih Seçin:")
            saat_baslangic = st.time_input("Başlangıç Saati:", value=datetime.strptime("09:00", "%H:%M").time())
            saat_bitis = st.time_input("Bitiş Saati:", value=datetime.strptime("10:00", "%H:%M").time())
            renk = st.color_picker("Renk Seçin:", "#3b82f6")
            submit_button = st.form_submit_button(label="Ajandaya Kaydet")
            
            if submit_button and görev_adi:
                st.session_state["events"].append({
                    "title": görev_adi, "start": f"{tarih}T{saat_baslangic}", "end": f"{tarih}T{saat_bitis}", "color": renk
                })
                st.success(f"'{görev_adi}' ajandaya eklendi!")
                st.rerun()
    with col2:
        st.markdown("### 📆 Programım")
        calendar(events=st.session_state["events"], options={"initialView": "dayGridMonth"})
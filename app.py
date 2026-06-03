import streamlit as st
from google import genai
from google.genai import types
import pypdf
from streamlit_calendar import calendar
from datetime import datetime
import re
import io
import json
import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. Sayfa Ayarları
st.set_page_config(page_title="ExamAI | Akıllı Akademik Asistan ve Planlayıcı", page_icon="🎓", layout="wide")

# 🧠 SÜREKLİ GÜNCELLENEN MOTİVASYON SÖZLERİ HAVUZU
MOTIVASYON_SOZLERI = [
    "🚀 'Derine indikçe zorlaşacak, ama unutma: En iyi yazılımlar en zorlu gecelerde derlenir!'",
    "💻 'Kodundaki bug'ları da, hayatındaki engelleri de tek tek çözeceksin. Çalışmaya devam, Memik Kızık seninle!'",
    "🔥 'Bugün attığın her adımla yarınki geleceğini inşa ediyorsun. Odaklan ve arkana bakma!'",
    "🎓 'Vizeler, finaller geçecek; geriye sadece senin pes etmediğin o efsane geceler kalacak!'",
    "⚡ 'Sistem hatası vermediğin sürece yenilmiş sayılmazsın. Derle, çalıştır, başar!'",
    "🌟 'Büyük işler, küçük adımların istikrarıyla gelir. Kulaklığı tak, dünyayı sessize al ve odaklan!'"
]

# Session State Başlatma (Giriş kontrolü için)
if "api_key_entered" not in st.session_state:
    st.session_state["api_key_entered"] = ""

# 🎨 GECE DOSTU (DIM/DARK MODE) VE LÜKS SaaS TASARIMI İÇİN ÖZEL CSS
st.markdown("""
    <style>
    .stApp { background: #1e293b; color: #f8fafc !important; }
    h1 { color: #38bdf8 !important; font-family: 'Poppins', sans-serif; font-weight: 800; text-shadow: 0px 4px 10px rgba(56, 189, 248, 0.2); }
    h2, h3 { color: #2dd4bf !important; font-family: 'Poppins', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #334155; }
    [data-testid="stSidebar"] * { color: #94a3b8 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #0f172a; padding: 8px; border-radius: 12px; }
    .stTabs [data-baseweb="tab"] { color: #94a3b8 !important; background-color: transparent; border-radius: 8px; padding: 10px 20px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #38bdf8 !important; color: #0f172a !important; }
    
    /* Premium Kart Yapısı */
    .edu-card { background-color: #0f172a; padding: 28px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); border: 1px solid #1e293b; border-left: 6px solid #2dd4bf; margin-bottom: 20px; color: #e2e8f0; line-height: 1.7; }
    
    /* Motivasyon Banner Stili */
    .motivation-banner { background: linear-gradient(90deg, #1e1b4b 0%, #311042 100%); padding: 15px; border-radius: 12px; border: 1px dashed #38bdf8; text-align: center; margin-bottom: 20px; font-style: italic; }
    
    /* Yenilikçi Analitik Metrik Kartları */
    .metric-container { display: flex; gap: 15px; margin-bottom: 25px; }
    .metric-box { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    .metric-val { font-size: 24px; font-weight: bold; color: #38bdf8; }
    .metric-lbl { font-size: 12px; color: #94a3b8; margin-top: 5px; }
    
    /* YouTube Buton Tasarımı */
    .yt-button { display: inline-flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%); color: white !important; padding: 12px 26px; font-weight: bold; text-decoration: none; border-radius: 10px; margin: 8px 0; box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3); }
    input, textarea, select { background-color: #0f172a !important; color: #f8fafc !important; border: 1px solid #334155 !important; border-radius: 8px !important; }
    
    /* Geliştirici İmzası */
    .dev-signature { position: fixed; bottom: 20px; right: 20px; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1px solid #38bdf8; padding: 10px 18px; border-radius: 30px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); z-index: 9999; display: flex; align-items: center; gap: 8px; text-decoration: none !important; transition: all 0.3s ease; }
    .dev-signature:hover { transform: translateY(-5px) scale(1.05); box-shadow: 0 15px 25px rgba(56, 189, 248, 0.4); border-color: #2dd4bf; }
    .dev-signature span { color: #94a3b8; font-size: 12px; }
    .dev-signature strong { color: #38bdf8; font-weight: 700; font-size: 14px; }
    
    /* Kilit Ekranı Özel Link Butonu */
    .key-button { display: inline-block; background: #2dd4bf; color: #0f172a !important; font-weight: bold; padding: 10px 20px; border-radius: 8px; text-decoration: none; margin-top: 10px; transition: all 0.3s ease; }
    .key-button:hover { background: #38bdf8; transform: translateY(-2px); }
    </style>
""", unsafe_allow_html=True)

# 🚀 FLOATING SIGNATURE (Geliştirici İmzası)
st.markdown("""
    <a href="https://github.com/memikkizik" target="_blank" class="dev-signature">
        <span>👨‍💻 Geliştirici:</span>
        <strong>Memik Kızık</strong>
    </a>
""", unsafe_allow_html=True)

# Session State Yönetimi
if "events" not in st.session_state: 
    st.session_state["events"] = [
        {"id": "1", "title": "📚 Örnek: Nesne Yönelimli Programlama Vizesi", "start": datetime.now().strftime("%Y-%m-%dT09:00:00"), "end": datetime.now().strftime("%Y-%m-%dT11:00:00"), "color": "#ef4444", "extendedProps": {"category": "Sınav", "status": "Devam Ediyor"}}
    ]
if "ai_results" not in st.session_state: st.session_state["ai_results"] = None
if "full_raw_output" not in st.session_state: st.session_state["full_raw_output"] = ""
if "current_material" not in st.session_state: st.session_state["current_material"] = ""

# AI YARDIMCI PROMPTLARI
SYSTEM_INSTRUCTION = """
Sen uzman bir Akademik Asistan ve AI Eğitmensin. Sana verilen öğrenme materyallerini işleyip, MUTLAKA aşağıdaki yapıda, Türkçe ve temiz bir Markdown formatında yanıt vermelisin.
### [KONU_ANLATIMI_BASLANGIC] ... ### [OZET_BASLANGIC] ... ### [SORULAR_BASLANGIC] ... ### [YOUTUBE_BASLANGIC] ... ### [CEVAP_ANAHTARI_BASLANGIC]
"""

NLP_CALENDAR_INSTRUCTION = 'Sen bir metinden takvim etkinlik verisi ayıklayan akıllı bir botsun. Kullanıcı sana doğal dille bir randevu, sınav veya ödev tarihi yazacak. Sen bu metni analiz edip SADECE aşağıdaki JSON formatında çıktı vereceksin: { "title": "emoji ve baslik", "start": "ISO_DATE", "end": "ISO_DATE", "category": "Sinav/Odev/Proje/Kisisel" }'

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

def generate_pdf(raw_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    clean_text = re.sub(r'### \[(.*?)\]', '', raw_text).replace("**", "").replace("*", "")
    story = []
    title_style = ParagraphStyle('TitleStyle', fontSize=18, spaceAfter=15, textColor='#1e3a8a')
    body_style = ParagraphStyle('BodyStyle', fontSize=11, leading=16, spaceAfter=10)
    story.append(Paragraph("ExamAI Akademik Çalışma Notları", title_style))
    for line in clean_text.split('\n'):
        if line.strip(): story.append(Paragraph(line, body_style))
        else: story.append(Spacer(1, 6))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# 🔐 GÜVENLİK KONTROLÜ & MERKEZİ GİRİŞ EKRANI
# ==========================================
if not st.session_state["api_key_entered"]:
    # Sol paneli kilit esnasında sade tutuyoruz
    st.sidebar.markdown("<h1 style='text-align: center; font-size: 28px; color: #38bdf8;'>🎓 ExamAI</h1>", unsafe_allow_html=True)
    st.sidebar.info("🔒 Sistem kilitli. Lütfen ana ekrandan giriş yapın.")
    
    # Ana Ekrandaki Giriş Paneli
    st.title("🔒 ExamAI Güvenlik Duvarı")
    st.markdown("""
    ### Sisteme Giriş Yapabilmek İçin API Anahtarı Gereklidir.
    Arkadaki yapay zekâ motorunun, ajandanın ve çalışma asistanının kilitlerini açmak için lütfen aşağıdaki kutuya geçerli bir **Gemini API Key** girip giriş yapın.
    """)
    
    # 🎯 KULLANICININ DİREKT YAZABİLECEĞİ MERKEZİ INPUT ALANI
    girilen_key = st.text_input("Gemini API Key'inizi Buraya Yapıştırın:", type="password", placeholder="AIzaSy...")
    
    if st.button("🚀 Sistemin Kilidini Aç ve Giriş Yap", type="primary"):
        if girilen_key:
            st.session_state["api_key_entered"] = girilen_key
            st.success("Giriş başarılı! Sistem yükleniyor...")
            st.rerun()
        else:
            st.error("Lütfen boş bir anahtar girmeyin!")

    # Rehber Bölümü
    st.markdown("""
    <div style="background-color: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-top: 20px;">
        <h4 style="color: #38bdf8; margin-top: 0;">🔑 Ücretsiz Gemini API Key Nasıl Alınır?</h4>
        <ol style="color: #94a3b8; line-height: 1.6;">
            <li>Aşağıdaki butona tıklayarak resmi <strong>Google AI Studio</strong> platformuna gidin.</li>
            <li>Google (Gmail) hesabınızla giriş yapın.</li>
            <li>Sol üst köşede bulunan yeşil <strong>"Get API key"</strong> (API Anahtarı Al) butonuna basın.</li>
            <li>Açılan ekranda <strong>"Create API key"</strong> seçeneğini seçip anahtarınızı saniyeler içinde kopyalayın.</li>
        </ol>
        <a href="https://aistudio.google.com/" target="_blank" class="key-button">🔑 Google AI Studio'dan Ücretsiz Key Al</a>
    </div>
    """, unsafe_allow_html=True)
else:
    # API KEY MEVCUTSA SOL PANEL VE SİSTEM EKSİKSİZ AÇILIR
    api_key = st.session_state["api_key_entered"]
    client = genai.Client(api_key=api_key)

    # 2. Sol Menü (Navigasyon Aktif)
    st.sidebar.markdown("<h1 style='text-align: center; font-size: 28px; color: #38bdf8;'>🎓 ExamAI</h1>", unsafe_allow_html=True)
    sayfa = st.sidebar.radio("Gitmek İstediğiniz Sayfa:", ["📚 Yapay Zekâ Asistanı", "📅 Akıllı Ajanda & Takvim"])
    
    st.sidebar.divider()
    
    # 🎵 ENTEGRE ÇALIŞAN SPOTIFY GÖMÜSÜ
    st.sidebar.markdown("### 🎵 ExamAI Radyo")
    muzik_secim = st.sidebar.selectbox("Müzik Modu:", ["🔥 Ezhel Özel Mix", "🧠 Study Music (Lo-Fi)"])

    if "radyo_aktif" not in st.session_state:
        st.session_state["radyo_aktif"] = False

    if not st.session_state["radyo_aktif"]:
        if st.sidebar.button("▶️ Oynatıcıyı Yükle"):
            st.session_state["radyo_aktif"] = True
            st.rerun()
    else:
        if muzik_secim == "🔥 Ezhel Özel Mix":
            st.sidebar.markdown('<iframe src="https://open.spotify.com/playlist/0omU17rR3fRfRnpuT0aq4B?si=4604a355680c44b8" width="100%" height="80" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<iframe src="https://open.spotify.com/embed/playlist/37i9dQZF1DWWQRwui0ExPn" width="100%" height="80" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>', unsafe_allow_html=True)
        
        if st.sidebar.button("⏹️ Radyoyu Kapat"):
            st.session_state["radyo_aktif"] = False
            st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("🚪 Çıkış Yap / Key Sıfırla"):
        st.session_state["api_key_entered"] = ""
        st.rerun()

    # ==========================================
    # SAYFA 1: YAPAY ZEKÂ ASİSTANI
    # ==========================================
    if sayfa == "📚 Yapay Zekâ Asistanı":
        st.title("📚 ExamAI Pro Akademik Asistan")
        st.markdown(f'<div class="motivation-banner">💡 {random.choice(MOTIVASYON_SOZLERI)}</div>', unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8;'>Derslerinize gece-gündüz odaklanabilmeniz için tasarlanmış premium yapay zekâ asistanı.</p>", unsafe_allow_html=True)
        st.divider()

        input_tab1, input_tab2 = st.tabs(["📄 PDF Yükleme İstasyonu", "✍️ Ham Metin Girişi"])
        
        with input_tab1:
            uploaded_file = st.file_uploader("Ders dökümanınızı buraya sürükleyin (PDF)", type=["pdf"])
            if uploaded_file is not None:
                with st.spinner("Döküman analiz ediliyor..."):
                    st.session_state["current_material"] = extract_text_from_pdf(uploaded_file)
                st.success("Döküman başarıyla yüklendi!")

        with input_tab2:
            user_text = st.text_area("Notları buraya aktarın:", height=100)
            if user_text: st.session_state["current_material"] = user_text

        if st.session_state["current_material"]:
            if st.button("✨ Materyali İşle ve Masayı Hazırla", type="primary"):
                with st.spinner("Gemini 2.5-flash derinlemesine inceliyor..."):
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=st.session_state["current_material"],
                        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.3)
                    )
                    st.session_state["full_raw_output"] = response.text
                    st.session_state["ai_results"] = parse_ai_response(response.text)

        if st.session_state["ai_results"] is not None:
            st.divider()
            st.markdown("## 📊 Akıllı Çalışma Alanı")
            res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs(["📖 Konu Anlatımı", "📝 Hap Özetler", "❓ Hazırlık Soruları", "📺 Video Dersler"])
            results = st.session_state["ai_results"]
            with res_tab1: st.markdown(f'<div class="edu-card">{results["konu"]}</div>', unsafe_allow_html=True)
            with res_tab2: st.markdown(f'<div class="edu-card">{results["ozet"]}</div>', unsafe_allow_html=True)
            with res_tab3:
                st.markdown(f'<div class="edu-card">{results["sorular"]}</div>', unsafe_allow_html=True)
                with st.expander("🔑 Detaylı Çözümleri İncele"): st.markdown(results["cevaplar"])
            with res_tab4: st.markdown(results["youtube"], unsafe_allow_html=True)
            
            st.markdown("### 🔄 Yapay Zekâya Not Bırak / Özelleştir")
            revize_istegi = st.text_input("Bu notlarda neyi değiştirmek istersiniz?", placeholder="Örn: Soruları biraz daha zorlaştır veya konu anlatımını zenginleştir.")
            
            if st.button("💬 İstek Gönder"):
                if revize_istegi:
                    with st.spinner("İstediğiniz düzenlemeler bizzat işleniyor..."):
                        revize_prompt = f"Mevcut Döküman:\n{st.session_state['full_raw_output']}\n\nKullanıcı İsteği:\n{revize_istegi}\n\nLütfen dökümanı bu isteğe göre güncelle."
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=revize_prompt,
                            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.3)
                        )
                        st.session_state["full_raw_output"] = response.text
                        st.session_state["ai_results"] = parse_ai_response(response.text)
                        st.success("Çalışma alanınız güncellendi!")
                        st.rerun()
                        
            st.divider()
            pdf_data = generate_pdf(st.session_state["full_raw_output"])
            st.download_button(label="📥 Tüm Notları Premium PDF Olarak İndir", data=pdf_data, file_name="ExamAI_Premium_Notlar.pdf", mime="application/pdf")

    # ==========================================
    # SAYFA 2: AKILLI AJANDA & TAKVİM
    # ==========================================
    elif sayfa == "📅 Akıllı Ajanda & Takvim":
        st.title("📅 Yenilikçi Akademik Planlama Merkezi")
        st.markdown(f'<div class="motivation-banner">🔥 {random.choice(MOTIVASYON_SOZLERI)}</div>', unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8;'>Yapay zekâ destekli doğal dil algılama ve akademik analitik paneli.</p>", unsafe_allow_html=True)
        st.divider()
        
        # 📊 AKADEMİK ANALİTİK PANELİ
        toplam_görev = len(st.session_state["events"])
        sinavlar = sum(1 for e in st.session_state["events"] if e.get("extendedProps", {}).get("category") == "Sınav")
        odevler = sum(1 for e in st.session_state["events"] if e.get("extendedProps", {}).get("category") == "Ödev")
        devam_eden = sum(1 for e in st.session_state["events"] if e.get("extendedProps", {}).get("status", "Devam Ediyor") == "Devam Ediyor")
        
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-box"><div class="metric-val">{toplam_görev}</div><div class="metric-lbl">Toplam Planlanan</div></div>
                <div class="metric-box"><div class="metric-val" style="color: #ef4444;">{sinavlar}</div><div class="metric-lbl">Aktif Sınav</div></div>
                <div class="metric-box"><div class="metric-val" style="color: #f59e0b;">{odevler}</div><div class="metric-lbl">Bekleyen Ödev</div></div>
                <div class="metric-box"><div class="metric-val" style="color: #10b981;">{devam_eden}</div><div class="metric-lbl">Kalan Görev Yükü</div></div>
            </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### 🧠 Yapay Zekâ ile Hızlı Ekle")
            nlp_text = st.text_area("Programınızı buraya özgürce yazın:", placeholder="Örn: Haftaya salı günü proje teslimim var.", height=80)
            
            if st.button("⚡ Akıllı Ayrıştır ve Ekle", type="secondary"):
                if nlp_text:
                    with st.spinner("Yapay zekâ zaman ve başlığı ayrıştırıyor..."):
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=nlp_text,
                                config=types.GenerateContentConfig(system_instruction=NLP_CALENDAR_INSTRUCTION, temperature=0.1)
                            )
                            
                            clean_response_text = response.text.strip().replace("```json", "").replace("```", "")
                            data = json.loads(clean_response_text)
                            
                            color_map = {"Sınav": "#ef4444", "Ödev": "#f59e0b", "Proje": "#10b981", "Kişisel": "#38bdf8"}
                            event_color = color_map.get(data.get("category", "Kişisel"), "#38bdf8")
                            
                            new_event = {
                                "id": str(len(st.session_state["events"]) + 1),
                                "title": data.get("title", "Yeni Görev"),
                                "start": data.get("start"),
                                "end": data.get("end"),
                                "color": event_color,
                                "extendedProps": {"category": data.get("category", "Kişisel"), "status": "Devam Ediyor"}
                            }
                            st.session_state["events"].append(new_event)
                            st.success(f"Başarıyla ayrıştırıldı: {data.get('title')}")
                            st.rerun()
                        except Exception as e:
                            st.error("Metin ayrıştırılamadı. Manuel alanı deneyin.")
            
            st.write("---")
            
            st.markdown("### ✍️ Manuel Görev Ekle")
            with st.form("etkinlik_formu", clear_on_submit=True):
                görev_adi = st.text_input("Etkinlik Adı:")
                kat = st.selectbox("Kategori:", ["Sınav", "Ödev", "Proje", "Kişisel"])
                tarih = st.date_input("Tarih:")
                saat_baslangic = st.time_input("Başlangıç Saati:")
                
                submit_button = st.form_submit_button(label="Ajandaya Sabitle")
                if submit_button and görev_adi:
                    color_map = {"Sınav": "#ef4444", "Ödev": "#f59e0b", "Proje": "#10b981", "Kişisel": "#38bdf8"}
                    st.session_state["events"].append({
                        "id": str(len(st.session_state["events"]) + 1),
                        "title": f"{görev_adi}",
                        "start": f"{tarih}T{saat_baslangic}",
                        "end": f"{tarih}T{saat_baslangic}",
                        "color": color_map[kat],
                        "extendedProps": {"category": kat, "status": "Devam Ediyor"}
                    })
                    st.rerun()

        with col2:
            st.markdown("### 📆 İnteraktif Zaman Çizelgesi")
            calendar_options = {
                "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,listMonth"},
                "initialView": "dayGridMonth",
                "selectable": True,
                "themeSystem": "bootstrap5"
            }
            
            calendar(events=st.session_state["events"], options=calendar_options)
            
            if st.session_state["events"]:
                st.markdown("### 📋 Görev Takip Paneli")
                for ev in st.session_state["events"]:
                    col_title, col_btn = st.columns([3, 1])
                    with col_title:
                        st.markdown(f"**{ev['title']}** | 🕒 {ev['start'].replace('T', ' ')}")
                    with col_btn:
                        if st.button("🗑️ Sil", key=f"del_{ev['id']}"):
                            st.session_state["events"] = [e for e in st.session_state["events"] if e["id"] != ev["id"]]
                            st.rerun()
            
            if st.button("🗑️ Tüm Ajandayı Sıfırla", type="primary"):
                st.session_state["events"] = []
                st.rerun()
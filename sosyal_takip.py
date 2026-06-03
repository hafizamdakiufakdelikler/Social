import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import io
import os
import re
from collections import Counter
from streamlit_gsheets import GSheetsConnection

# Sayfa ayarlarını en başta tanımlıyoruz
st.set_page_config(page_title="RH+ Yönetim Paneli", layout="wide", page_icon="🚀")

# ==========================================
# 🔒 GİRİŞ SİSTEMİ (MODERN VE MOBİL UYUMLU)
# ==========================================
GIRIS_SIFRESI = "RHplus2026*"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            if os.path.exists("logo.jpg"):
                st.image("logo.jpg", use_container_width=True)
            else:
                st.markdown("<h1 style='text-align: center;'>RH+ Reklam Film</h1>", unsafe_allow_html=True)
            
            st.markdown("<h3 style='text-align: center; color: gray;'>Yönetim Paneli Girişi</h3>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            sifre_giris = st.text_input("Erişim Şifresi:", type="password", placeholder="Şifrenizi giriniz...", label_visibility="collapsed")
            
            if st.button("Sisteme Giriş Yap", use_container_width=True, type="primary"):
                if sifre_giris == GIRIS_SIFRESI:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("⚠️ Hatalı şifre! Lütfen tekrar deneyin.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("💡 **Aydınlık/Karanlık Tema:** Sağ üst köşedeki üç noktaya (⋮) tıklayıp **Settings > Theme** menüsünden temanızı değiştirebilirsiniz.")
    
    st.stop()

# ==========================================
# VERİTABANI VE LİSTE BAĞLANTILARI
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Google Sheets bağlantısı kurulamadı. Lütfen bulut panelindeki Secrets ayarlarınızı kontrol edin.")
    st.stop()

def canlı_veritabanı_yukle():
    try:
        df = conn.read(worksheet="Veritabanı", ttl=0)
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception:
        return []

def canlı_veritabanı_kaydet(data_list):
    if data_list:
        df = pd.DataFrame(data_list)
    else:
        df = pd.DataFrame(columns=[
            "Ay", "Tarih", "Kayıt Adı", "Tür", "platform", 
            "url", "baslik", "aciklama", "etiketler",
            "web_haber", "web_duyuru", "web_not", "genel_not"
        ])
    conn.update(worksheet="Veritabanı", data=df)

def bulut_listelerini_yukle():
    try:
        df = conn.read(worksheet="Ayarlar", ttl=0)
        df = df.fillna("")
        kisiler = [x for x in df["Kişiler"].tolist() if x != ""]
        siteler = [x for x in df["Web Siteleri"].tolist() if x != ""]
        if not kisiler: kisiler = [f"Takip Edilen Kişi {i}" for i in range(1, 11)]
        if not siteler: siteler = [f"Haber/Kurum Sitesi {i}" for i in range(1, 6)]
        return {"kisiler": kisiler, "web_siteleri": siteler}
    except Exception:
        return {
            "kisiler": [f"Takip Edilen Kişi {i}" for i in range(1, 11)],
            "web_siteleri": [f"Haber/Kurum Sitesi {i}" for i in range(1, 6)]
        }

def bulut_listelerini_kaydet(lists):
    max_len = max(len(lists["kisiler"]), len(lists["web_siteleri"]))
    kisiler_list = lists["kisiler"] + [""] * (max_len - len(lists["kisiler"]))
    siteler_list = lists["web_siteleri"] + [""] * (max_len - len(lists["web_siteleri"]))
    df = pd.DataFrame({"Kişiler": kisiler_list, "Web Siteleri": siteler_list})
    conn.update(worksheet="Ayarlar", data=df)

st.session_state.veri_tabani = canlı_veritabanı_yukle()
st.session_state.sabit_listeler = bulut_listelerini_yukle()

if "temp_preview" not in st.session_state:
    st.session_state.temp_preview = {"url": "", "title": "", "description": "", "image": None, "tags": "", "platform": ""}

aylar_sabit = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# ==========================================
# AKILLI METİN VE ETİKET ANALİZ MOTORU
# ==========================================
def otomatik_etiket_uret(metin):
    if not metin or metin.strip() == "": return ""
    metin = metin.lower()
    kelimeler = re.findall(r'\b[a-zçğıöşü]{4,}\b', metin)
    stop_words = ["için", "göre", "tarafından", "hakkında", "ile", "veya", "olan", "olarak", "daha", "gibi", "kadar", "sonra", "önce", "üzere", "birlikte", "dair", "yeni", "korumalı", "gizli", "içerik", "lütfen", "aşağıdaki", "kutuya", "yapıştırın"]
    temiz_kelimeler = [k for k in kelimeler if k not in stop_words]
    en_cok_gecenler = [k[0] for k in Counter(temiz_kelimeler).most_common(4)]
    return ", ".join(en_cok_gecenler).title()

def get_link_preview(url):
    url_lower = url.lower()
    detected_platform = "Web Sitesi"
    
    if "instagram.com" in url_lower: detected_platform = "Instagram"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower: detected_platform = "YouTube"
    elif "linkedin.com" in url_lower: detected_platform = "LinkedIn"
    elif "x.com" in url_lower or "twitter.com" in url_lower: detected_platform = "X"
    elif "facebook.com" in url_lower: detected_platform = "Facebook"
    elif "nsosyal" in url_lower: detected_platform = "Nsosyal"

    try:
        # YOUTUBE İçin Yasal API (OEmbed)
        if detected_platform == "YouTube":
            api_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            res = requests.get(api_url, timeout=5).json()
            baslik = res.get("title", "Başlık Bulunamadı")
            aciklama = f"Kanal: {res.get('author_name', 'Bilinmeyen Kanal')} (YouTube Videosu)"
            image_url = res.get("thumbnail_url")
            return {"title": baslik, "description": aciklama, "image": image_url, "tags": otomatik_etiket_uret(baslik), "platform": "YouTube"}

        # X (Twitter) İçin JSON API Çözümü
        if detected_platform == "X":
            api_url = url.replace("x.com", "api.vxtwitter.com").replace("twitter.com", "api.vxtwitter.com").split("?")[0]
            try:
                res = requests.get(api_url, timeout=5).json()
            except:
                api_url = url.replace("x.com", "api.fxtwitter.com").replace("twitter.com", "api.fxtwitter.com").split("?")[0]
                res = requests.get(api_url, timeout=5).json()
                
            baslik = f"@{res.get('user_screen_name', 'Kullanıcı')} (X Gönderisi)"
            aciklama = res.get('text', 'İçerik okunamadı.')
            image_url = None
            if res.get('media_extended') and len(res['media_extended']) > 0:
                image_url = res['media_extended'][0].get('url')
            elif res.get('mediaURLs') and len(res['mediaURLs']) > 0:
                image_url = res['mediaURLs'][0]
                
            return {"title": baslik, "description": aciklama, "image": image_url, "tags": otomatik_etiket_uret(aciklama), "platform": "X"}

        # INSTAGRAM, FACEBOOK, LINKEDIN İÇİN WHATSAPP/MESSENGER BOT TAKLİDİ
        headers = {
            'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        
        baslik = og_title["content"] if og_title else ""
        aciklama = og_desc["content"] if og_desc else ""
        image_url = og_image["content"] if og_image else None
        
        if not baslik:
            fallback_title = soup.find("title")
            baslik = fallback_title.text.strip() if fallback_title else ""
        
        # Site yine de giriş duvarı çıkarırsa yakala
        engelli_kelimeler = ["Access Denied", "Just a moment", "Log In", "Sign Up", "LinkedIn Login", "Login • Instagram", "Facebook - Log In"]
        if not baslik or any(kelime in baslik for kelime in engelli_kelimeler):
            return {
                "title": "🔒 Korumalı/Gizli İçerik",
                "description": "Bu hesap gizli olduğu için platform okumaya izin vermiyor. Lütfen metni aşağıdaki manuel giriş alanına yapıştırın.",
                "image": None,
                "tags": "", 
                "platform": detected_platform
            }
        
        return {
            "title": baslik,
            "description": aciklama,
            "image": image_url,
            "tags": otomatik_etiket_uret(baslik + " " + aciklama),
            "platform": detected_platform
        }
        
    except Exception:
        return {
            "title": "🔒 Korumalı İçerik",
            "description": "Platform bağlantıyı reddetti. Lütfen metni manuel olarak aşağıdaki kutuya yapıştırın.",
            "image": None,
            "tags": "",
            "platform": detected_platform
        }

# ==========================================
# SOL MENÜ (SIDEBAR)
# ==========================================
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)

st.sidebar.title("🗂️ Yönetim Paneli")
ana_sekme = st.sidebar.radio("Menü Seçimi:", ["📝 Günlük Veri Girişi", "⚡ Anlık Özet Panosu", "📊 Aylık Rapor Merkezi"])

st.sidebar.markdown("---")
if ana_sekme == "📝 Günlük Veri Girişi":
    st.sidebar.subheader("⚙️ Takip Listesi Ayarları")
    kayit_turu = st.sidebar.radio("Çalışma Alanı:", ["👤 Kişiler / Kuruluşlar", "🌐 Web Siteleri"])

    with st.sidebar.expander("✏️ İsimleri Düzenle veya Ekle", expanded=False):
        if "👤 Kişiler / Kuruluşlar" in kayit_turu:
            secilen_kayit = st.selectbox("Düzenlenecek Kişi/Kurum:", st.session_state.sabit_listeler["kisiler"])
            yeni_isim = st.text_input("Seçili İsmi Değiştir:", value=secilen_kayit)
            if st.button("🔄 İsmi Güncelle", use_container_width=True):
                if yeni_isim and yeni_isim != secilen_kayit:
                    idx = st.session_state.sabit_listeler["kisiler"].index(secilen_kayit)
                    st.session_state.sabit_listeler["kisiler"][idx] = yeni_isim
                    bulut_listelerini_kaydet(st.session_state.sabit_listeler)
                    for entry in st.session_state.veri_tabani:
                        if entry.get("Kayıt Adı") == secilen_kayit and entry.get("Tür") == "Kişi/Kurum":
                            entry["Kayıt Adı"] = yeni_isim
                    canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                    st.toast("İsim başarıyla güncellendi!", icon="✅")
                    st.rerun()
            yeni_kisi =
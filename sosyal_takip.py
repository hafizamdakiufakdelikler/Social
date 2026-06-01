import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import io
import os
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="RH+ Sosyal Medya Yönetim Paneli", layout="wide")

# ==========================================
# 🔒 GİRİŞ SİSTEMİ VE GÜVENLİK AYARI
# ==========================================
# Uygulamanın giriş şifresini buradan değiştirebilirsiniz:
GIRIS_SIFRESI = "RHplus2026*"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Eğer kullanıcı giriş yapmadıysa sadece giriş ekranını göster
if not st.session_state.logged_in:
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo.jpg"):
            st.image("logo.jpg", use_container_width=True)
        
        st.title("🔒 Kurumsal Yönetim Paneli")
        st.subheader("RH+ Reklam Film Tasarım")
        
        sifre_giris = st.text_input("Lütfen erişim şifresini giriniz:", type="password")
        
        if st.button("Sisteme Giriş Yap", use_container_width=True):
            if sifre_giris == GIRIS_SIFRESI:
                st.session_state.logged_in = True
                st.success("Giriş başarılı! Sistem yükleniyor...")
                st.rerun()
            else:
                st.error("Hatalı şifre! Lütfen tekrar deneyiniz.")
    st.stop() # Giriş yapılmadığı sürece kodun kalanını çalıştırma ve gizle

# ==========================================
# GOOGLE SHEETS CANLI BAĞLANTI AYARLARI
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Google Sheets bağlantısı kurulamadı. Lütfen bulut panelindeki Secrets (Sırlar) ayarlarınızı kontrol edin.")
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
            "url", "baslik", "aciklama", "web_haber", "web_duyuru", "web_not", "genel_not"
        ])
    conn.update(worksheet="Veritabanı", data=df)

st.session_state.veri_tabani = canlı_veritabanı_yukle()

if "kisiler" not in st.session_state:
    st.session_state.kisiler = [f"Takip Edilen Kişi {i}" for i in range(1, 11)]
if "web_siteleri" not in st.session_state:
    st.session_state.web_siteleri = [f"Haber/Kurum Sitesi {i}" for i in range(1, 6)]

if "temp_preview" not in st.session_state:
    st.session_state.temp_preview = {"url": "", "title": "", "description": "", "image": None}

platform_listesi = ["Instagram", "YouTube", "LinkedIn", "X", "Nsosyal", "Facebook"]

def get_link_preview(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        return {
            "title": og_title["content"] if og_title else "Başlık bulunamadı",
            "description": og_desc["content"] if og_desc else "Açıklama bulunamadı",
            "image": og_image["content"] if og_image else None
        }
    except Exception:
        return None

# ==========================================
# SOL MENÜ (SIDEBAR)
# ==========================================
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)

st.sidebar.title("🗂️ Yönetim Paneli")
ana_sekme = st.sidebar.radio("Giriş / Rapor Seçimi:", ["📝 Günlük Veri Girişi", "📊 Rapor ve Çıktı Merkezi"])

# Güvenli Çıkış Butonu
if st.sidebar.button("🚪 Sistemden Güvenli Çıkış"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
if ana_sekme == "📝 Günlük Veri Girişi":
    st.sidebar.subheader("👤 Takip Listesi Ayarları")
    kayit_turu = st.sidebar.radio("Tür Seçin:", ["👤 Kişiler / Kuruluşlar", "🌐 Web Siteleri"])

    if "👤 Kişiler / Kuruluşlar" in kayit_turu:
        secilen_kayit = st.sidebar.selectbox("Kişi/Kurum Seçin:", st.session_state.kisiler)
        yeni_isim = st.sidebar.text_input("✏️ Seçili İsmi Değiştir:", value=secilen_kayit)
        if st.sidebar.button("🔄 İsmi Güncelle"):
            if yeni_isim and yeni_isim != secilen_kayit:
                idx = st.session_state.kisiler.index(secilen_kayit)
                st.session_state.kisiler[idx] = yeni_isim
                for entry in st.session_state.veri_tabani:
                    if entry.get("Kayıt Adı") == secilen_kayit and entry.get("Tür") == "Kişi/Kurum":
                        entry["Kayıt Adı"] = yeni_isim
                canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                st.success("İsim Google Sheets üzerinde güncellendi!")
                st.rerun()
        yeni_kisi = st.sidebar.text_input("➕ Yeni Kişi/Kurum Ekle:")
        if st.sidebar.button("Kişiyi Ekle"):
            if yeni_kisi and yeni_kisi not in st.session_state.kisiler:
                st.session_state.kisiler.append(yeni_kisi)
                st.rerun()
    else:
        secilen_kayit = st.sidebar.selectbox("Web Sitesi Seçin:", st.session_state.web_siteleri)
        yeni_site_ismi = st.sidebar.text_input("✏️ Seçili Site İsmini Değiştir:", value=secilen_kayit)
        if st.sidebar.button("🔄 Site İsmini Güncelle"):
            if yeni_site_ismi and yeni_site_ismi != secilen_kayit:
                idx = st.session_state.web_siteleri.index(secilen_kayit)
                st.session_state.web_siteleri[idx] = yeni_site_ismi
                for entry in st.session_state.veri_tabani:
                    if entry.get("Kayıt Adı") == secilen_kayit and entry.get("Tür") == "Web Sitesi":
                        entry["Kayıt Adı"] = yeni_site_ismi
                canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                st.success("Site ismi Google Sheets üzerinde güncellendi!")
                st.rerun()
        yeni_site = st.sidebar.text_input("➕ Yeni Web Sitesi Ekle:")
        if st.sidebar.button("Siteyi Ekle"):
            if yeni_site and yeni_site not in st.session_state.web_siteleri:
                st.session_state.web_siteleri.append(yeni_site)
                st.rerun()

# ==========================================
# ANA EKRAN - VERI GIRISI
# ==========================================
aylar = ["Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

if ana_sekme == "📝 Günlük Veri Girişi":
    st.title("🚀 Medya ve İçerik Yönetim Paneli")
    
    col_ay, col_gun = st.columns(2)
    with col_ay:
        secilen_ay = st.selectbox("📅 Ay Seçin:", aylar)
    with col_gun:
        gun_sayisi = 31 if secilen_ay in ["Temmuz", "Ağustos", "Ekim", "Aralık"] else 30
        gunler = [f"{str(i).zfill(2)} {secilen_ay}" for i in range(1, gun_sayisi + 1)]
        secilen_gun = st.selectbox("📆 Gün Seçin:", gunler)

    st.markdown("---")
    st.header(f"📝 Veri Girişi: {secilen_kayit} ({secilen_gun})")

    mevcut_kayitlar = [x for x in st.session_state.veri_tabani if x.get("Tarih") == secilen_gun and x.get("Kayıt Adı") == secilen_kayit]
    if mevcut_kayitlar:
        with st.expander(f"📋 Bugün Bu Kayda Eklenen Mevcut Gönderiler ({len(mevcut_kayitlar)} Adet)", expanded=True):
            for idx, mk in enumerate(mevcut_kayitlar):
                col_rec_text, col_rec_del = st.columns([5, 1])
                with col_rec_text:
                    if mk.get("Tür") == "Kişi/Kurum":
                        st.write(f"**{idx+1}. [{mk.get('platform')}]** {mk.get('url')[:60]}... | *{mk.get('baslik')}*")
                    else:
                        st.write(f"**{idx+1}. [Web Sitesi]** Haber: {mk.get('web_haber')[:30]}... | Duyuru: {mk.get('web_duyuru')[:30]}...")
                with col_rec_del:
                    if st.button("🗑️ Sil", key=f"del_{idx}_{mk.get('url')[:10]}"):
                        st.session_state.veri_tabani.remove(mk)
                        canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                        st.success("Kayıt buluttan silindi!")
                        st.rerun()

    st.subheader("➕ Yeni İçerik / Gönderi Ekle")
    
    if "👤 Kişiler / Kuruluşlar" in kayit_turu:
        col_plat, col_url = st.columns([1, 3])
        with col_plat:
            g_platform = st.selectbox("Platform:", platform_listesi)
        with col_url:
            g_url = st.text_input("Post URL Linki (Yeni):", value="")
        
        if g_url and g_url != st.session_state.temp_preview["url"]:
            with st.spinner("Link analiz ediliyor..."):
                preview = get_link_preview(g_url)
                if preview:
                    st.session_state.temp_preview = {
                        "url": g_url, "title": preview["title"], "description": preview["description"], "image": preview["image"]
                    }
                else:
                    st.session_state.temp_preview = {"url": g_url, "title": "Başlık bulunamadı", "description": "Açıklama bulunamadı", "image": None}

        if st.session_state.temp_preview["title"] and g_url:
            st.markdown("#### 📋 Otomatik Çekilen İçerik Önizlemesi")
            col_img, col_txt = st.columns([1, 2])
            with col_img:
                if st.session_state.temp_preview["image"]:
                    st.image(st.session_state.temp_preview["image"], use_container_width=True)
            with col_txt:
                st.subheader(st.session_state.temp_preview["title"])
                st.write(st.session_state.temp_preview["description"])
                
        g_web_haber, g_web_duyuru, g_web_not = "-", "-", "-"
    else:
        col_h, col_d, col_n = st.columns(3)
        with col_h:
            g_web_haber = st.text_area("📰 Haberler:", height=120)
        with col_d:
            g_web_duyuru = st.text_area("📢 Duyurular:", height=120)
        with col_n:
            g_web_not = st.text_area("📝 Özel Notlar:", height=120)
        g_platform, g_url = "-", "-"

    st.markdown("---")
    col_not, col_foto = st.columns([1, 2])
    with col_not:
        g_genel_not = st.text_area("Eklemek istediğiniz genel not:", height=150)
    with col_foto:
        yuklenen_dosyalar = st.file_uploader("En fazla 6 adet fotoğraf sürükleyin:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        if yuklenen_dosyalar and len(yuklenen_dosyalar) > 6:
            st.error("Maksimum 6 fotoğraf yükleyebilirsiniz!")

    st.markdown("---")
    if st.button("💾 Bu Gönderiyi Google Sheets Bulutuna Kaydet", use_container_width=True):
        yeni_kayit = {
            "Ay": secilen_ay, "Tarih": secilen_gun, "Kayıt Adı": secilen_kayit, 
            "Tür": "Kişi/Kurum" if "👤" in kayit_turu else "Web Sitesi",
            "platform": g_platform, "url": g_url, 
            "baslik": st.session_state.temp_preview["title"] if "👤" in kayit_turu else "-", 
            "aciklama": st.session_state.temp_preview["description"] if "👤" in kayit_turu else "-",
            "web_haber": g_web_haber, "web_duyuru": g_web_duyuru, "web_not": g_web_not, 
            "genel_not": g_genel_not
        }
        st.session_state.veri_tabani.append(yeni_kayit)
        canlı_veritabanı_kaydet(st.session_state.veri_tabani)
        st.session_state.temp_preview = {"url": "", "title": "", "description": "", "image": None}
        st.success(f"🎉 Rapor başarıyla doğrudan Google Sheets dosyanıza işlendi!")
        st.rerun()

# ==========================================
# ANA EKRAN - RAPORLAMA VE EXCEL CIKTI
# ==========================================
elif ana_sekme == "📊 Rapor ve Çıktı Merkezi":
    st.title("📊 Aylık Raporlama ve Çıktı Merkezi")
    rapor_ay = st.selectbox("🔍 Raporunu Görmek İstediğiniz Ayı Seçin:", aylar)
    
    rapor_listesi = []
    for deger in st.session_state.veri_tabani:
        if deger.get("Ay") == rapor_ay:
            rapor_listesi.append({
                "Tarih": deger.get("Tarih"),
                "Kayıt/Kurum Adı": deger.get("Kayıt Adı"),
                "Tür": deger.get("Tür"),
                "Sosyal Medya Platform": deger.get("platform"),
                "Post URL": deger.get("url"),
                "Çekilen Başlık": deger.get("baslik"),
                "Web - Haber": deger.get("web_haber"),
                "Web - Duyuru": deger.get("web_duyuru"),
                "Web - Not": deger.get("web_not"),
                "Genel Not": deger.get("genel_not")
            })
            
    if rapor_listesi:
        df_rapor = pd.DataFrame(rapor_listesi)
        df_rapor = df_rapor.sort_values(by="Tarih")
        
        st.subheader(f"📈 {rapor_ay} Ayı Toplu Bulut Raporu ({len(df_rapor)} Gönderi Arşivlendi)")
        st.dataframe(df_rapor, use_container_width=True, hide_index=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_rapor.to_excel(writer, sheet_name=rapor_ay, index=False)
        
        st.markdown("---")
        st.download_button(
            label=f"📥 {rapor_ay} Ayı Raporunu Excel Olarak İndir",
            data=buffer.getvalue(),
            file_name=f"{rapor_ay}_Sosyal_Medya_Raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info(f"{rapor_ay} ayına ait henüz bulutta kaydedilmiş bir veri bulunamadı.")
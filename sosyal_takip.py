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
GIRIS_SIFRESI = "RHplus2026*"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
                st.success("Giriş başarılı!")
                st.rerun()
            else:
                st.error("Hatalı şifre!")
    st.stop()

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
            "url", "baslik", "aciklama", "begeni", "yorum", "etiketler",
            "web_haber", "web_duyuru", "web_not", "genel_not"
        ])
    conn.update(worksheet="Veritabanı", data=df)

def bulut_listelerini_yukle():
    try:
        df = conn.read(worksheet="Ayarlar", ttl=0)
        df = df.fillna("")
        
        if "Kişiler" not in df.columns or "Web Siteleri" not in df.columns:
            st.sidebar.error(f"Sütun Başlığı Hatası! Lütfen Ayarlar sekmesindeki A1 ve B1 hücrelerinin 'Kişiler' ve 'Web Siteleri' olduğundan emin olun.")
            
        kisiler = [x for x in df["Kişiler"].tolist() if x != ""]
        siteler = [x for x in df["Web Siteleri"].tolist() if x != ""]
        
        if not kisiler: kisiler = [f"Takip Edilen Kişi {i}" for i in range(1, 11)]
        if not siteler: siteler = [f"Haber/Kurum Sitesi {i}" for i in range(1, 6)]
            
        return {"kisiler": kisiler, "web_siteleri": siteler}
    except Exception as e:
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

if st.sidebar.button("🚪 Sistemden Güvenli Çıkış"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
if ana_sekme == "📝 Günlük Veri Girişi":
    st.sidebar.subheader("👤 Takip Listesi Ayarları")
    kayit_turu = st.sidebar.radio("Tür Seçin:", ["👤 Kişiler / Kuruluşlar", "🌐 Web Siteleri"])

    if "👤 Kişiler / Kuruluşlar" in kayit_turu:
        secilen_kayit = st.sidebar.selectbox("Kişi/Kurum Seçin:", st.session_state.sabit_listeler["kisiler"])
        yeni_isim = st.sidebar.text_input("✏️ Seçili İsmi Değiştir:", value=secilen_kayit)
        if st.sidebar.button("🔄 İsmi Güncelle"):
            if yeni_isim and yeni_isim != secilen_kayit:
                idx = st.session_state.sabit_listeler["kisiler"].index(secilen_kayit)
                st.session_state.sabit_listeler["kisiler"][idx] = yeni_isim
                bulut_listelerini_kaydet(st.session_state.sabit_listeler)
                for entry in st.session_state.veri_tabani:
                    if entry.get("Kayıt Adı") == secilen_kayit and entry.get("Tür") == "Kişi/Kurum":
                        entry["Kayıt Adı"] = yeni_isim
                canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                st.success("İsim Google Sheets'te güncellendi!")
                st.rerun()
        yeni_kisi = st.sidebar.text_input("➕ Yeni Kişi/Kurum Ekle:")
        if st.sidebar.button("Kişiyi Ekle"):
            if yeni_kisi and yeni_kisi not in st.session_state.sabit_listeler["kisiler"]:
                st.session_state.sabit_listeler["kisiler"].append(yeni_kisi)
                bulut_listelerini_kaydet(st.session_state.sabit_listeler)
                st.rerun()
    else:
        secilen_kayit = st.sidebar.selectbox("Web Sitesi Seçin:", st.session_state.sabit_listeler["web_siteleri"])
        yeni_site_ismi = st.sidebar.text_input("✏️ Seçili Site İsmini Değiştir:", value=secilen_kayit)
        if st.sidebar.button("🔄 Site İsmini Güncelle"):
            if yeni_site_ismi and yeni_site_ismi != secilen_kayit:
                idx = st.session_state.sabit_listeler["web_siteleri"].index(secilen_kayit)
                st.session_state.sabit_listeler["web_siteleri"][idx] = yeni_site_ismi
                bulut_listelerini_kaydet(st.session_state.sabit_listeler)
                for entry in st.session_state.veri_tabani:
                    if entry.get("Kayıt Adı") == secilen_kayit and entry.get("Tür") == "Web Sitesi":
                        entry["Kayıt Adı"] = yeni_site_ismi
                canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                st.success("Site ismi Google Sheets'te güncellendi!")
                st.rerun()
        yeni_site = st.sidebar.text_input("➕ Yeni Web Sitesi Ekle:")
        if st.sidebar.button("Siteyi Ekle"):
            if yeni_site and yeni_site not in st.session_state.sabit_listeler["web_siteleri"]:
                st.session_state.sabit_listeler["web_siteleri"].append(yeni_site)
                bulut_listelerini_kaydet(st.session_state.sabit_listeler)
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

    # --- ŞIKLAŞTIRILMIŞ GEÇMİŞ KAYITLAR GÖRÜNÜMÜ ---
    mevcut_kayitlar = [x for x in st.session_state.veri_tabani if x.get("Tarih") == secilen_gun and x.get("Kayıt Adı") == secilen_kayit]
    if mevcut_kayitlar:
        with st.expander(f"📋 Bugün Bu Kayda Eklenen Mevcut Gönderiler ({len(mevcut_kayitlar)} Adet)", expanded=True):
            for idx, mk in enumerate(mevcut_kayitlar):
                col_rec_text, col_rec_del = st.columns([7, 1])
                with col_rec_text:
                    baslik = mk.get('baslik', '')
                    if baslik == "-" or not baslik: baslik = "Başlık Bulunamadı"
                    
                    if mk.get("Tür") == "Kişi/Kurum":
                        st.write(f"**{idx+1}. [{mk.get('platform')}]** ❤️ {mk.get('begeni', 0)} | 💬 {mk.get('yorum', 0)} | *{baslik}*")
                    else:
                        st.write(f"**{idx+1}. [Haber/Duyuru]** 📰 *{baslik}* | 🏷️ {mk.get('etiketler', '-')}")
                with col_rec_del:
                    if st.button("🗑️ Sil", key=f"del_{idx}_{mk.get('url', '')[:10]}"):
                        st.session_state.veri_tabani.remove(mk)
                        canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                        st.success("Kayıt buluttan silindi!")
                        st.rerun()

    st.subheader("➕ Yeni İçerik / Gönderi Ekle")
    
    # --- ORTAK AKILLI LİNK OKUYUCU ALANI ---
    col_plat, col_url = st.columns([1, 3])
    with col_plat:
        if "👤" in kayit_turu:
            g_platform = st.selectbox("Platform:", platform_listesi)
        else:
            g_platform = "Web Sitesi"
            st.info("🌐 Haber / Kurum Sitesi")
            
    with col_url:
        g_url = st.text_input("🔗 Haber veya Gönderi URL Linkini Buraya Yapıştırın:", value="")
        
    if g_url and g_url != st.session_state.temp_preview["url"]:
        with st.spinner("Yapay Zeka Linki Analiz Ediyor..."):
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

    # --- DİNAMİK ALT ALANLAR ---
    if "👤" in kayit_turu:
        col_b, col_y, col_e = st.columns([1, 1, 2])
        with col_b:
            g_begeni = st.number_input("❤️ Beğeni Sayısı:", min_value=0, step=1)
        with col_y:
            g_yorum = st.number_input("💬 Yorum Sayısı:", min_value=0, step=1)
        with col_e:
            g_etiketler = st.text_input("🏷️ Kullanılan Etiketler (Hashtags):")
        g_web_haber, g_web_duyuru, g_web_not = "-", "-", "-"
    else:
        # Web Siteleri için özel ve şık alanlar
        col_e, col_n = st.columns(2)
        with col_e:
            g_etiketler = st.text_input("🏷️ Habere Dair Etiketler (Örn: Savunma, İhale vb.):")
        with col_n:
            g_web_not = st.text_area("📝 Haberle İlgili Özel Notunuz:", height=68)
        
        g_begeni, g_yorum = 0, 0
        g_web_haber = st.session_state.temp_preview["description"]
        g_web_duyuru = "-"

    st.markdown("---")
    g_genel_not = st.text_area("📌 Arşive veya raporlamaya eklemek istediğiniz genel notlar:", height=100)

    st.markdown("---")
    if st.button("💾 Bu Gönderiyi Google Sheets Bulutuna Kaydet", use_container_width=True):
        
        # MÜKERRER KAYIT KONTROLÜ (Boşluk ve Harf Duyarlılığı Giderildi)
        if g_url and g_url.strip() != "-" and g_url.strip() != "":
            temiz_url = g_url.strip().lower()
            kayitli_mi = any(kayit.get("url", "").strip().lower() == temiz_url for kayit in st.session_state.veri_tabani)
            
            if kayitli_mi:
                st.error("⚠️ DİKKAT: Bu URL zaten sistemde kayıtlı! Lütfen farklı bir gönderi linki girin.")
                st.stop()
                
        yeni_kayit = {
            "Ay": secilen_ay, "Tarih": secilen_gun, "Kayıt Adı": secilen_kayit, 
            "Tür": "Kişi/Kurum" if "👤" in kayit_turu else "Web Sitesi",
            "platform": g_platform, "url": g_url.strip(), 
            "baslik": st.session_state.temp_preview["title"] if "👤" in kayit_turu else st.session_state.temp_preview["title"], 
            "aciklama": st.session_state.temp_preview["description"],
            "begeni": g_begeni, "yorum": g_yorum, "etiketler": g_etiketler,
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
                "Beğeni": pd.to_numeric(deger.get("begeni"), errors='coerce') if "begeni" in deger else 0,
                "Yorum": pd.to_numeric(deger.get("yorum"), errors='coerce') if "yorum" in deger else 0,
                "Etiketler": deger.get("etiketler", ""),
                "Web - Haber": deger.get("web_haber"),
                "Web - Duyuru": deger.get("web_duyuru"),
                "Web - Not": deger.get("web_not"),
                "Genel Not": deger.get("genel_not")
            })
            
    if rapor_listesi:
        df_rapor = pd.DataFrame(rapor_listesi)
        df_rapor = df_rapor.sort_values(by="Tarih")
        
        st.markdown("---")
        st.subheader(f"📈 {rapor_ay} Ayı Performans Özeti")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        toplam_gonderi = len(df_rapor)
        toplam_begeni = int(df_rapor["Beğeni"].sum())
        toplam_yorum = int(df_rapor["Yorum"].sum())
        
        col_m1.metric("Toplam İçerik Sayısı", toplam_gonderi)
        col_m2.metric("Toplam Beğeni Sayısı", toplam_begeni)
        col_m3.metric("Toplam Yorum Sayısı", toplam_yorum)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.write("**Platformlara Göre İçerik Dağılım Grafiği**")
        platform_counts = df_rapor["Sosyal Medya Platform"].value_counts()
        if not platform_counts.empty:
            st.bar_chart(platform_counts)
        else:
            st.info("Bu ay için sosyal medya platformu verisi bulunmuyor.")
        
        st.markdown("---")
        st.subheader(f"📋 {rapor_ay} Ayı Detaylı Kayıt Tablosu")
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
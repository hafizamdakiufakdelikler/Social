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
    st.session_state.temp_preview = {"url": "", "title": "", "description": "", "image": None, "tags": ""}

platform_listesi = ["Instagram", "YouTube", "LinkedIn", "X", "Nsosyal", "Facebook"]
aylar_sabit = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# ==========================================
# AKILLI METİN VE ETİKET ANALİZ MOTORU
# ==========================================
def otomatik_etiket_uret(metin):
    if not metin or metin.strip() == "": return ""
    metin = metin.lower()
    kelimeler = re.findall(r'\b[a-zçğıöşü]{4,}\b', metin)
    stop_words = ["için", "göre", "tarafından", "hakkında", "ile", "veya", "olan", "olarak", "daha", "gibi", "kadar", "sonra", "önce", "üzere", "birlikte"]
    temiz_kelimeler = [k for k in kelimeler if k not in stop_words]
    en_cok_gecenler = [k[0] for k in Counter(temiz_kelimeler).most_common(4)]
    return ", ".join(en_cok_gecenler).title()

def get_link_preview(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        
        scrape_url = url
        if "x.com" in scrape_url or "twitter.com" in scrape_url:
            scrape_url = scrape_url.replace("x.com", "vxtwitter.com").replace("twitter.com", "vxtwitter.com")
            
        response = requests.get(scrape_url, headers=headers, timeout=8)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        
        if not og_title:
            fallback_title = soup.find("title")
            baslik = fallback_title.text.strip() if fallback_title else "Başlık bulunamadı"
        else:
            baslik = og_title["content"]
            
        if not og_desc:
            fallback_desc = soup.find("meta", attrs={"name": "description"})
            aciklama = fallback_desc["content"] if fallback_desc else "Açıklama bulunamadı"
        else:
            aciklama = og_desc["content"]
        
        oto_etiket = otomatik_etiket_uret(baslik + " " + aciklama)
        
        return {
            "title": baslik,
            "description": aciklama,
            "image": og_image["content"] if og_image else None,
            "tags": oto_etiket
        }
    except Exception:
        return None

# ==========================================
# SOL MENÜ (SIDEBAR)
# ==========================================
if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", use_container_width=True)

st.sidebar.title("🗂️ Yönetim Paneli")
ana_sekme = st.sidebar.radio("Menü Seçimi:", ["📝 Günlük Veri Girişi", "⚡ Anlık Özet Panosu", "📊 Aylık Rapor Merkezi"])

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
if ana_sekme == "📝 Günlük Veri Girişi":
    st.title("🚀 Medya ve İçerik Yönetim Paneli")
    
    secilen_tarih = st.date_input("📅 Kayıt Tarihi (Otomatik olarak bugünü gösterir, isterseniz geçmişi seçebilirsiniz):", datetime.today())
    
    secilen_ay = aylar_sabit[secilen_tarih.month - 1]
    secilen_gun = f"{str(secilen_tarih.day).zfill(2)} {secilen_ay}"

    st.markdown("---")
    st.header(f"📝 Veri Girişi: {secilen_kayit} ({secilen_gun})")

    mevcut_kayitlar = [x for x in st.session_state.veri_tabani if x.get("Tarih") == secilen_gun and x.get("Kayıt Adı") == secilen_kayit]
    if mevcut_kayitlar:
        with st.expander(f"📋 Seçili Güne Eklenen Mevcut Gönderiler ({len(mevcut_kayitlar)} Adet)", expanded=True):
            for idx, mk in enumerate(mevcut_kayitlar):
                col_rec_text, col_rec_del = st.columns([7, 1])
                with col_rec_text:
                    baslik = mk.get('baslik', '')
                    if baslik == "-" or not baslik: baslik = "Başlık Bulunamadı"
                    
                    if mk.get("Tür") == "Kişi/Kurum":
                        st.write(f"**{idx+1}. [{mk.get('platform')}]** *{baslik}*")
                    else:
                        st.write(f"**{idx+1}. [Haber/Duyuru]** 📰 *{baslik[:80]}...* | 🏷️ {mk.get('etiketler', '-')}")
                with col_rec_del:
                    if st.button("🗑️ Sil", key=f"del_{idx}_{mk.get('url', '')[:10]}"):
                        st.session_state.veri_tabani.remove(mk)
                        canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                        st.success("Kayıt buluttan silindi!")
                        st.rerun()

    st.subheader("➕ Yeni İçerik / Gönderi Ekle")
    
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
        with st.spinner("Yapay Zeka Linki Analiz Ediyor ve Etiket Üretiyor..."):
            preview = get_link_preview(g_url)
            if preview:
                st.session_state.temp_preview = {
                    "url": g_url, "title": preview["title"], "description": preview["description"], "image": preview["image"], "tags": preview["tags"]
                }
            else:
                st.session_state.temp_preview = {"url": g_url, "title": "Başlık bulunamadı", "description": "Açıklama bulunamadı", "image": None, "tags": ""}

    if st.session_state.temp_preview["title"] and g_url:
        st.markdown("#### 📋 Otomatik Çekilen İçerik Önizlemesi")
        col_img, col_txt = st.columns([1, 2])
        with col_img:
            if st.session_state.temp_preview["image"]:
                st.image(st.session_state.temp_preview["image"], use_container_width=True)
        with col_txt:
            st.subheader(st.session_state.temp_preview["title"])
            st.write(st.session_state.temp_preview["description"])

    if "👤" in kayit_turu:
        g_etiketler = st.text_input("🏷️ Kullanılan Etiketler (Otomatik Üretildi):", value=st.session_state.temp_preview["tags"])
        g_web_haber, g_web_duyuru, g_web_not = "-", "-", "-"
    else:
        col_e, col_n = st.columns(2)
        with col_e:
            g_etiketler = st.text_input("🏷️ Habere Dair Etiketler (AI Tarafından Üretildi):", value=st.session_state.temp_preview["tags"])
        with col_n:
            g_web_not = st.text_area("📝 Haberle İlgili Özel Notunuz:", height=68)
        
        g_web_haber = st.session_state.temp_preview["description"]
        g_web_duyuru = "-"

    st.markdown("---")
    g_genel_not = st.text_area("📌 Arşive veya raporlamaya eklemek istediğiniz genel notlar:", height=100)

    st.markdown("---")
    if st.button("💾 Bu Gönderiyi Google Sheets Bulutuna Kaydet", use_container_width=True):
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
            "baslik": st.session_state.temp_preview["title"], 
            "aciklama": st.session_state.temp_preview["description"],
            "etiketler": g_etiketler,
            "web_haber": g_web_haber, "web_duyuru": g_web_duyuru, "web_not": g_web_not, 
            "genel_not": g_genel_not
        }
        st.session_state.veri_tabani.append(yeni_kayit)
        canlı_veritabanı_kaydet(st.session_state.veri_tabani)
        st.session_state.temp_preview = {"url": "", "title": "", "description": "", "image": None, "tags": ""}
        st.success(f"🎉 Rapor başarıyla doğrudan Google Sheets dosyanıza işlendi!")
        st.rerun()

# ==========================================
# ANLIK CANLI ÖZET PANOSU VE GÜNLÜK PAYLAŞIM
# ==========================================
elif ana_sekme == "⚡ Anlık Özet Panosu":
    st.title("⚡ Anlık Kurumsal Performans Panosu")
    st.markdown("Bu sayfa sistemdeki **tüm zamanlara ait** verilerinizi anlık olarak analiz eder.")
    
    if st.session_state.veri_tabani:
        df_all = pd.DataFrame(st.session_state.veri_tabani)
        
        st.metric("Toplam Arşivlenen İçerik", len(df_all))
        
        st.markdown("---")
        col_grafik, col_son_eklenen = st.columns([1, 2])
        
        with col_grafik:
            st.subheader("📊 Platform Dağılımı")
            platform_dagilimi = df_all[df_all["Tür"] == "Kişi/Kurum"]["platform"].value_counts()
            if not platform_dagilimi.empty:
                st.bar_chart(platform_dagilimi)
            else:
                st.info("Grafik için yeterli sosyal medya verisi yok.")
                
        with col_son_eklenen:
            st.subheader("🆕 Sisteme Eklenen Son 5 İçerik")
            son_5 = df_all.tail(5)[["Tarih", "Kayıt Adı", "Tür", "baslik"]]
            son_5 = son_5.rename(columns={"baslik": "Başlık / İçerik"})
            st.dataframe(son_5, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📤 Günlük Toplu Link Paylaşım Modülü")
        st.write("Yöneticilerinize veya müşterilerinize o günkü tüm haberleri tek bir mesaj olarak göndermek için kullanabilirsiniz.")
        
        mevcut_tarihler = sorted(df_all["Tarih"].dropna().unique().tolist(), reverse=True)
        
        if mevcut_tarihler:
            secilen_paylasim_tarihi = st.selectbox("📅 Raporunu Almak İstediğiniz Günü Seçin:", mevcut_tarihler)
            gunluk_veriler = df_all[df_all["Tarih"] == secilen_paylasim_tarihi]
            
            if not gunluk_veriler.empty:
                mesaj_metni = f"📅 *{secilen_paylasim_tarihi} - Günlük Medya ve Haber Takip Raporu:*\n\n"
                
                for i, row in enumerate(gunluk_veriler.to_dict('records')):
                    tur = row.get("Tür", "")
                    plat = row.get("platform", "")
                    baslik = row.get("baslik", "Başlık Yok")
                    url = row.get("url", "-")
                    
                    if tur == "Kişi/Kurum":
                        mesaj_metni += f"*{i+1}. [{plat}]* {baslik}\n🔗 {url}\n\n"
                    else:
                        mesaj_metni += f"*{i+1}. [Haber/Duyuru]* {baslik}\n🔗 {url}\n\n"
                
                st.info("💡 Aşağıdaki siyah kutunun sağ üst köşesinde beliren 'Kopyala' simgesine basarak tüm listeyi tek tıkla kopyalayabilirsiniz.")
                st.code(mesaj_metni, language="text")
                
    else:
        st.info("Sistemde henüz analiz edilecek bir kayıt bulunmuyor.")

# ==========================================
# ANA EKRAN - AYLIK RAPORLAMA VE EXCEL CIKTI
# ==========================================
elif ana_sekme == "📊 Aylık Rapor Merkezi":
    st.title("📊 Aylık Raporlama ve Çıktı Merkezi")
    
    aylar_sabit_isimler = ["Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    rapor_ay = st.selectbox("🔍 Raporunu Görmek İstediğiniz Ayı Seçin:", aylar_sabit_isimler)
    
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
                "Etiketler": deger.get("etiketler", ""),
                "Web - Haber": deger.get("web_haber"),
                "Genel Not": deger.get("genel_not")
            })
            
    if rapor_listesi:
        df_rapor = pd.DataFrame(rapor_listesi)
        df_rapor = df_rapor.sort_values(by="Tarih")
        
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
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

st.set_page_config(page_title="RH+ Sosyal Medya Yönetim Paneli", layout="wide", page_icon="🚀")

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
                st.rerun()
            else:
                st.error("Hatalı şifre! Lütfen tekrar deneyin.")
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
    stop_words = ["için", "göre", "tarafından", "hakkında", "ile", "veya", "olan", "olarak", "daha", "gibi", "kadar", "sonra", "önce", "üzere", "birlikte"]
    temiz_kelimeler = [k for k in kelimeler if k not in stop_words]
    en_cok_gecenler = [k[0] for k in Counter(temiz_kelimeler).most_common(4)]
    return ", ".join(en_cok_gecenler).title()

def get_link_preview(url):
    try:
        url_lower = url.lower()
        detected_platform = "Diğer"
        if "instagram.com" in url_lower: detected_platform = "Instagram"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower: detected_platform = "YouTube"
        elif "linkedin.com" in url_lower: detected_platform = "LinkedIn"
        elif "x.com" in url_lower or "twitter.com" in url_lower: detected_platform = "X"
        elif "facebook.com" in url_lower: detected_platform = "Facebook"
        elif "nsosyal" in url_lower: detected_platform = "Nsosyal"

        # X (Twitter) İçin JSON API Çözümü (Güçlendirildi)
        if detected_platform == "X":
            api_url = url.replace("x.com", "api.vxtwitter.com").replace("twitter.com", "api.vxtwitter.com")
            api_url = api_url.split("?")[0]
            res = requests.get(api_url, timeout=8).json()
            
            baslik = f"@{res.get('user_screen_name', 'Kullanıcı')} (X Gönderisi)"
            aciklama = res.get('text', 'Açıklama bulunamadı')
            
            image_url = None
            if res.get('media_extended') and len(res['media_extended']) > 0:
                image_url = res['media_extended'][0].get('url')
                
            oto_etiket = otomatik_etiket_uret(aciklama)
            return {"title": baslik, "description": aciklama, "image": image_url, "tags": oto_etiket, "platform": detected_platform}

        # Diğer Siteler İçin Standart Çekim
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=8)
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
            "tags": oto_etiket,
            "platform": detected_platform
        }
    except Exception:
        return None

# ==========================================
# SOL MENÜ (SIDEBAR) - UX Temizliği Yapıldı
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
            yeni_kisi = st.text_input("➕ Yeni Kişi/Kurum Ekle:")
            if st.button("Kişiyi Ekle", use_container_width=True):
                if yeni_kisi and yeni_kisi not in st.session_state.sabit_listeler["kisiler"]:
                    st.session_state.sabit_listeler["kisiler"].append(yeni_kisi)
                    bulut_listelerini_kaydet(st.session_state.sabit_listeler)
                    st.toast("Yeni kişi listeye eklendi!", icon="🎉")
                    st.rerun()
        else:
            secilen_kayit = st.selectbox("Düzenlenecek Web Sitesi:", st.session_state.sabit_listeler["web_siteleri"])
            yeni_site_ismi = st.text_input("Seçili Siteyi Değiştir:", value=secilen_kayit)
            if st.button("🔄 Site İsmini Güncelle", use_container_width=True):
                if yeni_site_ismi and yeni_site_ismi != secilen_kayit:
                    idx = st.session_state.sabit_listeler["web_siteleri"].index(secilen_kayit)
                    st.session_state.sabit_listeler["web_siteleri"][idx] = yeni_site_ismi
                    bulut_listelerini_kaydet(st.session_state.sabit_listeler)
                    for entry in st.session_state.veri_tabani:
                        if entry.get("Kayıt Adı") == secilen_kayit and entry.get("Tür") == "Web Sitesi":
                            entry["Kayıt Adı"] = yeni_site_ismi
                    canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                    st.toast("Site ismi güncellendi!", icon="✅")
                    st.rerun()
            yeni_site = st.text_input("➕ Yeni Web Sitesi Ekle:")
            if st.button("Siteyi Ekle", use_container_width=True):
                if yeni_site and yeni_site not in st.session_state.sabit_listeler["web_siteleri"]:
                    st.session_state.sabit_listeler["web_siteleri"].append(yeni_site)
                    bulut_listelerini_kaydet(st.session_state.sabit_listeler)
                    st.toast("Yeni site listeye eklendi!", icon="🎉")
                    st.rerun()
else:
    # Diğer sayfalarda sol menü temiz kalması için değişkenleri dummy atıyoruz
    kayit_turu = "👤 Kişiler / Kuruluşlar"
    secilen_kayit = None

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Güvenli Çıkış", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# ==========================================
# ANA EKRAN - VERI GIRISI
# ==========================================
if ana_sekme == "📝 Günlük Veri Girişi":
    st.title("🚀 Medya ve İçerik Yönetim Paneli")
    st.markdown("Verilerinizi hızlı ve düzenli bir şekilde doğrudan bulut sisteminize kaydedin.")
    
    # UX Eklentisi: Yardımcı Tooltip
    secilen_tarih = st.date_input("📅 Kayıt Tarihi", datetime.today(), help="Sistem varsayılan olarak bugünü seçer. Geçmişteki bir gün için veri girmek istiyorsanız takvimden tarihi değiştirebilirsiniz.")
    secilen_ay = aylar_sabit[secilen_tarih.month - 1]
    secilen_gun = f"{str(secilen_tarih.day).zfill(2)} {secilen_ay}"

    st.markdown("---")
    
    # UX Eklentisi: Seçili Gün Metrik Kartı
    mevcut_kayitlar = [x for x in st.session_state.veri_tabani if x.get("Tarih") == secilen_gun and x.get("Kayıt Adı") == secilen_kayit]
    
    col_baslik, col_sayac = st.columns([3, 1])
    with col_baslik:
        st.header(f"📝 {secilen_kayit}")
        st.caption(f"İşlem yapılan tarih: **{secilen_gun}**")
    with col_sayac:
        st.metric(label="Bugün Girilen İçerik", value=len(mevcut_kayitlar), help="Seçtiğiniz tarihte bu kişi/kurum için girilen toplam veri sayısı.")

    if mevcut_kayitlar:
        with st.expander(f"📋 Bu Kayda Eklenen Mevcut Gönderiler ({len(mevcut_kayitlar)} Adet)", expanded=True):
            for idx, mk in enumerate(mevcut_kayitlar):
                col_rec_text, col_rec_del = st.columns([8, 1])
                with col_rec_text:
                    baslik = mk.get('baslik', '')
                    if baslik == "-" or not baslik: baslik = "Başlık Bulunamadı"
                    
                    if mk.get("Tür") == "Kişi/Kurum":
                        st.markdown(f"**{idx+1}. [{mk.get('platform')}]** *{baslik}*")
                    else:
                        st.markdown(f"**{idx+1}. [Haber/Duyuru]** 📰 *{baslik[:80]}...* | 🏷️ {mk.get('etiketler', '-')}")
                with col_rec_del:
                    if st.button("🗑️ Sil", key=f"del_{idx}_{mk.get('url', '')[:10]}", help="Bu kaydı veritabanından kalıcı olarak siler."):
                        st.session_state.veri_tabani.remove(mk)
                        canlı_veritabanı_kaydet(st.session_state.veri_tabani)
                        st.toast("Kayıt sistemden silindi.", icon="🗑️")
                        st.rerun()

    st.markdown("### ➕ Yeni İçerik Ekle")
    st.info("💡 Linki yapıştırdığınızda sistem platformu otomatik olarak tanır ve içeriği sizin için çeker.")
    
    g_url = st.text_input("🔗 Haber veya Gönderi Linki:", value="", placeholder="https://...", help="İlgili habere veya gönderiye ait tam linki buraya yapıştırın.")
        
    if g_url and g_url != st.session_state.temp_preview["url"]:
        with st.spinner("Yapay Zeka Devrede: Link Analiz Ediliyor..."):
            preview = get_link_preview(g_url)
            if preview:
                st.session_state.temp_preview = {
                    "url": g_url, "title": preview["title"], "description": preview["description"], "image": preview["image"], "tags": preview["tags"], "platform": preview["platform"]
                }
            else:
                st.session_state.temp_preview = {"url": g_url, "title": "İçerik Bulunamadı", "description": "Lütfen linki kontrol ediniz.", "image": None, "tags": "", "platform": "Web Sitesi"}

    # UX Eklentisi: Şık Önizleme Kartı
    if st.session_state.temp_preview["title"] and g_url:
        with st.container(border=True):
            st.markdown("#### 🤖 Otomatik Çekilen İçerik")
            col_img, col_txt = st.columns([1, 4])
            with col_img:
                if st.session_state.temp_preview["image"]:
                    st.image(st.session_state.temp_preview["image"], use_container_width=True)
                else:
                    st.markdown("*(Görsel Yok)*")
            with col_txt:
                if "👤" in kayit_turu:
                    st.markdown(f"**Tespit Edilen Platform:** `{st.session_state.temp_preview.get('platform', 'Hesaplanıyor...')}`")
                st.subheader(st.session_state.temp_preview["title"])
                st.caption(st.session_state.temp_preview["description"])

    if "👤" in kayit_turu:
        g_platform = st.session_state.temp_preview.get("platform", "Diğer")
        g_etiketler = st.text_input("🏷️ Etiketler (Otomatik Üretildi):", value=st.session_state.temp_preview["tags"], help="Yapay zeka tarafından haberden çıkarılan kelimeler. İsterseniz kendiniz de değiştirebilirsiniz.")
        g_web_haber, g_web_duyuru, g_web_not = "-", "-", "-"
    else:
        g_platform = "Web Sitesi"
        col_e, col_n = st.columns(2)
        with col_e:
            g_etiketler = st.text_input("🏷️ Etiketler:", value=st.session_state.temp_preview["tags"])
        with col_n:
            g_web_not = st.text_area("📝 Özel Notunuz:", height=68, placeholder="Haberin önemi veya iletilmek istenen not...")
        g_web_haber = st.session_state.temp_preview["description"]
        g_web_duyuru = "-"

    g_genel_not = st.text_area("📌 Genel Not (İsteğe Bağlı):", height=68, placeholder="Raporlarda görünmesi için bu gönderiyle ilgili eklemek istediğiniz notlar...", help="Bu alan raporlama ekranında görünecektir.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Kaydet ve Buluta Gönder", use_container_width=True, type="primary"):
        if g_url and g_url.strip() != "-" and g_url.strip() != "":
            temiz_url = g_url.strip().lower()
            kayitli_mi = any(kayit.get("url", "").strip().lower() == temiz_url for kayit in st.session_state.veri_tabani)
            if kayitli_mi:
                st.error("⚠️ DİKKAT: Bu URL zaten sistemde kayıtlı! Mükerrer kayıt engellendi.")
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
        st.session_state.temp_preview = {"url": "", "title": "", "description": "", "image": None, "tags": "", "platform": ""}
        
        # UX Eklentisi: Zarif Bildirim (Toast)
        st.toast("Rapor Google Sheets'e işlendi!", icon="✅")
        st.rerun()

# ==========================================
# ANLIK CANLI ÖZET PANOSU VE GÜNLÜK PAYLAŞIM
# ==========================================
elif ana_sekme == "⚡ Anlık Özet Panosu":
    st.title("⚡ Kurumsal Performans Panosu")
    st.markdown("Sistemdeki **tüm zamanlara ait** verilerin anlık analizini ve paylaşım modülünü burada bulabilirsiniz.")
    
    if st.session_state.veri_tabani:
        df_all = pd.DataFrame(st.session_state.veri_tabani)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Toplam Arşivlenen İçerik", len(df_all))
        
        st.markdown("---")
        col_grafik, col_son_eklenen = st.columns([1, 2])
        
        with col_grafik:
            st.subheader("📊 Platform Dağılımı")
            platform_dagilimi = df_all[df_all["Tür"] == "Kişi/Kurum"]["platform"].value_counts()
            if not platform_dagilimi.empty:
                st.bar_chart(platform_dagilimi)
            else:
                st.info("Grafik için veri yok.")
                
        with col_son_eklenen:
            st.subheader("🆕 Son Eklenen 5 İçerik")
            son_5 = df_all.tail(5)[["Tarih", "Kayıt Adı", "Tür", "baslik"]]
            son_5 = son_5.rename(columns={"baslik": "Başlık / İçerik"})
            st.dataframe(son_5, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📤 Günlük Toplu Link Paylaşım Modülü")
        st.caption("Yöneticilerinize veya müşterilerinize o günkü haberleri tek mesajda göndermek için (WhatsApp/E-Posta) uygundur.")
        
        mevcut_tarihler = sorted(df_all["Tarih"].dropna().unique().tolist(), reverse=True)
        
        if mevcut_tarihler:
            secilen_paylasim_tarihi = st.selectbox("📅 Paylaşım İçin Gün Seçin:", mevcut_tarihler)
            gunluk_veriler = df_all[df_all["Tarih"] == secilen_paylasim_tarihi]
            
            if not gunluk_veriler.empty:
                mesaj_metni = f"📅 *{secilen_paylasim_tarihi} - Günlük Medya Takip Raporu:*\n\n"
                
                for i, row in enumerate(gunluk_veriler.to_dict('records')):
                    tur = row.get("Tür", "")
                    plat = row.get("platform", "")
                    baslik = row.get("baslik", "Başlık Yok")
                    url = row.get("url", "-")
                    
                    if tur == "Kişi/Kurum":
                        mesaj_metni += f"*{i+1}. [{plat}]* {baslik}\n🔗 {url}\n\n"
                    else:
                        mesaj_metni += f"*{i+1}. [Haber/Duyuru]* {baslik}\n🔗 {url}\n\n"
                
                st.success("💡 Siyah kutunun sağ üst köşesindeki 'Kopyala' butonuna basarak tüm listeyi alabilirsiniz.")
                st.code(mesaj_metni, language="text")
                
    else:
        st.info("Sistemde henüz analiz edilecek kayıt bulunmuyor.")

# ==========================================
# ANA EKRAN - AYLIK RAPORLAMA VE EXCEL CIKTI
# ==========================================
elif ana_sekme == "📊 Aylık Rapor Merkezi":
    st.title("📊 Aylık Raporlama ve Çıktı Merkezi")
    st.markdown("Seçtiğiniz aya ait detaylı dökümleri görüntüleyin ve Excel olarak bilgisayarınıza indirin.")
    
    aylar_sabit_isimler = ["Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    rapor_ay = st.selectbox("🔍 Raporunu İncelemek İstediğiniz Ayı Seçin:", aylar_sabit_isimler)
    
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
        
        with st.container(border=True):
            st.subheader(f"📋 {rapor_ay} Ayı Kayıt Tablosu")
            st.dataframe(df_rapor, use_container_width=True, hide_index=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_rapor.to_excel(writer, sheet_name=rapor_ay, index=False)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                label=f"📥 {rapor_ay} Raporunu Excel Olarak İndir",
                data=buffer.getvalue(),
                file_name=f"{rapor_ay}_Medya_Takip_Raporu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
    else:
        st.info(f"{rapor_ay} ayına ait henüz veri girişi yapılmamış.")
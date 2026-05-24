import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from scanner import scan_username
from photo_analyzer import upload_to_catbox, get_exif_data, get_google_maps_url, generate_search_links
import os
import shutil
import yt_dlp
import re
import time
import imageio_ffmpeg
from flask import Flask
import threading

TOKEN = "7929116701:AAGSkYeqfVV5ZlcLFU24diufgA8qOsrgZoo"
bot = telebot.TeleBot(TOKEN)

# Flask Web Sunucusu (Bulutta 7/24 uyanık kalmak için)
app = Flask(__name__)

@app.route('/')
def home():
    return "Siber OSINT Botu 7/24 Aktif Olarak Çalışıyor!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# Global değişkenler
user_files = {}
url_extractor = re.compile(r'(https?://\S+)')
user_links = {}

# Yetkilendirme (Instagram Takip) Dosyası
AUTH_FILE = "authorized_users.txt"
if os.path.exists(AUTH_FILE):
    with open(AUTH_FILE, "r") as f:
        authorized_users = set(int(line.strip()) for line in f if line.strip().isdigit())
else:
    authorized_users = set()

def save_auth(user_id):
    authorized_users.add(user_id)
    with open(AUTH_FILE, "a") as f:
        f.write(f"{user_id}\n")

def check_auth(chat_id):
    if chat_id not in authorized_users:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📸 Instagram Hesabını Takip Et", url="https://instagram.com/yilmazavsar_21"))
        markup.add(InlineKeyboardButton("✅ Takip Ettim", callback_data="auth_verify"))
        bot.send_message(chat_id, "🛑 <b>DUR! ERİŞİM REDDEDİLDİ!</b>\n\nBu gizli Siber İstihbarat botunu kullanabilmek için öncelikle geliştiriciyi Instagram'da takip etmelisin.\n\n⚠️ <i>Takip etmeden 'Takip Ettim' tuşuna basanların erişimi kalıcı olarak engellenir.</i>", reply_markup=markup, parse_mode="HTML")
        return False
    return True

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not check_auth(message.chat.id): return
    welcome_text = (
        "🕵️‍♂️ <b>Siber İstihbarat (OSINT) Botuna Hoş Geldiniz!</b>\n\n"
        "Komut Sistemine Geçildi. Botu kullanmak için komut yazmalısınız:\n\n"
        "1️⃣ <b>İsim Analizi:</b> 38 platformda kullanıcı adı tarar.\n"
        "👉 <code>/isim elonmusk</code>\n\n"
        "2️⃣ <b>Yüz / Profil Bulucu:</b> Bir fotoğraf gönderin, Yandex ve Google üzerinden profillerini bulayım.\n\n"
        "3️⃣ <b>Adli Bilişim (EXIF):</b> Fotoğrafı <i>'Dosya (Belge)'</i> olarak atarsanız, çekildiği GPS konumunu çıkarırım.\n\n"
        "4️⃣ <b>Video İndirici (Yeni):</b> Instagram, TikTok, YouTube linkini doğrudan atarsanız filigransız indiririm!"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML")

@bot.message_handler(commands=['isim'])
def handle_isim_command(message):
    if not check_auth(message.chat.id): return
    # Kullanıcı sadece "/isim" yazmışsa uyar
    if len(message.text.split()) < 2:
        bot.send_message(message.chat.id, "❌ Lütfen komuttan sonra bir isim yazın. Örnek: `/isim elonmusk`", parse_mode="Markdown")
        return
        
    # Komuttan sonraki kısmı al ve boşlukları birleştir ("yılmaz avşar" -> "yılmazavşar")
    raw_text = message.text.replace("/isim", "").strip()
    username = raw_text.replace(" ", "")
    chat_id = message.chat.id
    
    # Kullanıcıya taramanın başladığını bildir
    msg = bot.send_message(chat_id, f"🔍 <code>{username}</code> adlı hedef için Küresel OSINT Taraması başlatıldı. Lütfen bekleyin...", parse_mode="HTML")
    
    try:
        # Asenkron tarayıcıyı çalıştır
        results = asyncio.run(scan_username(username))
        
        if not results:
            bot.edit_message_text(f"❌ <code>{username}</code> için hiçbir sonuç bulunamadı. (Belki bu kullanıcı adını kimse kullanmıyordur).", chat_id, msg.message_id, parse_mode="HTML")
            return
        
        # Sonuçları formatla (Siber Güvenlik Terminali Teması)
        report = "<b>[ OSINT TARAMA RAPORU ]</b>\n"
        report += f"👤 <b>Hedef:</b> <code>{username}</code>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for res in results:
            report += f"✅ <b>{res['site']}</b>\n"
            report += f"└ 🔗 <a href='{res['url']}'>Profile Git</a>\n\n"
            
        report += "━━━━━━━━━━━━━━━━━━━━\n"
        report += "🕵️‍♂️ <i>Tarama başarıyla tamamlandı.</i>"
        
        # Sonucu gönder
        bot.edit_message_text(report, chat_id, msg.message_id, parse_mode="HTML", disable_web_page_preview=True)
        
    except Exception as e:
        bot.edit_message_text(f"❌ Tarama sırasında bir hata oluştu: {str(e)}", chat_id, msg.message_id)

@bot.message_handler(content_types=['photo', 'document'])
def handle_photo(message):
    if not check_auth(message.chat.id): return
    chat_id = message.chat.id
    
    # Dosya türünü belirle
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id # En yüksek çözünürlüklü olanı al
        is_document = False
    elif message.content_type == 'document':
        # Sadece resim belgelerini kabul et
        if not message.document.mime_type.startswith('image/'):
            bot.send_message(chat_id, "❌ Lütfen belge olarak sadece resim dosyası gönderin.")
            return
        file_id = message.document.file_id
        is_document = True
        
    # Dosya bilgisini hafızaya kaydet
    user_files[message.message_id] = {'file_id': file_id, 'is_doc': is_document}
    
    # Butonlu menü oluştur
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📸 Yüz ve Profil Bulucu", callback_data=f"yuz_{message.message_id}"))
    markup.add(InlineKeyboardButton("🗺️ EXIF / Konum Analizi", callback_data=f"exif_{message.message_id}"))
    
    bot.reply_to(message, "⚙️ Fotoğraf alındı. Lütfen yapmak istediğiniz Siber Analiz türünü seçin:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "auth_verify":
        chat_id = call.message.chat.id
        save_auth(chat_id)
        bot.edit_message_text("✅ <b>DOĞRULAMA BAŞARILI!</b>\n\nTakip ettiğiniz için teşekkürler. Botun tüm Siber İstihbarat özellikleri sizin için açıldı. 🎉\n\nİşlem yapmak için <code>/start</code> yazabilir veya doğrudan özellikleri kullanmaya başlayabilirsiniz.", chat_id, call.message.message_id, parse_mode="HTML")
        return

    action, msg_id_str = call.data.split('_')
    msg_id = int(msg_id_str)
    
    # OSINT ve Fotoğraf İşlemleri
    if action in ['yuz', 'exif']:
        if msg_id not in user_files:
            bot.answer_callback_query(call.id, "❌ Fotoğrafın süresi dolmuş, lütfen tekrar gönderin.")
            return
            
        file_info_data = user_files[msg_id]
        file_id = file_info_data['file_id']
        is_doc = file_info_data['is_doc']
        
        bot.edit_message_text("⏳ Dosya indiriliyor, analiz başlatılıyor...", call.message.chat.id, call.message.message_id)
        
        try:
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            if action == 'yuz':
                bot.edit_message_text("🕵️‍♂️ <i>Yüz tanıma algoritmaları için anonim köprü oluşturuluyor...</i>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
                image_url = asyncio.run(upload_to_catbox(downloaded_file))
                
                if image_url:
                    report = "<b>[ OSINT GÖRSEL ANALİZ RAPORU ]</b>\n"
                    report += "━━━━━━━━━━━━━━━━━━━━\n"
                    report += "👁️ <b>Yüz ve Profil Eşleşmeleri Hazır</b>\n\n"
                    
                    links = generate_search_links(image_url)
                    for engine, link in links.items():
                        report += f"🔹 <b>{engine}</b>\n"
                        report += f"└ 🔗 <a href='{link}'>Taramayı Başlat</a>\n\n"
                        
                    report += "━━━━━━━━━━━━━━━━━━━━\n"
                    report += "💡 <i>İpucu: En net sonuçlar için Yandex'i kullanın.</i>"
                    
                    bot.edit_message_text(report, call.message.chat.id, call.message.message_id, parse_mode="HTML", disable_web_page_preview=True)
                else:
                    bot.edit_message_text("❌ <b>Sistem Hatası:</b> Resim sunucuya yüklenemedi.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
                    
            elif action == 'exif':
                if not is_doc:
                    bot.edit_message_text("❌ <b>HATA:</b> Telegram normal fotoğrafların konum verisini otomatik siler.\n\nKonum bulmak (EXIF) için fotoğrafı <b>'Dosya / Belge'</b> olarak atmalısınız!", call.message.chat.id, call.message.message_id, parse_mode="HTML")
                    return
                    
                bot.edit_message_text("🗺️ <i>EXIF ve GPS verileri aranıyor...</i>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
                exif_data = get_exif_data(downloaded_file)
                maps_url = get_google_maps_url(exif_data)
                
                report = "<b>[ ADLİ BİLİŞİM (FORENSICS) RAPORU ]</b>\n"
                report += "━━━━━━━━━━━━━━━━━━━━\n"
                
                if maps_url:
                    report += f"📍 <b>Konum Tespit Edildi!</b>\n"
                    report += f"└ 🔗 <a href='{maps_url}'>Haritada Aç</a>\n\n"
                    if exif_data.get('Model'): 
                        report += f"📱 <b>Cihaz:</b> <code>{exif_data.get('Model')}</code>\n"
                    if exif_data.get('DateTimeOriginal') or exif_data.get('DateTime'): 
                        report += f"⏰ <b>Zaman:</b> <code>{exif_data.get('DateTimeOriginal') or exif_data.get('DateTime')}</code>\n"
                else:
                    report += "❌ <b>Sonuç:</b> Fotoğrafın içinde GPS verisi bulunamadı (Veya silinmiş).\n"
                    
                report += "━━━━━━━━━━━━━━━━━━━━"
                bot.edit_message_text(report, call.message.chat.id, call.message.message_id, parse_mode="HTML", disable_web_page_preview=True)
                
        except Exception as e:
            bot.edit_message_text(f"❌ Analiz sırasında kritik hata: {str(e)}", call.message.chat.id, call.message.message_id)

    # Video İndirici Handler
    elif action in ['dlvideo', 'dlaudio']:
        chat_id = call.message.chat.id
        
        if chat_id not in user_links or not user_links[chat_id]:
            bot.edit_message_text("❌ Link süresi doldu, lütfen tekrar gönderin.", chat_id, call.message.message_id)
            return
            
        bot.edit_message_text("⏳ <i>İsteğiniz alındı, altyapı hazırlanıyor...</i>", chat_id, call.message.message_id, parse_mode="HTML")
        urls = user_links[chat_id]
        is_audio = action.startswith("dlaudio")
        
        for i, url in enumerate(urls):
            temp_dir = f"temp_downloads_{chat_id}_{call.message.message_id}_{i}"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            progress_msg = bot.send_message(chat_id, f"📥 İndiriliyor... Lütfen bekleyin.")
            
            last_edit_time = [time.time()]
            last_percentage = ["0%"]
            
            def my_hook(d):
                if d['status'] == 'downloading':
                    try:
                        percent = d.get('_percent_str', '0%').strip()
                        percent = re.sub(r'\x1b\[[0-9;]*m', '', percent)
                        
                        if percent != last_percentage[0] and time.time() - last_edit_time[0] > 3:
                            bot.edit_message_text(f"🚀 İndiriliyor: <b>{percent}</b>", chat_id, progress_msg.message_id, parse_mode="HTML")
                            last_edit_time[0] = time.time()
                            last_percentage[0] = percent
                    except Exception:
                        pass
                elif d['status'] == 'finished':
                    try:
                        bot.edit_message_text("⚡ <i>Sihir gerçekleşti! Telegram'a aktarılıyor...</i>", chat_id, progress_msg.message_id, parse_mode="HTML")
                    except:
                        pass
            
            try:
                ydl_opts = {
                    'outtmpl': os.path.join(temp_dir, '%(title)s_%(id)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'progress_hooks': [my_hook],
                    'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
                }
                
                if is_audio:
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                else:
                    ydl_opts['format'] = 'best'
                    
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    
                downloaded_files = os.listdir(temp_dir)
                if not downloaded_files:
                    bot.send_message(chat_id, "❌ Link indirilemedi.")
                    continue
                    
                for file_name in downloaded_files:
                    file_path = os.path.join(temp_dir, file_name)
                    ext = file_name.split('.')[-1].lower()
                    with open(file_path, 'rb') as f:
                        if is_audio:
                            bot.send_audio(chat_id, f, caption="✨ İndirildi (Siber OSINT Bot)")
                        elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                            bot.send_photo(chat_id, f, caption="📸")
                        else:
                            bot.send_video(chat_id, f, caption="🎬 (Siber OSINT Bot)", supports_streaming=True)
                            
                bot.delete_message(chat_id=chat_id, message_id=progress_msg.message_id)
                    
            except Exception as e:
                bot.send_message(chat_id, f"❌ Hata detayları: {str(e)}")
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
        if chat_id in user_links:
            del user_links[chat_id]

@bot.message_handler(func=lambda message: True)
def handle_unknown_text(message):
    if not check_auth(message.chat.id): return
    urls = url_extractor.findall(message.text)
    if urls:
        chat_id = message.chat.id
        user_links[chat_id] = urls
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🎬 Video Olarak İndir", callback_data=f"dlvideo_{message.message_id}"),
            InlineKeyboardButton("🎵 Sadece Müzik (MP3)", callback_data=f"dlaudio_{message.message_id}")
        )
        
        bot.reply_to(message, f"🔗 <b>Link tespit edildi!</b> Bu medyayı nasıl indirmek istersiniz?", reply_markup=markup, parse_mode="HTML")
        return

    bot.send_message(message.chat.id, "⚠️ <b>Yanlış Kullanım!</b>\n\nLütfen işlem yapmak için bir komut kullanın veya doğrudan link/resim gönderin.\nİsim taramak için: <code>/isim hedefine_yaz</code>", parse_mode="HTML")

if __name__ == "__main__":
    # Flask sunucusunu arka planda başlat (Bulut uyku modunu engellemek için)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🕵️‍♂️ OSINT Botu Bulut Uyumlu Olarak Başlatıldı...")
    bot.infinity_polling()

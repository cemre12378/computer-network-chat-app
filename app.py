from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from cryptography.fernet import Fernet
from database import Database
from collections import deque
from datetime import datetime, timezone, timedelta
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
import logging

logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('flask').setLevel(logging.ERROR)
logging.getLogger('flask.app').disabled = True

app = Flask(__name__)
app.logger.disabled = True
app.config['SECRET_KEY'] = 'secret_key_123'
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   ping_timeout=120,
                   ping_interval=25,
                   engineio_logger=False,
                   socketio_logger=False)

encryption_key = b'WfPJJzJwkDZr4XP0qLkOnIZxg32nKZ0PYWLdx2Xs6xA='
cipher = Fernet(encryption_key)

db = Database()

users = {}  # username → SID
users_by_sid = {}  # SID → username
user_sids = {}
message_ids = {}
waiting_users = deque()
online_users = set()  # Online olan kullanıcılar
user_public_keys = {}  # Kullanıcı public key'leri

# 🔐 Startup: Tüm users'ın public keys'ini load et
all_users = db.get_all_users()
for user in all_users:
    public_key = db.get_public_key(user)
    if public_key:
        user_public_keys[user] = public_key

# RSA Key Generation
def generate_rsa_keys():
    """RSA 2048 key pair oluştur"""
    key = RSA.generate(2048)
    private_key = key.export_key().decode()
    public_key = key.publickey().export_key().decode()
    return private_key, public_key

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print(f'🔗 Yeni bağlantı: {request.sid}')
    emit('response', {'data': 'Sunucuya bağlandınız'})

@socketio.on('register')
def handle_register(data):
    """Yeni kullanıcı kaydı"""
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    success, message = db.register_user(username, password)
    
    if success:
        print(f'✅ Kayıt: {username}')
        emit('register_response', {
            'success': True,
            'message': message
        })
    else:
        print(f'❌ Kayıt başarısız: {username} - {message}')
        emit('register_response', {
            'success': False,
            'message': message
        })

@socketio.on('login')
def handle_login(data):
    """Kullanıcı giriş"""
    global waiting_users
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    success, message = db.login_user(username, password)
    
    if not success:
        print(f'❌ Giriş başarısız: {username}')
        emit('login_response', {
            'success': False,
            'message': message
        })
        return
    
    # Giriş başarılı
    users[username] = request.sid
    users_by_sid[request.sid] = username
    user_sids[username] = request.sid
    print(f'👤 Giriş: {username}')
    
    # RSA key pair oluştur
    private_key, public_key = generate_rsa_keys()
    user_public_keys[username] = public_key
    
    # Database'ye kaydet
    db.save_public_key(username, public_key)
    print(f'🔐 RSA Keys: {username}')
    
    # Online listesine ekle
    online_users.add(username)
    print(f'🟢 Online: {username}')
    
    # Tüm kullanıcılara online listesini gönder
    emit('update_online_users', {
        'online_users': list(online_users)
    }, broadcast=True)
    
    auto_chat_partner = None
    
    if len(waiting_users) > 0:
        # Birisi bekliyor - otomatik sohbet aç!
        partner_data = waiting_users.popleft()
        partner = partner_data['username']
        partner_sid = partner_data['sid']
        
        auto_chat_partner = partner
        print(f'🔗 Otomatik Sohbet: {username} ↔ {partner}')
        
        # Partner'a yeni sohbetçi bulduğunu söyle
        emit('partner_found', {'partner': username}, to=partner_sid)
        
        # Her ikisine sohbeti başlat
        emit('load_conversations', {
            'conversations': db.get_user_conversations(partner),
            'online_users': list(online_users - {partner}),
            'auto_chat': username
        }, to=partner_sid)
    else:
        # Bekle
        waiting_users.append({
            'username': username,
            'sid': request.sid
        })
        print(f'⏳ {username} beklemede...')
    
    emit('user_joined', {
        'username': username,
        'message': f'{username} sohbete katıldı 👋'
    }, broadcast=True)
    
    # Kullanıcıya kendi sohbetlerini gönder ve login başarısını haber ver
    emit('login_response', {
        'success': True,
        'message': '✅ Giriş başarılı!',
        'my_private_key': private_key,
        'public_keys': user_public_keys  # Tüm users' public keys (online + offline)
    })
    
    # Tüm users'a yeni user'ın public key'ini gönder (update)
    emit('new_user_public_key', {
        'username': username,
        'public_key': public_key
    }, broadcast=True)
    
    emit('load_conversations', {
        'conversations': db.get_user_conversations(username),
        'online_users': list(online_users - {username}),
        'auto_chat': auto_chat_partner
    })

@socketio.on('message')
def handle_message(data):
    sender = users_by_sid.get(request.sid, 'User')
    recipient = data.get('recipient')
    message = data['message']
    
    if not recipient:
        print(f"❌ Alıcı belirtilmedi!")
        return
    
    print(f'🔐 Encrypted Mesaj: {sender} → {recipient} (Server Decrypt ETMEYİ)')
    
    timestamp = datetime.now(timezone(timedelta(hours=3))).strftime('%H:%M')  # Türkiye Saati (UTC+3)
    
    try:
        message_id = db.save_message(sender, recipient, message)
        message_ids[request.sid] = message_id
    except Exception as e:
        print(f"❌ Database hatası: {e}")
        message_id = None
    
    # ✅ Her zaman sender'a gönder (kendi mesajını görsün)
    emit('message', {
        'username': sender,
        'message': message,
        'message_id': message_id,
        'status': 'sent',
        'recipient': recipient,
        'timestamp': timestamp,
        'cache_key': data.get('cache_key')  # Cache key'i gönder
    })
    
    # ✅ Recipient online ise, gönder
    if recipient in user_sids:
        recipient_sid = user_sids[recipient]
        socketio.emit('message', {
            'username': sender,
            'message': message,
            'message_id': message_id,
            'status': 'sent',
            'recipient': recipient,
            'timestamp': timestamp,
            'cache_key': data.get('cache_key')  # Cache key'i gönder
        }, to=recipient_sid)
    else:
        print(f"⏳ {recipient} offline - Database'de kaydedildi")
    
    # Message status
    emit('message_status', {
        'message_id': message_id,
        'status': 'delivered'
    }, broadcast=True, skip_sid=request.sid)

@socketio.on('message_read')
def handle_message_read(data):
    message_id = data.get('message_id')
    if message_id:
        db.update_message_status(message_id, 'read')
        emit('message_status', {
            'message_id': message_id,
            'status': 'read'
        }, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    """Yazıyor göstergesi gönder"""
    sender = users_by_sid.get(request.sid, 'User')
    recipient = data.get('recipient')
    
    if recipient and recipient in user_sids:
        recipient_sid = user_sids[recipient]
        emit('typing', {
            'username': sender
        }, to=recipient_sid)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    """Yazıyor göstergesi kapat"""
    recipient = data.get('recipient')
    
    if recipient and recipient in user_sids:
        recipient_sid = user_sids[recipient]
        emit('stop_typing', {}, to=recipient_sid)

@socketio.on('get_conversation_messages')
def handle_get_conversation_messages(data):
    username = users_by_sid.get(request.sid, 'User')
    other_user = data['other_user']
    
    messages = db.get_conversation_messages(username, other_user)
    
    emit('conversation_messages', {
        'other_user': other_user,
        'messages': messages
    })

@socketio.on('get_public_key')
def handle_get_public_key(data):
    """Public key talep et"""
    requested_user = data.get('username')
    
    if requested_user and requested_user in user_public_keys:
        print(f'🔐 Public Key Gönderiliyor: {requested_user}')
        emit('new_user_public_key', {
            'username': requested_user,
            'public_key': user_public_keys[requested_user]
        })
    else:
        print(f'⚠️ Public Key Bulunamadı: {requested_user}')

@socketio.on('delete_conversation')
def handle_delete_conversation(data):
    username = users.get(request.sid, 'User')
    other_user = data['user']
    
    # Database'den sil
    db.delete_conversation(username, other_user)
    print(f'🗑️ Sohbet silindi: {username} - {other_user}')
    
    emit('conversation_deleted', {
        'user': other_user
    })

@socketio.on('disconnect')
def handle_disconnect():
    global waiting_users
    username = None
    
    # users_by_sid'den username bul ve sil
    if request.sid in users_by_sid:
        username = users_by_sid.pop(request.sid)
    
    # users'dan da sil
    if username and username in users:
        users.pop(username)
    
    # Waiting listesinden sil
    waiting_users = deque([u for u in waiting_users if u['username'] != username])
    
    if username and username != 'User':
        user_sids.pop(username, None)
        online_users.discard(username)  # Online listesinden çıkar
        print(f'⚫ Offline: {username}')
        print(f'⚫ Online Users Set: {online_users}')  # DEBUG
        
        # Tüm kullanıcılara offline statusunu gönder
        emit('update_online_users', {
            'online_users': list(online_users)
        }, broadcast=True)
        print(f'📤 Broadcast Online Users: {list(online_users)}')  # DEBUG
        
        emit('user_left', {
            'username': username,
            'message': f'{username} ayrıldı 👋'
        }, broadcast=True)
    else:
        user_sids.pop('User', None)

if __name__ == '__main__':
    print('✅ Database başlatıldı!')
    print('🌐 Web Chat Server Başlıyor...')
    print('🔐 Şifreleme: AÇIK')
    print('📱 Browser: http://localhost:5001')
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5001, use_reloader=False)
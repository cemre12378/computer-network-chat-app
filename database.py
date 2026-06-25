import sqlite3
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_name='chat.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Veritabanını başlat"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                public_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'sent',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database başlatıldı!")
    
    def add_user(self, username, password="default"):
        """Yeni kullanıcı ekle"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            print(f"❌ Kullanıcı '{username}' zaten var!")
            return False
    
    def register_user(self, username, password):
        """Yeni kullanıcı kaydet (şifreli)"""
        if not username or not password:
            return False, "Kullanıcı adı ve şifre boş olamaz!"
        
        if len(username) < 3:
            return False, "Kullanıcı adı en az 3 karakter olmalı!"
        
        if len(password) < 4:
            return False, "Şifre en az 4 karakter olmalı!"
        
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
            conn.close()
            return True, "✅ Kayıt başarılı!"
        except sqlite3.IntegrityError:
            return False, "❌ Bu kullanıcı adı zaten var!"
        except Exception as e:
            return False, f"❌ Hata: {str(e)}"
    
    def login_user(self, username, password):
        """Kullanıcı giriş kontrol et"""
        if not username or not password:
            return False, "Kullanıcı adı ve şifre boş olamaz!"
        
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            
            if result is None:
                return False, "❌ Kullanıcı bulunamadı!"
            
            if check_password_hash(result[0], password):
                return True, "✅ Giriş başarılı!"
            else:
                return False, "❌ Şifre yanlış!"
        except Exception as e:
            return False, f"❌ Hata: {str(e)}"
    
    def user_exists(self, username):
        """Kullanıcı var mı kontrol et"""
        return self.get_user(username) is not None
    
    def get_user(self, username):
        """Kullanıcı bilgisini al"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def save_public_key(self, username, public_key):
        """Kullanıcının public key'ini kaydet"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET public_key = ? WHERE username = ?",
                (public_key, username)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Public key kaydedilemedi: {e}")
            return False
    
    def get_public_key(self, username):
        """Kullanıcının public key'ini al"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT public_key FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] else None
        except Exception as e:
            print(f"❌ Public key alınamadı: {e}")
            return None

    def save_message(self, sender, recipient, message):
        """Mesajı veritabanına kaydet (sender ve recipient ile)"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            # Türkiye saati (UTC+3)
            tr_time = datetime.now(timezone(timedelta(hours=3))).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                "INSERT INTO messages (sender, recipient, message, status, timestamp) VALUES (?, ?, ?, ?, ?)",
                (sender, recipient, message, 'sent', tr_time)
            )
            conn.commit()
            message_id = cursor.lastrowid
            conn.close()
            return message_id
        except Exception as e:
            print(f"❌ Mesaj kaydedilemedi: {e}")
            return None
    
    def update_message_status(self, message_id, status):
        """Mesaj durumunu güncelle (sent, delivered, read)"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE messages SET status = ? WHERE id = ?",
                (status, message_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Mesaj durumu güncellenemedi: {e}")
            return False
    
    def get_messages(self, limit=50):
        """Son mesajları al"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sender, message, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        messages = cursor.fetchall()
        conn.close()
        return messages
    
    def get_all_users(self):
        """Tüm kullanıcıları al"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users")
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]
    
    def delete_user(self, username):
        """Kullanıcıyı sil"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Kullanıcı silinemedi: {e}")
            return False
    
    def get_user_conversations(self, username):
        """Kullanıcının konuşma yaptığı kişileri al"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT 
                    CASE 
                        WHEN sender = ? THEN recipient
                        ELSE sender
                    END as other_user
                FROM messages 
                WHERE sender = ? OR recipient = ?
                ORDER BY timestamp DESC
            """, (username, username, username))
            conversations = [row[0] for row in cursor.fetchall()]
            conn.close()
            return list(dict.fromkeys(conversations))
        except Exception as e:
            print(f"❌ Konuşma listesi hatası: {e}")
            return []
    
    def get_conversation_messages(self, user1, user2):
        """İki kullanıcı arasındaki mesajları al"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sender, message, status, timestamp FROM messages 
                WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
                ORDER BY timestamp ASC
            """, (user1, user2, user2, user1))
            messages = cursor.fetchall()
            conn.close()
            return messages
        except Exception as e:
            print(f"❌ Konuşma mesajları hatası: {e}")
            return []
    
    def delete_conversation(self, user1, user2):
        """İki kullanıcı arasındaki sohbeti sil"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM messages 
                WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
            """, (user1, user2, user2, user1))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Sohbet silinemedi: {e}")
            return False

if __name__ == "__main__":
    db = Database()
    print("✅ Database test başarılı!")
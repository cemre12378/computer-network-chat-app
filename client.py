import socket
import threading
import sys
from cryptography.fernet import Fernet

class ChatClient:
    def __init__(self, host='localhost', port=5002):
        self.host = host
        self.port = port
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = ""
        
        # Şifreleme anahtarı
        self.encryption_key = b'WfPJJzJwkDZr4XP0qLkOnIZxg32nKZ0PYWLdx2Xs6xA='
        self.cipher = Fernet(self.encryption_key)
    
    def connect(self):
        """Sunucuya bağlan"""
        try:
            self.client.connect((self.host, self.port))
            print(f"✅ Sunucuya bağlandı: {self.host}:{self.port}")
            print(f"🔐 Şifreleme: AÇIK")
            return True
        except Exception as e:
            print(f"❌ Bağlantı başarısız: {e}")
            return False
    
    def get_username(self):
        """Kullanıcı adı iste"""
        self.username = input("Kullanıcı adınız: ").strip()
        if not self.username:
            self.username = "User"
    
    def receive_messages(self):
        """Sunucudan şifreli mesaj al"""
        while True:
            try:
                encrypted_message = self.client.recv(1024)
                if encrypted_message:
                    try:
                        # Deşifreleme
                        message = self.cipher.decrypt(encrypted_message).decode('utf-8')
                        print(f"\n📨 {message}")
                        print(f"{self.username} > ", end='', flush=True)
                    except Exception as e:
                        print(f"\n❌ Deşifreleme hatası: {e}")
            except:
                break
    
    def send_messages(self):
        """Sunucuya şifreli mesaj gönder"""
        while True:
            try:
                message = input(f"{self.username} > ").strip()
                if message:
                    full_message = f"{self.username}: {message}"
                    # Şifreleme
                    encrypted_message = self.cipher.encrypt(full_message.encode('utf-8'))
                    self.client.send(encrypted_message)
            except KeyboardInterrupt:
                print("\n❌ Bağlantı kesildi")
                self.client.close()
                break
            except Exception as e:
                print(f"❌ Hata: {e}")
                break
    
    def start(self):
        """Client'i başlat"""
        if not self.connect():
            return
        
        self.get_username()
        
        # Mesaj almayı başlat (arka planda)
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        # Mesaj gönder (ana thread)
        self.send_messages()

if __name__ == "__main__":
    client = ChatClient(port=5002)
    client.start()
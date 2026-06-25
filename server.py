import socket
import threading
from cryptography.fernet import Fernet
from database import Database

class ChatServer:
    def __init__(self, host='0.0.0.0', port=5002):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.lock = threading.Lock()
        self.db = Database()
        
        # Şifreleme anahtarı
        self.encryption_key = b'WfPJJzJwkDZr4XP0qLkOnIZxg32nKZ0PYWLdx2Xs6xA='
        self.cipher = Fernet(self.encryption_key)
    
    def start(self):
        """Sunucuyu başlat"""
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print(f"✅ Server başladı: {self.host}:{self.port}")
        print(f"🔐 Şifreleme: AÇIK")
        print(f"🌐 Tüm ağ arabirimlerinde dinleniyor")
        print(f"📱 İstemciler bu sunucuya bağlanabilir")
        
        try:
            while True:
                client, address = self.server.accept()
                print(f"🔗 Yeni bağlantı: {address}")
                self.clients.append(client)
                threading.Thread(target=self.handle_client, args=(client, address)).start()
        except KeyboardInterrupt:
            print("\n❌ Server kapatıldı")
            self.server.close()
    
    def handle_client(self, client, address):
        """Her client'i yönet"""
        try:
            while True:
                encrypted_message = client.recv(1024)
                if encrypted_message:
                    try:
                        # Mesajı deşifreleme
                        message = self.cipher.decrypt(encrypted_message).decode('utf-8')
                        print(f"📨 Mesaj: {message}")
                        self.broadcast(encrypted_message, client)
                        self.save_message(message)
                    except Exception as e:
                        print(f"❌ Deşifreleme hatası: {e}")
                else:
                    break
        except Exception as e:
            print(f"❌ Hata: {e}")
        finally:
            with self.lock:
                if client in self.clients:
                    self.clients.remove(client)
            client.close()
            print(f"❌ Bağlantı kesildi: {address}")
    
    def broadcast(self, encrypted_message, sender):
        """Tüm client'lere şifreli mesaj gönder"""
        with self.lock:
            for client in self.clients:
                if client != sender:
                    try:
                        client.send(encrypted_message)
                    except:
                        pass
    
    def save_message(self, message):
        """Mesajı veritabanına kaydet"""
        self.db.save_message('User', message)

if __name__ == "__main__":
    server = ChatServer()
    server.start()
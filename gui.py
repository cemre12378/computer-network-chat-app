import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import socket
import threading
from cryptography.fernet import Fernet

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Chat Application")
        self.root.geometry("600x500")
        self.root.configure(bg='#2b2b2b')
        
        self.client_socket = None
        self.username = ""
        self.connected = False
        
        # Şifreleme anahtarı
        self.encryption_key = b'WfPJJzJwkDZr4XP0qLkOnIZxg32nKZ0PYWLdx2Xs6xA='
        self.cipher = Fernet(self.encryption_key)
        
        self.setup_login_screen()
    
    def setup_login_screen(self):
        """Login ekranı oluştur"""
        self.login_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.login_frame.pack(expand=True)
        
        # Başlık
        title = tk.Label(
            self.login_frame,
            text="💬 CHAT UYGULAMASI 🔐",
            font=("Arial", 20, "bold"),
            bg='#2b2b2b',
            fg='#00ff00'
        )
        title.pack(pady=20)
        
        # Username Label
        user_label = tk.Label(
            self.login_frame,
            text="Kullanıcı Adı:",
            font=("Arial", 12),
            bg='#2b2b2b',
            fg='white'
        )
        user_label.pack(pady=5)
        
        # Username Entry
        self.username_entry = tk.Entry(
            self.login_frame,
            font=("Arial", 12),
            width=20
        )
        self.username_entry.pack(pady=5)
        self.username_entry.focus()
        
        # Host Label
        host_label = tk.Label(
            self.login_frame,
            text="Sunucu (localhost):",
            font=("Arial", 10),
            bg='#2b2b2b',
            fg='white'
        )
        host_label.pack(pady=5)
        
        # Host Entry
        self.host_entry = tk.Entry(
            self.login_frame,
            font=("Arial", 10),
            width=20
        )
        self.host_entry.insert(0, "localhost")
        self.host_entry.pack(pady=5)
        
        # Port Label
        port_label = tk.Label(
            self.login_frame,
            text="Port (5002):",
            font=("Arial", 10),
            bg='#2b2b2b',
            fg='white'
        )
        port_label.pack(pady=5)
        
        # Port Entry
        self.port_entry = tk.Entry(
            self.login_frame,
            font=("Arial", 10),
            width=20
        )
        self.port_entry.insert(0, "5002")
        self.port_entry.pack(pady=5)
        
        # Bağlan Butonu
        connect_btn = tk.Button(
            self.login_frame,
            text="🔗 BAĞLAN",
            font=("Arial", 12, "bold"),
            bg='#00ff00',
            fg='black',
            command=self.connect_to_server,
            width=20
        )
        connect_btn.pack(pady=20)
    
    def connect_to_server(self):
        """Sunucuya bağlan"""
        self.username = self.username_entry.get().strip()
        host = self.host_entry.get().strip()
        port = int(self.port_entry.get().strip())
        
        if not self.username:
            messagebox.showerror("Hata", "Lütfen kullanıcı adı girin!")
            return
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.connected = True
            
            self.login_frame.destroy()
            self.setup_chat_screen()
            
            # Mesaj almayı başlat
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Bağlantı Hatası", f"Sunucuya bağlanılamadı:\n{e}")
    
    def setup_chat_screen(self):
        """Chat ekranı oluştur"""
        # Üst bar
        top_bar = tk.Frame(self.root, bg='#1a1a1a')
        top_bar.pack(fill=tk.X, padx=10, pady=10)
        
        status_text = f"✅ Bağlandı: {self.username} @ localhost:5002 🔐"
        status_label = tk.Label(
            top_bar,
            text=status_text,
            font=("Arial", 10, "bold"),
            bg='#1a1a1a',
            fg='#00ff00'
        )
        status_label.pack(side=tk.LEFT)
        
        # Mesaj gösterim alanı
        self.message_display = scrolledtext.ScrolledText(
            self.root,
            font=("Arial", 11),
            bg='#1a1a1a',
            fg='#00ff00',
            height=20,
            state=tk.DISABLED
        )
        self.message_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Input frame
        input_frame = tk.Frame(self.root, bg='#2b2b2b')
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Mesaj giriş kutusu
        self.message_input = tk.Entry(
            input_frame,
            font=("Arial", 11),
            bg='#3a3a3a',
            fg='white',
            insertbackground='white'
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.message_input.bind('<Return>', lambda e: self.send_message())
        
        # Gönder butonu
        send_btn = tk.Button(
            input_frame,
            text="📤 GÖNDER",
            font=("Arial", 10, "bold"),
            bg='#00ff00',
            fg='black',
            command=self.send_message,
            width=10
        )
        send_btn.pack(side=tk.RIGHT, padx=5)
    
    def send_message(self):
        """Şifreli mesaj gönder"""
        message = self.message_input.get().strip()
        
        if not message:
            return
        
        try:
            full_message = f"{self.username}: {message}"
            # Şifreleme
            encrypted_message = self.cipher.encrypt(full_message.encode('utf-8'))
            self.client_socket.send(encrypted_message)
            
            # Kendi mesajını göster
            self.display_message(f"Sen: {message}", "#00ff00")
            
            self.message_input.delete(0, tk.END)
            self.message_input.focus()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Mesaj gönderilemedi: {e}")
    
    def receive_messages(self):
        """Sunucudan şifreli mesaj al"""
        while self.connected:
            try:
                encrypted_message = self.client_socket.recv(1024)
                if encrypted_message:
                    try:
                        # Deşifreleme
                        message = self.cipher.decrypt(encrypted_message).decode('utf-8')
                        self.display_message(message, "#ff6b6b")
                    except Exception as e:
                        print(f"Deşifreleme hatası: {e}")
            except:
                self.connected = False
                break
    
    def display_message(self, message, color):
        """Mesajı ekranda göster"""
        self.message_display.config(state=tk.NORMAL)
        self.message_display.insert(tk.END, f"{message}\n")
        self.message_display.tag_add("color", "end-2c linestart", "end-1c")
        self.message_display.tag_config("color", foreground=color)
        self.message_display.see(tk.END)
        self.message_display.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()
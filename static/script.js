const socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5
});
let username = '';
let isLoggedIn = false;
let messageStatuses = {};
let currentChat = null;
let conversations = [];
let sentMessagesCache = {};  // 🔐 Cache: Gönderilen plaintext mesajlar
let typingTimeout = null;  // 📝 Typing indicator timeout
 
// 🔐 RSA Encryption Variables
let myPrivateKey = '';
let publicKeys = {};  // Diğer users' public keys
const encrypt = new JSEncrypt();
const decrypt = new JSEncrypt();
 
// Socket reconnect durumunu handle et
socket.on('disconnect', function() {
    console.log('⚫ Socket kesildi');
    isLoggedIn = false;  // Logout state
});
 
socket.on('reconnect', function() {
    console.log('🔗 Socket yeniden bağlandı');
    // Eğer login olmuşsa, tekrar login yap
    if (isLoggedIn && username) {
        console.log(`🔄 Yeniden login: ${username}`);
        // Login bilgilerini kaydetmemiş olabiliriz, o yüzden emit edelim
        // Ama sorun: Password yok. Alternatif: Server'a tekrar login istesini gönder
        // Şimdilik: Reload sayfayı (basit çözüm)
        // location.reload();
    }
});
 
// 🔐 Yeni user login olunca public key'i al
socket.on('new_user_public_key', function(data) {
    console.log(`🔐 Yeni Public Key Alındı: ${data.username}`);
    publicKeys[data.username] = data.public_key;
});
 
function toggleAuthForm() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    loginForm.style.display = loginForm.style.display === 'none' ? 'block' : 'none';
    registerForm.style.display = registerForm.style.display === 'none' ? 'block' : 'none';
    
    // İçeriği temizle
    document.getElementById('loginUsername').value = '';
    document.getElementById('loginPassword').value = '';
    document.getElementById('registerUsername').value = '';
    document.getElementById('registerPassword').value = '';
    document.getElementById('registerPasswordConfirm').value = '';
    document.getElementById('loginMessage').innerHTML = '';
    document.getElementById('registerMessage').innerHTML = '';
    
    // Focus ayarla
    if (loginForm.style.display === 'none') {
        document.getElementById('registerUsername').focus();
    } else {
        document.getElementById('loginUsername').focus();
    }
}
 
function showMessage(elementId, message, isError = false) {
    const msgEl = document.getElementById(elementId);
    msgEl.innerHTML = message;
    msgEl.className = 'message-box ' + (isError ? 'error' : 'success');
}
 
function register() {
    const username = document.getElementById('registerUsername').value.trim();
    const password = document.getElementById('registerPassword').value.trim();
    const passwordConfirm = document.getElementById('registerPasswordConfirm').value.trim();
    
    if (!username) {
        showMessage('registerMessage', '❌ Lütfen kullanıcı adı girin!', true);
        return;
    }
    
    if (!password) {
        showMessage('registerMessage', '❌ Lütfen şifre girin!', true);
        return;
    }
    
    if (password !== passwordConfirm) {
        showMessage('registerMessage', '❌ Şifreler eşleşmiyor!', true);
        return;
    }
    
    showMessage('registerMessage', '⏳ Kaydediliyor...', false);
    
    socket.emit('register', {
        username: username,
        password: password
    });
}
 
socket.on('register_response', function(data) {
    if (data.success) {
        showMessage('registerMessage', '✅ Kayıt başarılı! Giriş yapabilirsiniz.', false);
        
        // 1.5 saniye sonra login formuna geç
        setTimeout(() => {
            if (document.getElementById('registerForm').style.display !== 'none') {
                toggleAuthForm();
                document.getElementById('loginUsername').focus();
            }
        }, 1500);
    } else {
        showMessage('registerMessage', data.message, true);
    }
});
 
function login() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    
    if (!username) {
        showMessage('loginMessage', '❌ Lütfen kullanıcı adı girin!', true);
        return;
    }
    
    if (!password) {
        showMessage('loginMessage', '❌ Lütfen şifre girin!', true);
        return;
    }
    
    showMessage('loginMessage', '⏳ Giriş yapılıyor...', false);
    
    socket.emit('login', { 
        username: username,
        password: password
    });
}
 
socket.on('login_response', function(data) {
    if (data.success) {
        username = document.getElementById('loginUsername').value.trim();
        showMessage('loginMessage', '✅ ' + data.message, false);
        
        // 🔐 RSA Keys'i al
        myPrivateKey = data.my_private_key;
        publicKeys = data.public_keys || {};
        
        // Decrypt instance'ına private key yükle
        decrypt.setPrivateKey(myPrivateKey);
        
        console.log('🔐 RSA Keys Yüklendi');
        console.log('🔑 My Public Key:', publicKeys[username]);
        
        // 500ms sonra arayüzü göster
        setTimeout(() => {
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('chatSection').style.display = 'flex';
            document.getElementById('currentUser').textContent = username;
            document.getElementById('messageInput').focus();
            isLoggedIn = true;
        }, 500);
    } else {
        showMessage('loginMessage', data.message, true);
    }
});
 
function getStatusIcon(status) {
    return '✓✓';
}
 
function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
 
    if (!message) return;
    
    if (!currentChat) {
        alert('Lütfen bir sohbet seçin!');
        return;
    }
 
    // 🔐 Receiver'ın public key'i ile mesajı encrypt et
    const receiverPublicKey = publicKeys[currentChat];
    if (!receiverPublicKey) {
        alert('Hata: Alıcının public key bulunamadı!');
        return;
    }
    
    // Encrypt instance'ına receiver'ın public key'ini yükle
    encrypt.setPublicKey(receiverPublicKey);
    const encryptedMessage = encrypt.encrypt(message);
    
    console.log(`🔐 Şifreli mesaj gönderiliyor: ${currentChat}`);
 
    // 🔐 Plaintext mesajı cache'de tut (gönderici görsün)
    const cacheKey = `${currentChat}-${Date.now()}`;
    sentMessagesCache[cacheKey] = message;
 
    socket.emit('message', { 
        message: encryptedMessage,  // Şifreli mesaj gönder!
        recipient: currentChat,
        cache_key: cacheKey  // Cache key'i gönder
    });
    
    // Yazıyor göstergesi kapat
    socket.emit('stop_typing', {
        recipient: currentChat
    });
    
    messageInput.value = '';
    messageInput.focus();
    
    // Mesajlar socket.on('message') event'i ile zaten gelecek
}
 
function logout() {
    // Socket bağlantısını kes
    socket.disconnect();
    
    // Sayfayı yenile (tüm state reset + socket fresh bağlantı)
    setTimeout(() => {
        location.reload();
    }, 500);
}
 
// Yazma göstergesi
const messageInput = document.getElementById('messageInput');
 
if (messageInput) {
    messageInput.addEventListener('input', function() {
        if (!currentChat) return;
        
        // Yazıyor göstergesi gönder
        socket.emit('typing', {
            recipient: currentChat,
            status: true
        });
        
        // Timeout temizle
        clearTimeout(typingTimeout);
        
        // 3 saniye yazmazsa yazma durumunu kapat
        typingTimeout = setTimeout(() => {
            socket.emit('stop_typing', {
                recipient: currentChat
            });
        }, 3000);
    });
}
 
socket.on('message', function(data) {
    const isForMe = data.recipient === username;
    const isSentByMe = data.username === username;
    const isInCurrentChat = currentChat === data.username || currentChat === data.recipient;
    
    if (!isForMe && !isSentByMe && !isInCurrentChat) {
        return;
    }
    
    // Yazıyor göstergesi kapat
    removeTypingIndicator();
    
    // 🔐 Mesajı göster
    let displayMessage = data.message;
    
    if (isSentByMe) {
        // Kendi mesajım - cache'den plaintext al
        if (data.cache_key && sentMessagesCache[data.cache_key]) {
            displayMessage = sentMessagesCache[data.cache_key];
            delete sentMessagesCache[data.cache_key];  // Temizle
            console.log(`✅ Kendi mesajım (plaintext gösterilir)`);
        } else {
            displayMessage = data.message;  // Fallback
        }
    } else {
        // Gelen mesaj - decrypt et
        try {
            displayMessage = decrypt.decrypt(data.message);
            console.log(`🔓 Mesaj decrypted: ${data.username}`);
        } catch (e) {
            console.error('❌ Decryption hatası:', e);
            displayMessage = '[Decryption hatası]';
        }
    }
    
    const messagesDiv = document.getElementById('messages');
    const messageElement = document.createElement('div');
    messageElement.className = 'message ' + (data.username === username ? 'sent' : 'received');
    messageElement.setAttribute('data-message-id', data.message_id);
    
    let messageHTML = `<div class="message-content">${displayMessage}</div>`;
    
    if (data.username === username) {
        // Benim mesajım - timestamp tiklerin solunda
        messageHTML += `<div class="message-time">${data.timestamp}</div>`;
        messageHTML += `<div class="message-status" data-status="delivered" style="color: #999;">✓✓</div>`;
    } else {
        // Gelen mesaj - timestamp mesajın yanında
        messageHTML += `<span class="message-time-received">${data.timestamp}</span>`;
    }
    
    messageElement.innerHTML = messageHTML;
    
    // Gelen mesaj ise gönderenin adını container'ın dışında göster
    if (data.username !== username) {
        const senderLabel = document.createElement('div');
        senderLabel.className = 'message-sender-label';
        senderLabel.innerHTML = `👤 <strong>${data.username}</strong>`;
        messagesDiv.appendChild(senderLabel);
    }
    
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});
 
socket.on('message_status', function(data) {
    const messageId = data.message_id;
    const status = data.status;
    
    messageStatuses[messageId] = status;
    
    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (messageElement) {
        const statusEl = messageElement.querySelector('.message-status');
        if (statusEl) {
            statusEl.textContent = getStatusIcon(status);
            statusEl.setAttribute('data-status', status);
            statusEl.style.color = '#999';  // Hep gri
        }
    }
});
 
socket.on('user_joined', function(data) {
    const messagesDiv = document.getElementById('messages');
    const systemMsg = document.createElement('div');
    systemMsg.className = 'system-message';
    systemMsg.textContent = `✅ ${data.message}`;
    messagesDiv.appendChild(systemMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});
 
socket.on('user_left', function(data) {
    const messagesDiv = document.getElementById('messages');
    const systemMsg = document.createElement('div');
    systemMsg.className = 'system-message';
    systemMsg.textContent = `❌ ${data.message}`;
    messagesDiv.appendChild(systemMsg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
});
 
socket.on('load_conversations', function(data) {
    conversations = data.conversations;
    const onlineUsers = data.online_users || [];
    const autoChat = data.auto_chat;
    
    renderConversations();
    renderOnlineUsersList(onlineUsers);
    
    // Sohbetlerin statusunu güncelle
    setTimeout(() => {
        document.querySelectorAll('.conversation-item').forEach(item => {
            const userName = item.querySelector('span:nth-child(2)').textContent;
            const statusEl = item.querySelector('.user-status');
            
            if (onlineUsers.includes(userName)) {
                statusEl.textContent = '🟢';
                statusEl.style.color = '#00c851';
            } else {
                statusEl.textContent = '🔴';
                statusEl.style.color = '#ff6b6b';
            }
        });
    }, 100);
    
    if (autoChat) {
        // Otomatik sohbet açıldı!
        currentChat = autoChat;
        loadConversationMessages(autoChat);
        
        // Konuşmaları güncelle
        if (!conversations.includes(autoChat)) {
            conversations.push(autoChat);
            renderConversations();
        }
        
        // Sidebar'da vurgula
        const convItem = Array.from(document.querySelectorAll('.conversation-item')).find(el => el.querySelector('span:nth-child(2)').textContent === autoChat);
        if (convItem) {
            selectConversation(autoChat, convItem);
        }
    } else if (conversations.length > 0) {
        // Eski sohbetlerden seç
        const firstConv = document.querySelector('.conversation-item');
        if (firstConv) {
            const firstUser = firstConv.querySelector('span:nth-child(2)').textContent;
            selectConversation(firstUser, firstConv);
            loadConversationMessages(firstUser);
        }
    }
});
 
socket.on('partner_found', function(data) {
    const partner = data.partner;
    
    // Sohbeti konuşmalara ekle
    if (!conversations.includes(partner)) {
        conversations.push(partner);
        renderConversations();
    }
    
    // Otomatik seç
    currentChat = partner;
    loadConversationMessages(partner);
});
 
socket.on('update_online_users', function(data) {
    const onlineUsers = data.online_users;
    
    // Online Users bölümünü güncelle
    renderOnlineUsersList(onlineUsers);
    
    // Sohbetler listesinde durumları güncelle
    document.querySelectorAll('.conversation-item').forEach(item => {
        const userName = item.querySelector('span:nth-child(2)').textContent;
        const statusEl = item.querySelector('.user-status');
        
        if (onlineUsers.includes(userName)) {
            statusEl.textContent = '🟢';
            statusEl.style.color = '#00c851';
        } else {
            statusEl.textContent = '🔴';
            statusEl.style.color = '#ff6b6b';
        }
    });
});
 
function renderConversations() {
    const conversationsList = document.getElementById('conversationsList');
    conversationsList.innerHTML = '';
    
    if (conversations.length === 0) {
        conversationsList.innerHTML = '<div style="color: #999; font-size: 12px; padding: 10px;">Henüz sohbet yok</div>';
        return;
    }
    
    conversations.forEach(user => {
        const convEl = document.createElement('div');
        convEl.className = 'conversation-item';
        convEl.setAttribute('data-user', user);
        
        // Status göstergesi
        const statusEl = document.createElement('span');
        statusEl.className = 'user-status';
        statusEl.textContent = '⚫';
        statusEl.style.marginRight = '8px';
        statusEl.style.flexShrink = '0';
        
        const userSpan = document.createElement('span');
        userSpan.textContent = user;
        userSpan.style.flex = '1';
        userSpan.onclick = () => {
            selectConversation(user, convEl);
            loadConversationMessages(user);
        };
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-chat';
        deleteBtn.textContent = '−';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteConversation(user);
        };
        
        convEl.appendChild(statusEl);
        convEl.appendChild(userSpan);
        convEl.appendChild(deleteBtn);
        
        conversationsList.appendChild(convEl);
    });
}
 
function renderOnlineUsersList(onlineUsers) {
    const onlineUsersList = document.getElementById('onlineUsersList');
    onlineUsersList.innerHTML = '';
    
    if (!onlineUsers || onlineUsers.length === 0) {
        onlineUsersList.innerHTML = '<div style="color: #999; font-size: 12px; padding: 10px;">Kimse online değil</div>';
        return;
    }
    
    // TÜM online users'ları göster (conversations'dan bağımsız)
    onlineUsers.forEach(user => {
        const userEl = document.createElement('div');
        userEl.className = 'online-user-item';
        
        const statusEl = document.createElement('span');
        statusEl.textContent = '🟢';
        statusEl.style.marginRight = '8px';
        statusEl.style.color = '#00c851';
        statusEl.style.fontSize = '14px';
        
        const nameEl = document.createElement('span');
        nameEl.textContent = user;
        nameEl.style.flex = '1';
        
        userEl.appendChild(statusEl);
        userEl.appendChild(nameEl);
        userEl.onclick = () => {
            // Sohbete tıklayınca aç
            const convItem = document.querySelector(`[data-user="${user}"]`);
            if (convItem) {
                selectConversation(user, convItem);
                loadConversationMessages(user);
            } else {
                // Sohbet yoksa konuşmaya ekle
                if (!conversations.includes(user)) {
                    conversations.push(user);
                    renderConversations();
                }
                const newConv = document.querySelector(`[data-user="${user}"]`);
                if (newConv) {
                    selectConversation(user, newConv);
                    loadConversationMessages(user);
                }
            }
        };
        
        onlineUsersList.appendChild(userEl);
    });
}
 
function deleteConversation(user) {
    if (confirm(`${user} ile sohbeti silmek istediğinize emin misiniz?`)) {
        socket.emit('delete_conversation', { user: user });
        
        // UI'dan sil
        conversations = conversations.filter(u => u !== user);
        renderConversations();
        renderOnlineUsersList([]);
        
        // Seçili sohbet silinirse, başka bir tane seç
        if (currentChat === user) {
            currentChat = null;
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #999;"><div style="font-size: 50px; margin-bottom: 20px;">💬</div><div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;">Sohbete Hoşgeldiniz!</div><div style="font-size: 14px;">Sol taraftan bir sohbet seçin</div></div>';
        }
    }
}
 
function selectConversation(user, element) {
    currentChat = user;
    
    document.querySelectorAll('.conversation-item').forEach(el => {
        el.classList.remove('active');
    });
    element.classList.add('active');
}
 
function loadConversationMessages(otherUser) {
    currentChat = otherUser;
    const messagesDiv = document.getElementById('messages');
    // messagesDiv.innerHTML = ''; // Boş bırak, mesajlar hemen gelecek
    
    // 🔐 Eğer public key yoksa talep et
    if (!publicKeys[otherUser]) {
        console.log(`⚠️ ${otherUser}'ın public key'i yok, talep ediliyor...`);
        socket.emit('get_public_key', {
            username: otherUser
        });
    } else {
        console.log(`✅ ${otherUser}'ın public key'i var`);
    }
    
    socket.emit('get_conversation_messages', {
        other_user: otherUser
    });
}
 
// Yazıyor göstergesi göster
socket.on('typing', function(data) {
    if (currentChat === data.username) {
        showTypingIndicator(data.username);
    }
});
 
// Yazıyor göstergesi kapat
socket.on('stop_typing', function(data) {
    removeTypingIndicator();
});
 
function showTypingIndicator(senderName) {
    let indicator = document.getElementById('typing-indicator');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.className = 'typing-indicator';
        indicator.innerHTML = `
            <div class="typing-dots">
                <span>●</span>
                <span>●</span>
                <span>●</span>
            </div>
            <span>${senderName} yazıyor...</span>
        `;
        document.getElementById('messages').appendChild(indicator);
    }
}
 
function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}
 
socket.on('conversation_messages', function(data) {
    const messagesDiv = document.getElementById('messages');
    
    messagesDiv.innerHTML = '';
    
    // 🔐 E2EE: Boş sohbet - hiçbir şey gösterme
    // Yeni mesajlar socket.on('message') event'i ile gelir ve gösterilir
});
 
// Enter key support
document.addEventListener('DOMContentLoaded', function() {
    const loginUsername = document.getElementById('loginUsername');
    const loginPassword = document.getElementById('loginPassword');
    const registerUsername = document.getElementById('registerUsername');
    const registerPassword = document.getElementById('registerPassword');
    const registerPasswordConfirm = document.getElementById('registerPasswordConfirm');
    const messageInput = document.getElementById('messageInput');
    
    if (loginUsername) {
        loginUsername.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                if (loginPassword.value.trim()) {
                    login();
                } else {
                    loginPassword.focus();
                }
            }
        });
    }
    
    if (loginPassword) {
        loginPassword.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') login();
        });
    }
    
    if (registerUsername) {
        registerUsername.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') registerPassword.focus();
        });
    }
    
    if (registerPassword) {
        registerPassword.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') registerPasswordConfirm.focus();
        });
    }
    
    if (registerPasswordConfirm) {
        registerPasswordConfirm.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') register();
        });
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    }
});
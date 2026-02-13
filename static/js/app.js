const API_BASE = '/api';
let currentPostId = null;
let currentUser = null; // Текущий пользователь (для админ-кнопки удаления)
let emojiAnimations = new Set(); // Отслеживание активных анимаций

function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
        (navigator.maxTouchPoints > 0 && window.innerWidth < 1024);
}

function setupLoginLinks() {
    const mobile = isMobile();
    const headerLink = document.getElementById('auth-login-link');
    const modalLink = document.getElementById('auth-required-modal-link');
    [headerLink, modalLink].filter(Boolean).forEach(function(link) {
        var mobileHref = link.dataset.mobileHref;
        var desktopHref = link.dataset.desktopHref || link.href;
        if (mobile) {
            link.href = mobileHref || desktopHref;
            link.removeAttribute('target');
            link.onclick = null;
        } else {
            link.href = link.dataset.desktopHref || link.href;
            link.target = 'telegram_login';
            link.onclick = function(e) {
                window.open(this.href, 'telegram_login', 'width=420,height=500');
                if (link.id === 'auth-required-modal-link') {
                    document.getElementById('auth-required-modal').style.display = 'none';
                }
                return false;
            };
        }
    });
}

// Список популярных эмодзи
const popularEmojis = [
    { code: '1f600', type: 'grinning', emoji: '😀' },
    { code: '2764_fe0f', type: 'heart', emoji: '❤️' },
    { code: '1f44d', type: 'like', emoji: '👍' },
    { code: '1f602', type: 'laughing', emoji: '😂' },
    { code: '1f62e', type: 'surprised', emoji: '😮' },
    { code: '1f603', type: 'smiley', emoji: '😃' },
    { code: '1f604', type: 'grin', emoji: '😄' },
    { code: '1f617', type: 'kissing', emoji: '😗' },
    { code: '1f618', type: 'kissing_heart', emoji: '😘' },
    { code: '1f61a', type: 'kissing_closed_eyes', emoji: '😚' },
    { code: '1f61c', type: 'winky_tongue', emoji: '😜' },
    { code: '1f61d', type: 'squinting_tongue', emoji: '😝' },
    { code: '1f60e', type: 'sunglasses', emoji: '😎' },
    { code: '1f60f', type: 'smirk', emoji: '😏' },
    { code: '1f612', type: 'unamused', emoji: '😒' },
    { code: '1f613', type: 'sweat', emoji: '😓' },
    { code: '1f614', type: 'pensive', emoji: '😔' },
    { code: '1f615', type: 'confused', emoji: '😕' },
    { code: '1f616', type: 'confounded', emoji: '😖' },
    { code: '1f61e', type: 'disappointed', emoji: '😞' },
    { code: '1f61f', type: 'worried', emoji: '😟' },
    { code: '1f620', type: 'angry', emoji: '😠' },
    { code: '1f621', type: 'rage', emoji: '😡' },
    { code: '1f622', type: 'cry', emoji: '😢' },
    { code: '1f623', type: 'persevere', emoji: '😣' },
    { code: '1f625', type: 'relieved', emoji: '😥' },
    { code: '1f628', type: 'fearful', emoji: '😨' },
    { code: '1f629', type: 'weary', emoji: '😩' },
    { code: '1f62a', type: 'sleepy', emoji: '😪' },
    { code: '1f62b', type: 'tired_face', emoji: '😫' },
    { code: '1f62c', type: 'grimace', emoji: '😬' },
    { code: '1f62d', type: 'loudly_crying', emoji: '😭' },
    { code: '1f630', type: 'cold_sweat', emoji: '😰' },
    { code: '1f631', type: 'scream', emoji: '😱' },
    { code: '1f632', type: 'astonished', emoji: '😲' },
    { code: '1f633', type: 'flushed', emoji: '😳' },
    { code: '1f634', type: 'sleeping', emoji: '😴' },
    { code: '1f635', type: 'dizzy_face', emoji: '😵' },
    { code: '1f637', type: 'mask', emoji: '😷' },
    { code: '1f638', type: 'cat_grinning', emoji: '😸' },
    { code: '1f639', type: 'cat_laughing', emoji: '😹' },
    { code: '1f63a', type: 'cat_smiling', emoji: '😺' },
    { code: '1f63b', type: 'cat_heart_eyes', emoji: '😻' },
    { code: '1f63c', type: 'cat_wry_smile', emoji: '😼' },
    { code: '1f63d', type: 'cat_kissing', emoji: '😽' },
    { code: '1f63e', type: 'cat_pouting', emoji: '😾' },
    { code: '1f63f', type: 'cat_crying', emoji: '😿' },
    { code: '1f640', type: 'cat_weary', emoji: '🙀' },
    { code: '1f641', type: 'slightly_frowning', emoji: '🙁' },
    { code: '1f642', type: 'slightly_smiling', emoji: '🙂' },
    { code: '1f643', type: 'upside_down', emoji: '🙃' },
    { code: '1f644', type: 'rolling_eyes', emoji: '🙄' },
    { code: '1f910', type: 'zipper_mouth', emoji: '🤐' },
    { code: '1f911', type: 'money_mouth', emoji: '🤑' },
    { code: '1f912', type: 'thermometer_face', emoji: '🤒' },
    { code: '1f913', type: 'nerd', emoji: '🤓' },
    { code: '1f914', type: 'thinking', emoji: '🤔' },
    { code: '1f915', type: 'head_bandage', emoji: '🤕' },
    { code: '1f916', type: 'robot', emoji: '🤖' },
    { code: '1f917', type: 'hugging', emoji: '🤗' },
    { code: '1f918', type: 'sign_of_the_horns', emoji: '🤘' },
    { code: '1f919', type: 'call_me', emoji: '🤙' },
    { code: '1f91a', type: 'raised_back_of_hand', emoji: '🤚' },
    { code: '1f91b', type: 'left_facing_fist', emoji: '🤛' },
    { code: '1f91c', type: 'right_facing_fist', emoji: '🤜' },
    { code: '1f91d', type: 'handshake', emoji: '🤝' },
    { code: '1f91e', type: 'crossed_fingers', emoji: '🤞' },
    { code: '1f920', type: 'cowboy', emoji: '🤠' },
    { code: '1f921', type: 'clown', emoji: '🤡' },
    { code: '1f922', type: 'nauseated_face', emoji: '🤢' },
    { code: '1f923', type: 'rofl', emoji: '🤣' },
    { code: '1f924', type: 'drooling_face', emoji: '🤤' },
    { code: '1f925', type: 'lying_face', emoji: '🤥' },
    { code: '1f927', type: 'sneezing_face', emoji: '🤧' },
    { code: '1f929', type: 'star_struck', emoji: '🤩' },
    { code: '1f92a', type: 'zany_face', emoji: '🤪' },
    { code: '1f92b', type: 'shushing_face', emoji: '🤫' },
    { code: '1f92c', type: 'symbols_over_mouth', emoji: '🤬' },
    { code: '1f92d', type: 'hand_over_mouth', emoji: '🤭' },
    { code: '1f92e', type: 'face_vomiting', emoji: '🤮' },
    { code: '1f92f', type: 'exploding_head', emoji: '🤯' },
    { code: '1f970', type: 'smiling_face_with_three_hearts', emoji: '🥰' },
    { code: '1f973', type: 'partying_face', emoji: '🥳' },
    { code: '1f974', type: 'woozy_face', emoji: '🥴' },
    { code: '1f975', type: 'hot_face', emoji: '🥵' },
    { code: '1f976', type: 'cold_face', emoji: '🥶' },
    { code: '1f97a', type: 'pleading_face', emoji: '🥺' },
    { code: '1f9d0', type: 'face_with_monocle', emoji: '🧐' },
];

// Инициализация реакций
function initReactions() {
    const reactionsScroll = document.getElementById('reactions-scroll');
    reactionsScroll.innerHTML = '';
    
    popularEmojis.forEach(emoji => {
        const reaction = document.createElement('span');
        reaction.className = 'reaction';
        reaction.setAttribute('data-emoji', emoji.emoji);
        reaction.setAttribute('data-type', emoji.type);
        
        reaction.innerHTML = `
            <picture>
                <source srcset="https://fonts.gstatic.com/s/e/notoemoji/latest/${emoji.code}/512.webp" type="image/webp">
                <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/${emoji.code}/512.gif" alt="${emoji.emoji}" width="28" height="28">
            </picture>
        `;
        
        reaction.addEventListener('click', function(e) {
            e.stopPropagation();
            handleReactionClick(this, currentPostId);
        });
        
        reactionsScroll.appendChild(reaction);
    });
}

// Обработка клика по реакции
async function handleReactionClick(element, postId) {
    if (!postId) return;
    
    const reactionType = element.getAttribute('data-type');
    const emojiData = popularEmojis.find(e => e.type === reactionType);
    
    if (!emojiData) return;
    
    // Анимация нажатия
    element.classList.add('active');
    setTimeout(() => element.classList.remove('active'), 300);
    
    // Отправка на сервер
    try {
        const response = await fetch(`${API_BASE}/posts/${postId}/reactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reaction_type: reactionType })
        });
        
        const data = await response.json().catch(() => ({}));
        
        if (response.status === 401 || data.error === 'auth_required') {
            showAuthRequiredModal();
            document.getElementById('reactions').style.display = 'none';
            return;
        }
        
        if (data.is_new) {
            playEmojiAnimation(element, emojiData);
        }
        const postEl = document.querySelector(`.post[data-post-id="${postId}"]`);
        if (postEl) {
            updatePostReactions(postEl, data.reactions, data.my_reaction);
        }
        setTimeout(() => {
            document.getElementById('reactions').style.display = 'none';
        }, 200);
    } catch (error) {
        console.error('Ошибка при добавлении реакции:', error);
    }
}

// Проигрывание анимации эмодзи (только 1 цикл)
function playEmojiAnimation(element, emojiData) {
    const rect = element.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    
    // Создаем уникальный ключ для отслеживания
    const animationKey = `${currentPostId}_${emojiData.type}`;
    
    // Проверяем, не проигрывается ли уже эта анимация
    if (emojiAnimations.has(animationKey)) {
        return;
    }
    
    emojiAnimations.add(animationKey);
    
    // Создаем изображение с анимацией (GIF проиграется 1 раз)
    const img = document.createElement('img');
    img.src = `https://fonts.gstatic.com/s/e/notoemoji/latest/${emojiData.code}/512.gif`;
    img.alt = emojiData.emoji;
    img.className = 'emoji-animation';
    img.style.left = x + 'px';
    img.style.top = y + 'px';
    img.style.width = '24px';
    img.style.height = '24px';
    
    document.body.appendChild(img);
    
    // Удаляем после анимации
    setTimeout(() => {
        img.remove();
        emojiAnimations.delete(animationKey);
    }, 1000);
}

// Загрузка постов
async function loadPosts() {
    try {
        const response = await fetch(`${API_BASE}/posts`);
        const posts = await response.json();
        
        const container = document.getElementById('posts-container');
        container.innerHTML = '';
        
        if (posts.length === 0) {
            container.innerHTML = '<div class="loading">Пока нет постов</div>';
            return;
        }
        
        posts.forEach(post => {
            const postElement = createPostElement(post);
            container.appendChild(postElement);
        });
    } catch (error) {
        console.error('Ошибка при загрузке постов:', error);
    }
}

// Создание элемента поста
function createPostElement(post) {
    const postDiv = document.createElement('div');
    postDiv.className = 'post';
    postDiv.dataset.postId = post.id;
    
    let mediaHTML = '';
    
    // ПРОВЕРКА: Если путь начинается с http, используем его как есть.
    // Если нет (старый формат) — добавляем /uploads/
    const isCloudinary = post.media_path && post.media_path.startsWith('http');
    const fullMediaPath = isCloudinary ? post.media_path : ('/uploads/' + post.media_path);

    if (post.media_type === 'photo') {
        mediaHTML = `<img src="${fullMediaPath}" alt="Post" class="post-media" loading="lazy">`;
    } else if (post.media_type === 'video' || post.media_type === 'animation') {
        // Добавим autoplay и loop для анимаций (гифок из TG), так как они приходят как видео
        const isAnimation = post.media_type === 'animation';
        mediaHTML = `<video src="${fullMediaPath}" ${isAnimation ? 'autoplay loop muted playsinline' : 'controls'} class="post-media"></video>`;
    }
    
    const captionHTML = post.caption ? `<div class="post-caption">${escapeHtml(post.caption)}</div>` : '';
    const reactionsHTML = createReactionsHTML(post.reactions || {}, post.id, post.my_reaction);
    const deleteBtnHTML = (currentUser && currentUser.is_admin) ? `<button type="button" class="post-delete-btn" aria-label="Удалить пост" data-post-id="${post.id}">×</button>` : '';
    
    postDiv.innerHTML = `
        <div class="post-inner">
            ${deleteBtnHTML}
            ${mediaHTML}
            ${captionHTML}
            <div class="post-footer">
                <div class="counter-container">
                    ${reactionsHTML}
                </div>
            </div>
        </div>
    `;
    
    // Добавляем обработчик правого клика
    const mediaElement = postDiv.querySelector('.post-media');
    if (mediaElement) {
        mediaElement.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            currentPostId = post.id;
            showReactionsPanel(e);
        });
    }
    
    attachCounterListeners(postDiv);

    // Обработчик удаления поста (админ)
    const deleteBtn = postDiv.querySelector('.post-delete-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            showDeletePostModal(post.id);
        });
    }

    // Наклон карточки за курсором
    (function bindTilt(el) {
        const maxTilt = 1;
        el.addEventListener('mouseenter', function() {
            el.style.transition = 'transform 0.1s ease-out';
        });
        el.addEventListener('mousemove', function(e) {
            const rect = el.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;
            const rotateY = x * maxTilt * 2;
            const rotateX = -y * maxTilt * 2;
            el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });
        el.addEventListener('mouseleave', function() {
            el.style.transition = 'transform 0.3s ease-out';
            el.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)';
        });
    })(postDiv);

    return postDiv;
}

// HTML одного счётчика реакций (с обёрткой для анимации прокрутки)
function counterItemHTML(type, count, isMine) {
    const emojiData = popularEmojis.find(e => e.type === type);
    if (!emojiData || count === 0) return '';
    return `
        <div class="counter-item ${isMine ? 'my-reaction' : ''}" data-type="${type}" data-count="${count}">
            <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/${emojiData.code}/512.gif" alt="${emojiData.emoji}" width="18" height="18">
            <div class="counter-value-wrap">
                <span class="counter-value current">${count}</span>
                <span class="counter-value next">${count}</span>
            </div>
        </div>
    `;
}

// Создание HTML для реакций (myReaction — тип реакции текущего пользователя или null)
function createReactionsHTML(reactions, postId, myReaction) {
    let html = '';
    Object.entries(reactions).forEach(([type, count]) => {
        if (count === 0) return;
        html += counterItemHTML(type, count, type === myReaction);
    });
    return html;
}

const COUNTER_ANIMATION_DURATION_MS = 250;

// Обновить только блок реакций у одного поста (с анимацией прокрутки счётчика)
function updatePostReactions(postElement, reactions, myReaction) {
    const postId = parseInt(postElement.dataset.postId, 10);
    const container = postElement.querySelector('.counter-container');
    if (!container) return;

    const newReactions = reactions || {};
    const newMyReaction = myReaction || null;

    // Обновить существующие счётчики и удалить исчезнувшие
    container.querySelectorAll('.counter-item').forEach(item => {
        const type = item.dataset.type;
        const oldCount = parseInt(item.dataset.count, 10) || 0;
        const newCount = newReactions[type];

        if (newCount === undefined || newCount === 0) {
            item.remove();
            return;
        }

        item.classList.toggle('my-reaction', type === newMyReaction);
        item.dataset.count = String(newCount);

        if (newCount === oldCount) {
            item.querySelector('.counter-value.current').textContent = newCount;
            const nextEl = item.querySelector('.counter-value.next');
            if (nextEl) nextEl.textContent = newCount;
            return;
        }

        // Анимация прокрутки: новое число сверху (увеличение) или снизу (уменьшение)
        const wrap = item.querySelector('.counter-value-wrap');
        if (!wrap) return;
        const currentSpan = wrap.querySelector('.counter-value.current');
        const nextSpan = wrap.querySelector('.counter-value.next');
        if (!currentSpan || !nextSpan) return;

        currentSpan.textContent = oldCount;
        nextSpan.textContent = newCount;
        wrap.classList.remove('roll-up', 'roll-down', 'animating');
        wrap.classList.add(newCount > oldCount ? 'roll-up' : 'roll-down');

        requestAnimationFrame(() => {
            wrap.classList.add('animating');
        });

        setTimeout(() => {
            wrap.classList.remove('animating', 'roll-up', 'roll-down');
            currentSpan.textContent = newCount;
            nextSpan.textContent = newCount;
        }, COUNTER_ANIMATION_DURATION_MS);
    });

    // Добавить новые типы реакций, которых ещё нет
    Object.entries(newReactions).forEach(([type, count]) => {
        if (count === 0) return;
        if (container.querySelector(`.counter-item[data-type="${type}"]`)) return;
        container.insertAdjacentHTML('beforeend', counterItemHTML(type, count, type === newMyReaction));
    });
}

// Один обработчик на карточку поста (делегирование): клики по счётчикам не дублируют запросы
function attachCounterListeners(postElement) {
    postElement.addEventListener('click', async function(e) {
        const item = e.target.closest('.counter-item');
        if (!item) return;
        e.stopPropagation();
        const postId = parseInt(postElement.dataset.postId, 10);
        const reactionType = item.dataset.type;
        const emojiData = popularEmojis.find(em => em.type === reactionType);
        if (!emojiData) return;
        try {
            const response = await fetch(`${API_BASE}/posts/${postId}/reactions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reaction_type: reactionType })
            });
            const data = await response.json().catch(() => ({}));
            if (response.status === 401 || data.error === 'auth_required') {
                showAuthRequiredModal();
                return;
            }
            if (data.is_new) {
                playEmojiAnimationFromCounter(item, emojiData, postId);
            }
            updatePostReactions(postElement, data.reactions, data.my_reaction);
        } catch (error) {
            console.error('Ошибка при добавлении реакции:', error);
        }
    });
}

// Модальное окно «Необходимо авторизоваться»
function showAuthRequiredModal() {
    const modal = document.getElementById('auth-required-modal');
    if (modal) modal.style.display = 'flex';
}

function hideAuthRequiredModal() {
    const modal = document.getElementById('auth-required-modal');
    if (modal) modal.style.display = 'none';
}

// Модальное окно подтверждения удаления поста
let deletePostModalPostId = null;

function showDeletePostModal(postId) {
    deletePostModalPostId = postId;
    const modal = document.getElementById('delete-post-modal');
    if (modal) modal.style.display = 'flex';
}

function hideDeletePostModal() {
    deletePostModalPostId = null;
    const modal = document.getElementById('delete-post-modal');
    if (modal) modal.style.display = 'none';
}

async function confirmDeletePost() {
    if (deletePostModalPostId == null) return;
    const postId = deletePostModalPostId;
    hideDeletePostModal();
    try {
        const response = await fetch(`${API_BASE}/posts/${postId}`, { method: 'DELETE' });
        if (response.ok) {
            const card = document.querySelector(`.post[data-post-id="${postId}"]`);
            if (card) card.remove();
        }
    } catch (error) {
        console.error('Ошибка при удалении поста:', error);
    }
}

// Показ панели реакций
function showReactionsPanel(e) {
    const panel = document.getElementById('reactions');
    panel.style.display = 'block';
    panel.style.left = e.pageX + 'px';
    panel.style.top = e.pageY + 'px';
    
    // Корректировка позиции, чтобы панель не выходила за границы экрана
    setTimeout(() => {
        const rect = panel.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            panel.style.left = (e.pageX - rect.width) + 'px';
        }
        if (rect.bottom > window.innerHeight) {
            panel.style.top = (e.pageY - rect.height) + 'px';
        }
    }, 0);
}

// Проигрывание анимации из счетчика
function playEmojiAnimationFromCounter(counterElement, emojiData, postId) {
    const rect = counterElement.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    
    const animationKey = `${postId}_${emojiData.type}`;
    
    if (emojiAnimations.has(animationKey)) {
        return;
    }
    
    emojiAnimations.add(animationKey);
    
    const img = document.createElement('img');
    img.src = `https://fonts.gstatic.com/s/e/notoemoji/latest/${emojiData.code}/512.gif`;
    img.alt = emojiData.emoji;
    img.className = 'emoji-animation';
    img.style.left = x + 'px';
    img.style.top = y + 'px';
    img.style.width = '24px';
    img.style.height = '24px';
    
    document.body.appendChild(img);
    
    setTimeout(() => {
        img.remove();
        emojiAnimations.delete(animationKey);
    }, 1000);
}

// ——— Вход через Telegram ———
function displayName(user) {
    if (user.username) return '@' + user.username;
    if (user.first_name) return user.first_name + (user.last_name ? ' ' + user.last_name : '');
    return 'Пользователь';
}

function getFirstChar(user) {
    if (user.username && user.username.length > 0) return user.username[0].toUpperCase();
    if (user.first_name && user.first_name.length > 0) return user.first_name[0].toUpperCase();
    return 'П';
}

function updateAuthUI(user) {
    const loginWrap = document.getElementById('auth-login-wrap');
    const userWrap = document.getElementById('auth-user-wrap');
    const avatarEl = document.getElementById('auth-user-avatar');
    const fallbackEl = document.getElementById('auth-user-avatar-fallback');
    const adminBadge = document.getElementById('auth-admin-badge');
    if (!loginWrap || !userWrap) return;
    if (user && (user.telegram_id || user.username || user.first_name)) {
        if (avatarEl) {
            if (user.photo_url) {
                avatarEl.src = user.photo_url;
                avatarEl.alt = displayName(user);
                avatarEl.title = displayName(user);
                avatarEl.style.display = '';
                if (fallbackEl) fallbackEl.style.display = 'none';
            } else {
                avatarEl.removeAttribute('src');
                avatarEl.style.display = 'none';
                if (fallbackEl) {
                    fallbackEl.textContent = getFirstChar(user);
                    fallbackEl.style.display = 'flex';
                }
            }
        }
        if (adminBadge) {
            adminBadge.style.display = user.is_admin ? 'inline' : 'none';
        }
        loginWrap.style.display = 'none';
        userWrap.style.display = 'flex';
    } else {
        if (avatarEl) { avatarEl.removeAttribute('src'); avatarEl.style.display = 'none'; }
        if (fallbackEl) fallbackEl.style.display = 'none';
        if (adminBadge) adminBadge.style.display = 'none';
        loginWrap.style.display = 'flex';
        userWrap.style.display = 'none';
    }
}

async function loadMe() {
    try {
        const response = await fetch(API_BASE + '/me');
        const user = await response.json();
        currentUser = user && (user.telegram_id || user.username || user.first_name) ? user : null;
        updateAuthUI(user);
    } catch (e) {
        currentUser = null;
        updateAuthUI(null);
    }
}

window.onTelegramAuth = async function(user) {
    try {
        const response = await fetch(API_BASE + '/auth/telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(user)
        });
        const data = await response.json();
        if (data.ok && data.user) {
            updateAuthUI(data.user);
            try { window.open('', 'telegram_login')?.close(); } catch (_) {}
        }
    } catch (e) {
        console.error('Ошибка входа через Telegram:', e);
    }
};

// Загрузка информации о канале
async function loadChannelInfo() {
    try {
        const response = await fetch(`${API_BASE}/channel-info`);
        const info = await response.json();
        
        document.getElementById('channel-name').textContent = info.name || 'Telegram Channel';
        const avatar = document.getElementById('channel-avatar');
        if (info.avatar_url) {
            avatar.src = info.avatar_url;
            avatar.style.display = 'block';
        } else {
            avatar.style.display = 'none';
        }
    } catch (error) {
        console.error('Ошибка при загрузке информации о канале:', error);
    }
}

// Экранирование HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Закрытие панели при клике вне её
document.addEventListener('click', function(e) {
    const panel = document.getElementById('reactions');
    if (!panel.contains(e.target) && panel.style.display === 'block') {
        panel.style.display = 'none';
    }
});

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    setupLoginLinks();
    initReactions();
    loadChannelInfo();
    (async function() {
        await loadMe();
        loadPosts();
    })();

    document.getElementById('auth-logout')?.addEventListener('click', async function() {
        try {
            await fetch(API_BASE + '/logout', { method: 'POST' });
            currentUser = null;
            updateAuthUI(null);
            loadPosts();
        } catch (e) {
            currentUser = null;
            updateAuthUI(null);
        }
    });

    document.getElementById('auth-required-modal-close')?.addEventListener('click', hideAuthRequiredModal);
    document.getElementById('delete-post-confirm')?.addEventListener('click', confirmDeletePost);
    document.getElementById('delete-post-cancel')?.addEventListener('click', hideDeletePostModal);
    document.getElementById('delete-post-modal')?.addEventListener('click', function(e) {
        if (e.target === this) hideDeletePostModal();
    });
    document.getElementById('auth-required-modal')?.addEventListener('click', function(e) {
        if (e.target === this) hideAuthRequiredModal();
    });

    // Обновление постов каждые 30 секунд
    setInterval(loadPosts, 30000);
});

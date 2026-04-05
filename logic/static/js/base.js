function showToast(msg, duration = 5000) {
  const toastBody = document.getElementById('toast-body');
  const toastEl = document.getElementById('app-toast');
  
  if (!toastBody || !toastEl) return;
  
  toastBody.textContent = msg;
  
  if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
    const t = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: duration, autohide: true });
    t.show();
  }
}

const btn = document.getElementById('lang');

if (btn) {
  btn.addEventListener('click', async () => {
    const currentLang = sessionStorage.getItem('lang') || 'en';
    const newLang = currentLang === 'ru' ? 'en' : 'ru';
    
    try {
      const response = await fetch('/set_language', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ lang: newLang })
      });
      
      if (response.ok) {
        sessionStorage.setItem('lang', newLang);
        window.location.reload();
      } else {
        showToast('Failed to change language');
      }
    } catch (error) {
      showToast('Network error');
    }
  });
}

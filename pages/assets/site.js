'use strict';
document.documentElement.classList.add('js');
const menu = document.getElementById('menu-toggle');
const sidebar = document.getElementById('sidebar');
menu.hidden = false;
function closeMenu() {
  menu.setAttribute('aria-expanded', 'false');
  sidebar.classList.remove('is-open');
}
menu.addEventListener('click', () => {
  const opening = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(opening));
  sidebar.classList.toggle('is-open', opening);
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
    closeMenu();
    menu.focus();
  }
});
if (navigator.clipboard && window.isSecureContext) {
  document.querySelectorAll('pre > code').forEach((code) => {
    const button = document.createElement('button');
    button.className = 'copy-button';
    button.type = 'button';
    button.textContent = 'Copy';
    button.setAttribute('aria-label', 'Copy code to clipboard');
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = 'Copied';
        document.getElementById('copy-status').textContent = 'Code copied to clipboard.';
      } catch {
        document.getElementById('copy-status').textContent = 'Could not copy. Select the code and copy it manually.';
      }
      window.setTimeout(() => { button.textContent = 'Copy'; }, 1800);
    });
    code.before(button);
  });
}

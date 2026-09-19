// UniApp H5 renders custom elements. Supply keyboard and label semantics without
// changing native mini-program controls.
export function installH5Accessibility() {
  // #ifdef H5
  const decorate = () => {
    document.querySelectorAll<HTMLElement>('uni-button').forEach((button) => {
      const disabled = button.hasAttribute('disabled');
      button.setAttribute('role', 'button');
      button.setAttribute('tabindex', disabled ? '-1' : '0');
      button.setAttribute('aria-disabled', String(disabled));
    });
    document.querySelectorAll<HTMLElement>('uni-input,uni-textarea').forEach((wrapper) => {
      const input = wrapper.querySelector<HTMLInputElement>('input,textarea');
      if (!input) return;
      const label = wrapper.getAttribute('aria-label');
      if (label) input.setAttribute('aria-label', label);
      const invalid = wrapper.getAttribute('aria-invalid') || 'false';
      if (input.getAttribute('aria-invalid') !== invalid)
        input.setAttribute('aria-invalid', invalid);
    });
  };
  let queued = false;
  new MutationObserver(() => {
    if (!queued) {
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        decorate();
      });
    }
  }).observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['disabled', 'aria-invalid']
  });
  document.addEventListener('keydown', (event) => {
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'UNI-BUTTON' &&
      !target.hasAttribute('disabled') &&
      (event.key === 'Enter' || event.key === ' ')
    ) {
      event.preventDefault();
      target.click();
    }
  });
  decorate();
  // #endif
}

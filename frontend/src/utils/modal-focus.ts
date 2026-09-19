// H5 only: each modal owns its focus boundary, including before the global
// UniApp accessibility observer has decorated newly mounted custom buttons.
const activeDialogs: HTMLElement[] = [];

export function trapModalFocus(
  dialog: HTMLElement,
  canClose: () => boolean,
  close: () => void
) {
  const previous = document.activeElement as HTMLElement | null;
  dialog.tabIndex = -1;
  activeDialogs.push(dialog);
  const active = () => activeDialogs[activeDialogs.length - 1] === dialog;
  function controls() {
    dialog.querySelectorAll<HTMLElement>('uni-button').forEach((button) => {
      button.tabIndex = button.hasAttribute('disabled') ? -1 : 0;
    });
    return Array.from(
      dialog.querySelectorAll<HTMLElement>(
        'uni-button,button,input,textarea,select,a[href],[tabindex]'
      )
    ).filter(
      (node) =>
        !node.hasAttribute('disabled') &&
        node.getAttribute('aria-disabled') !== 'true' &&
        node.tabIndex >= 0 &&
        node.getClientRects().length > 0 &&
        !node.closest('[inert]')
    );
  }
  function focusFirst() {
    (controls()[0] || dialog).focus();
  }
  function enforceFocus(event: FocusEvent) {
    if (active() && !dialog.contains(event.target as Node)) focusFirst();
  }
  function keyboard(event: KeyboardEvent) {
    if (!active()) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      if (canClose()) close();
      return;
    }
    if (event.key === 'Tab') {
      const nodes = controls();
      const index = nodes.indexOf(document.activeElement as HTMLElement);
      event.preventDefault();
      const next = index < 0 ? (event.shiftKey ? nodes.length - 1 : 0) :
        (index + (event.shiftKey ? -1 : 1) + nodes.length) % nodes.length;
      (nodes[next] || dialog).focus();
    } else if (!dialog.contains(event.target as Node)) {
      // A disabled control or the browser chrome may have left focus outside.
      event.preventDefault();
      event.stopPropagation();
      focusFirst();
    }
  }
  document.addEventListener('keydown', keyboard, true);
  document.addEventListener('focusin', enforceFocus);
  focusFirst();
  return () => {
    const wasActive = active();
    const index = activeDialogs.indexOf(dialog);
    if (index >= 0) activeDialogs.splice(index, 1);
    document.removeEventListener('keydown', keyboard, true);
    document.removeEventListener('focusin', enforceFocus);
    if (wasActive && previous?.isConnected) previous.focus();
  };
}

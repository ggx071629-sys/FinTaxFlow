/** UniApp's blur/confirm payload differs from the DOM FocusEvent declaration. */
export function inputValue(event: unknown): string {
  const payload = event as { detail?: { value?: unknown }; target?: { value?: unknown } };
  return String(payload.detail?.value ?? payload.target?.value ?? '');
}

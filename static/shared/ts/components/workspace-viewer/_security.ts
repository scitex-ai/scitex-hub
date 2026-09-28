/** Keep an untrusted value on one physical log line. */
export function sanitizeLogValue(value: string): string {
  return value
    .replace(/[\r\n\u2028\u2029]/g, " ")
    .replace(/[\u0000-\u001f\u007f]/g, "?");
}

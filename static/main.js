// Global utility — used across pages
function useLastVal(fieldId, val) {
  const el = document.getElementById(fieldId);
  if (el) {
    el.value = val;
    el.dispatchEvent(new Event('input'));
  }
}

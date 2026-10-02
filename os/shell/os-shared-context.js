/**
 * NYAYA-SATYA OS — Shared Case Context & Navigation Controller
 * Manages active case synchronization across all 13 application experiences.
 */

(function() {
  // 1. Determine active case
  const urlParams = new URLSearchParams(window.location.search);
  let activeCaseId = urlParams.get('case_id') || localStorage.getItem('nyaya_active_case_id') || 'CASE-2024-DEL-0482';
  localStorage.setItem('nyaya_active_case_id', activeCaseId);

  window.nyayaActiveCaseId = activeCaseId;
  window.osGetActiveCase = function() {
    return activeCaseId || localStorage.getItem('nyaya_active_case_id') || 'CASE-2024-DEL-0482';
  };

  // 2. Global case switcher
  window.osSwitchCase = async function(newCaseId) {
    if (!newCaseId || newCaseId === activeCaseId) return;
    localStorage.setItem('nyaya_active_case_id', newCaseId);
    activeCaseId = newCaseId;
    window.nyayaActiveCaseId = newCaseId;

    try {
      await fetch(`/api/cases/switch?case_id=${encodeURIComponent(newCaseId)}`, { method: 'POST' });
    } catch (e) {
      console.warn('[NYAYA-OS] Case switch network warning:', e);
    }

    // Update URL without full reload if supported, or reload with new param
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('case_id', newCaseId);
    window.location.href = currentUrl.toString();
  };

  // 3. Initialize dropdowns on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    const selector = document.getElementById('os-global-case-select');
    if (selector) {
      selector.value = activeCaseId;
    }
    const label = document.getElementById('os-active-case-label');
    if (label) {
      label.innerText = activeCaseId;
    }
  });
})();

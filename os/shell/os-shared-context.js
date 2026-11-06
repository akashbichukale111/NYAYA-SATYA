/**
 * NYAYA-SATYA OS — Shared Case Context & Multilingual Navigation Controller
 * Manages active case synchronization and real-time pan-India language translation
 * across all 13 application experiences.
 */

(function() {
  const urlParams = new URLSearchParams(window.location.search);

  // 1. Determine active case
  let activeCaseId = urlParams.get('case_id') || localStorage.getItem('nyaya_active_case_id') || 'CASE-2024-DEL-0482';
  localStorage.setItem('nyaya_active_case_id', activeCaseId);
  window.nyayaActiveCaseId = activeCaseId;

  window.osGetActiveCase = function() {
    return activeCaseId || localStorage.getItem('nyaya_active_case_id') || 'CASE-2024-DEL-0482';
  };

  // 2. Global Case Switcher
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

    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('case_id', newCaseId);
    window.location.href = currentUrl.toString();
  };

  // 3. Determine active language (Default: 'en' for English)
  let activeLang = urlParams.get('lang') || localStorage.getItem('nyaya_active_lang') || 'en';
  localStorage.setItem('nyaya_active_lang', activeLang);
  window.nyayaActiveLang = activeLang;

  window.osGetActiveLang = function() {
    return localStorage.getItem('nyaya_active_lang') || 'en';
  };

  // 4. Global Language Switcher
  window.osSetGlobalLang = function(newLang) {
    if (!newLang) return;
    activeLang = newLang;
    localStorage.setItem('nyaya_active_lang', newLang);
    window.nyayaActiveLang = newLang;

    // Synchronize all dropdowns on page
    document.querySelectorAll('.nyaya-lang-select, #global-lang-select, #lang-select').forEach(sel => {
      sel.value = newLang;
    });

    // Notify page translator
    if (typeof window.applyLanguageTranslations === 'function') {
      window.applyLanguageTranslations(newLang);
    }

    // Dispatch global event
    window.dispatchEvent(new CustomEvent('nyaya-language-changed', { detail: { language: newLang } }));
  };

  // 5. Guaranteed Audio & Speech Synthesis Engine
  window.osPlayVoiceGuidance = function(textToSpeak, langCode, onStartCb, onEndCb) {
    langCode = (langCode || activeLang || 'en').toLowerCase();

    // A. Web Audio API Synthetic Chime (Immediate guaranteed audible confirmation)
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        if (ctx.state === 'suspended') {
          ctx.resume();
        }
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.12); // A5

        gain.gain.setValueAtTime(0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.36);
      }
    } catch (e) {
      console.warn('[NYAYA-AUDIO] WebAudio chime failed:', e);
    }

    // B. SpeechSynthesis Speech Output
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }

      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.volume = 1.0;
      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      // Map language tags
      const langMap = {
        'hi': 'hi-IN',
        'mr': 'mr-IN',
        'kn': 'kn-IN',
        'ta': 'ta-IN',
        'bn': 'bn-IN',
        'en': 'en-IN'
      };
      utterance.lang = langMap[langCode] || 'en-IN';

      // Pick matching voice if installed
      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        let chosenVoice = voices.find(v => v.lang && v.lang.toLowerCase().replace('_', '-').startsWith(langCode));
        if (!chosenVoice && (langCode === 'mr' || langCode === 'kn' || langCode === 'ta' || langCode === 'bn')) {
          // Fallback to Hindi or Indian English voice for Indic pronunciation
          chosenVoice = voices.find(v => v.lang && (v.lang.includes('hi') || v.lang.includes('IN')));
        }
        if (!chosenVoice) {
          chosenVoice = voices.find(v => v.lang && v.lang.includes('en'));
        }
        if (chosenVoice) {
          utterance.voice = chosenVoice;
        }
      }

      if (typeof onStartCb === 'function') {
        utterance.onstart = onStartCb;
      }
      if (typeof onEndCb === 'function') {
        utterance.onend = onEndCb;
        utterance.onerror = onEndCb;
      }

      // Small 30ms timeout helps Chrome audio context wake up properly
      setTimeout(() => {
        try {
          window.speechSynthesis.speak(utterance);
        } catch (err) {
          console.error('[NYAYA-SPEECH] speak error:', err);
          if (typeof onEndCb === 'function') onEndCb();
        }
      }, 35);
    } else {
      alert('Audio Speech Synthesis is not supported in this browser.');
      if (typeof onEndCb === 'function') onEndCb();
    }
  };

  // Pre-load voices for Chrome
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = function() {
      window.speechSynthesis.getVoices();
    };
    window.speechSynthesis.getVoices();
  }

  // 6. Inject Language Selector into Master Headers on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    // Sync Case selector
    const selector = document.getElementById('os-global-case-select');
    if (selector) selector.value = activeCaseId;

    const label = document.getElementById('os-active-case-label');
    if (label) label.innerText = activeCaseId;

    // Inject language selector into .os-master-header if missing
    const masterRight = document.querySelector('.os-master-header .os-header-right');
    if (masterRight && !document.getElementById('header-lang-widget')) {
      const widget = document.createElement('div');
      widget.id = 'header-lang-widget';
      widget.style.cssText = 'display:flex; align-items:center; gap:6px; background:#121b2a; border:1px solid #2e4466; border-radius:6px; padding:3px 8px; margin-right:10px;';
      widget.innerHTML = `
        <span style="font-size:11px; color:#d4af37; font-weight:700;">🌐</span>
        <select class="nyaya-lang-select" onchange="osSetGlobalLang(this.value)" style="background:transparent; color:#fff; border:none; font-size:11.5px; font-weight:600; cursor:pointer; outline:none;">
          <option value="en" ${activeLang === 'en' ? 'selected' : ''}>English</option>
          <option value="hi" ${activeLang === 'hi' ? 'selected' : ''}>हिंदी (Hindi)</option>
          <option value="mr" ${activeLang === 'mr' ? 'selected' : ''}>मराठी (Marathi)</option>
          <option value="kn" ${activeLang === 'kn' ? 'selected' : ''}>ಕನ್ನಡ (Kannada)</option>
          <option value="ta" ${activeLang === 'ta' ? 'selected' : ''}>தமிழ் (Tamil)</option>
          <option value="bn" ${activeLang === 'bn' ? 'selected' : ''}>বাংলা (Bengali)</option>
        </select>
      `;
      masterRight.insertBefore(widget, masterRight.firstChild);
    }

    // Trigger initial language translation if provided
    if (typeof window.applyLanguageTranslations === 'function') {
      window.applyLanguageTranslations(activeLang);
    }
  });
})();

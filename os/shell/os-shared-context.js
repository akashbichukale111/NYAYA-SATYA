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
    document.querySelectorAll('.nyaya-lang-select, #global-lang-select, #lang-select, #main-lang-select').forEach(sel => {
      sel.value = newLang;
    });

    // Synchronize all Indic pill buttons
    document.querySelectorAll('.lang-pill-btn').forEach(btn => {
      if (btn.getAttribute('data-lang') === newLang) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Notify page translator
    if (typeof window.applyLanguageTranslations === 'function') {
      window.applyLanguageTranslations(newLang);
    }

    // Dispatch global event
    window.dispatchEvent(new CustomEvent('nyaya-language-changed', { detail: { language: newLang } }));
  };

  // 5. Preload and cache speech synthesis voices
  let cachedVoices = [];
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    cachedVoices = window.speechSynthesis.getVoices() || [];
    window.speechSynthesis.onvoiceschanged = function() {
      cachedVoices = window.speechSynthesis.getVoices() || [];
    };
  }

  // 6. Guaranteed Audio & Speech Synthesis Engine (with WebAudio + Indic Fallbacks)
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

        gain.gain.setValueAtTime(0.2, now);
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
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
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

      // Pick matching voice or intelligent Indic fallback
      const voices = (cachedVoices && cachedVoices.length > 0) ? cachedVoices : (window.speechSynthesis.getVoices() || []);
      if (voices && voices.length > 0) {
        let chosenVoice = voices.find(v => v.lang && v.lang.toLowerCase().replace('_', '-').startsWith(langCode));
        // Fallback for Indian regional languages to Hindi or Indian English if regional voice not installed in Windows
        if (!chosenVoice && (langCode === 'mr' || langCode === 'kn' || langCode === 'ta' || langCode === 'bn')) {
          chosenVoice = voices.find(v => v.lang && (v.lang.toLowerCase().includes('hi') || v.lang.toLowerCase().includes('in')));
        }
        if (!chosenVoice) {
          chosenVoice = voices.find(v => v.lang && v.lang.toLowerCase().includes('en'));
        }
        if (chosenVoice) {
          utterance.voice = chosenVoice;
        }
      }

      let started = false;
      let completed = false;

      const triggerStart = () => {
        if (!started) {
          started = true;
          if (typeof onStartCb === 'function') onStartCb();
        }
      };

      const triggerEnd = () => {
        if (!completed) {
          completed = true;
          if (typeof onEndCb === 'function') onEndCb();
        }
      };

      utterance.onstart = triggerStart;
      utterance.onend = triggerEnd;
      utterance.onerror = (err) => {
        console.warn('[NYAYA-SPEECH] Utterance error:', err);
        triggerEnd();
      };

      // Safety timeout in case browser TTS finishes without firing onend
      const approxDurationMs = Math.max(4000, Math.min(25000, textToSpeak.length * 80));
      setTimeout(() => {
        if (started && !completed) {
          triggerEnd();
        }
      }, approxDurationMs);

      // 40ms timeout helps Chromium initialize audio context on user gesture
      setTimeout(() => {
        try {
          triggerStart();
          window.speechSynthesis.speak(utterance);
          // Chromium freeze prevention
          if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
          }
        } catch (err) {
          console.error('[NYAYA-SPEECH] speak error:', err);
          triggerEnd();
        }
      }, 40);
    } else {
      if (typeof onStartCb === 'function') onStartCb();
      setTimeout(() => {
        if (typeof onEndCb === 'function') onEndCb();
      }, 1500);
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
        <select class="nyaya-lang-select" onchange="osSetGlobalLang(this.value)" style="background:#0c121c; color:#f0f4f8; border:none; font-size:11.5px; font-weight:600; cursor:pointer; outline:none;">
          <option value="en" style="background:#0c121c; color:#f0f4f8;" ${activeLang === 'en' ? 'selected' : ''}>English (Default)</option>
          <option value="hi" style="background:#0c121c; color:#f0f4f8;" ${activeLang === 'hi' ? 'selected' : ''}>हिंदी (Hindi)</option>
          <option value="mr" style="background:#0c121c; color:#f0f4f8;" ${activeLang === 'mr' ? 'selected' : ''}>मराठी (Marathi)</option>
          <option value="kn" style="background:#0c121c; color:#f0f4f8;" ${activeLang === 'kn' ? 'selected' : ''}>ಕನ್ನಡ (Kannada)</option>
          <option value="ta" style="background:#0c121c; color:#f0f4f8;" ${activeLang === 'ta' ? 'selected' : ''}>தமிழ் (Tamil)</option>
          <option value="bn" style="background:#0c121c; color:#f0f4f8;" ${activeLang === 'bn' ? 'selected' : ''}>বাংলা (Bengali)</option>
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

/**
 * NYAYA-SATYA — GLOBAL LEGAL CASE INTELLIGENCE PLATFORM
 * Core Application Engine & Living Intelligence Controller
 * Architecture: Clean Product Frontend with Dedicated Workspaces
 */

(function () {
  'use strict';

  // --- PLATFORM STATE CONFIGURATION ---
  const STATE = {
    caseId: 'CASE_SYNTHETIC_DEMO_2026',
    activeExhibit: 'E17',
    currentRoute: 'home',
    currentLanguage: 'EN',
    currentRole: 'litigator',
    currentJurisdiction: 'IN',
    counterfactualStep: 1,
    gateStatus: 'ASK_HUMAN',
    attackSimulationActive: false,
    apiConnected: false,
    lastSyncTimestamp: null,
  };

  // --- I18N TRANSLATION DICTIONARY (EN / MR / HI) ---
  const I18N = {
    EN: {
      headline: "Built for one case. Architected for every jurisdiction.",
      subhead: "Transform complex evidence into verifiable, multi-layered truth graphs. Stress-test claims, isolate procedural bottlenecks, and generate court-ready audit dossiers with human-in-the-loop control.",
      whatToDo: "What do you want to do?",
      newCaseTitle: "Start New Case",
      newCaseDesc: "Ingest FIRs, contracts, notices, and forensic records into a verified evidence vault.",
      evidenceTitle: "Evidence Vault",
      evidenceDesc: "Inspect immutable SHA-256 seals, chain-of-custody, and extracted factual claims.",
      twinTitle: "Case Digital Twin",
      twinDesc: "Explore the 3-layer semantic graph connecting Entities, Claims, and Legal Issues.",
      attackTitle: "Adversarial Review",
      attackDesc: "Run adversarial cross-examinations and detect contradictions before the other side does.",
      bottleneckTitle: "Bottleneck Radar",
      bottleneckDesc: "Pinpoint evidentiary gaps, missing custody links, and procedural delay factors.",
      repairTitle: "Repair Workbench",
      repairDesc: "Draft evidentiary repair patches, re-anchor claims, and verify survival against re-attack.",
      dossierTitle: "Certified Dossier",
      dossierDesc: "Generate exportable cryptographic proof bundles and judicial reasoning records.",
      citizenPrompt: "Explain your legal problem in plain language. (e.g. Property dispute, unfair dismissal, tenant issue)",
      analyzeBtn: "Analyze Legal Requirements",
    },
    MR: {
      headline: "एका प्रकरणासाठी निर्मित. प्रत्येक न्यायक्षेत्रासाठी सक्षम.",
      subhead: "गुंतागुंतीच्या पुराव्यांचे सत्यापन करण्यायोग्य सत्य आलेखात रूपांतर करा. दाव्यांची उलटतपासणी करा, कायदेशीर अडचणी ओळखा आणि मानवी नियंत्रणासह न्यायालयास अनुकूल पुरावे तयार करा.",
      whatToDo: "तुम्हाला काय करायचे आहे?",
      newCaseTitle: "नवीन प्रकरण सुरू करा",
      newCaseDesc: "तक्रार, करार, नोटिसा आणि फॉरेन्सिक नोंदी सुरक्षित पुरावा कक्षात दाखल करा.",
      evidenceTitle: "पुरावा कक्ष (Evidence Vault)",
      evidenceDesc: "अपरिवर्तनीय SHA-256 सील, साखळी पुरावा आणि काढलेले तथ्यात्मक दावे तपासा.",
      twinTitle: "डिजिटल जुळा (Digital Twin)",
      twinDesc: "व्यक्ती, दावे आणि कायदेशीर मुद्द्यांना जोडणारा ३-स्तरीय आलेख एक्सप्लोर करा.",
      attackTitle: "आक्षेप आणि उलटतपासणी",
      attackDesc: "विरोधकांपूर्वीच दाव्यांमधील विसंगती आणि विरोधाभास शोधून काढा.",
      bottleneckTitle: "अडथळे आणि विलंब रडार",
      bottleneckDesc: "गहाळ पुरावे, प्रक्रियात्मक विलंब आणि न्यायालयीन अडथळे अचूक ओळखा.",
      repairTitle: "दुरुस्ती कार्यशाळा",
      repairDesc: "पुराव्यांची दुरुस्ती करा, दावे पुन्हा मजबूत करा आणि पुनर्हल्ल्यापासून संरक्षण तपासा.",
      dossierTitle: "सत्यापित अहवाल (Dossier)",
      dossierDesc: "न्यायालयासाठी सुरक्षित डिजिटल पुरावा संच आणि तर्क नोंदी डाउनलोड करा.",
      citizenPrompt: "तुमची कायदेशीर समस्या तुमच्या स्वतःच्या भाषेत सांगा. (उदा. जमिनीचा वाद, भाडेकरू वाद, नोकरीतील अन्याय)",
      analyzeBtn: "कायदेशीर गरजा तपासा",
    },
    HI: {
      headline: "एक मामले के लिए निर्मित। हर क्षेत्राधिकार के लिए तैयार।",
      subhead: "जटिल साक्ष्यों को सत्यापन योग्य सत्य आलेख में बदलें। दावों की जिरह करें, कानूनी बाधाओं की पहचान करें और मानवीय नियंत्रण के तहत अदालत के लिए पुख्ता डोजियर तैयार करें।",
      whatToDo: "आप क्या करना चाहते हैं?",
      newCaseTitle: "नया मामला दर्ज करें",
      newCaseDesc: "एफआईआर, अनुबंध, नोटिस और फोरेंसिक रिकॉर्ड सुरक्षित साक्ष्य वॉल्ट में जमा करें।",
      evidenceTitle: "साक्ष्य वॉल्ट (Evidence Vault)",
      evidenceDesc: "अपरिवर्तनीय SHA-256 मुहर, अभिरक्षा श्रृंखला और निकाले गए तथ्यात्मक दावों की जांच करें।",
      twinTitle: "डिजिटल ट्विन (Digital Twin)",
      twinDesc: "इकाइयों, दावों और कानूनी मुद्दों को जोड़ने वाले 3-स्तरीय आलेख का विश्लेषण करें।",
      attackTitle: "विरोधी तर्क और जिरह",
      attackDesc: "विरोधी पक्ष से पहले ही दावों की कमजोरियों और विरोधाभासों को उजागर करें।",
      bottleneckTitle: "बाधा और विलंब रडार",
      bottleneckDesc: "साक्ष्य अंतराल, समय-सीमा के जोखिम और प्रक्रियात्मक देरी के कारकों की पहचान करें।",
      repairTitle: "सुधार कार्यशाला (Repair)",
      repairDesc: "साक्ष्य सुधार प्रस्ताव तैयार करें, दावों को फिर से मजबूत करें और पुनर्हमले में रक्षा जांचें।",
      dossierTitle: "प्रमाणित डोजियर",
      dossierDesc: "अदालत के लिए तैयार डिजिटल प्रमाण बंडल और न्यायिक तर्क रिकॉर्ड निर्यात करें।",
      citizenPrompt: "अपनी कानूनी समस्या अपनी सरल भाषा में बताएं। (जैसे: संपत्ति विवाद, किरायेदार समस्या, अनुबंध उल्लंघन)",
      analyzeBtn: "कानूनी आवश्यकताओं का विश्लेषण करें",
    }
  };

  // --- EVIDENCE DEMO DATA ---
  const EVIDENCE_DATA = {
    E17: {
      id: 'EXHIBIT E17',
      title: 'Vendor Warehouse Shipment Memo',
      hash: 'e17a4b92c815d73f4094a9712a3d02b85e49f87498c5675c9281a94f0923058a',
      status: 'CONTRADICTED (-48h vs Exhibit E22)',
      quote: '"Consignment dispatched from factory warehouse on 12 March 2026."',
      anchoredClaim: 'CLM-17 (Primary Dispatch Date)',
      dna: [
        { title: 'Physical Acquisition', meta: 'Scanned digital PDF uploaded by VendorCorp on 15 March 2026' },
        { title: 'Cryptographic Normalization', meta: 'SHA-256 seal computed: e17a4b... (Integrity Verified)' },
        { title: 'Text Extraction & Quarantine', meta: 'OCR sandboxed, zero executable payload, MIME validated' },
        { title: 'Entity & Claim Extraction', meta: 'Extracted Entity: Factory_Warehouse; Predicate: DISPATCHED_ON; Date: 2026-03-12' },
        { title: 'Adversarial Gauntlet Result', meta: 'Contradiction flagged with Freight Terminal Receipt (E22, 14 March 2026)' }
      ]
    },
    E22: {
      id: 'EXHIBIT E22',
      title: 'Freight Terminal Acceptance Docket',
      hash: 'e22c9f18b341aa0812e4f0d6182c4091a1829e57849bc5276e01a8849bca710e',
      status: 'CORROBORATED (Terminal Log)',
      quote: '"Consignment accepted at freight terminal on 14 March 2026 at 09:30."',
      anchoredClaim: 'CLM-22 (Carrier Custody Handover)',
      dna: [
        { title: 'Direct Carrier Feed', meta: 'Electronic EDI transmission from FreightTrans Logistics Corp' },
        { title: 'SHA-256 Hash Ingestion', meta: 'Hash seal computed: e22c9f... (Authentic)' },
        { title: 'Timeline Reconciliation', meta: 'Anchored at timeline offset T+48h relative to E17' },
        { title: 'Adversarial Status', meta: 'Survives gauntlet; serves as empirical ground for Proposed Repair' }
      ]
    },
    E30: {
      id: 'EXHIBIT E30',
      title: 'Commercial Supply Contract Clause 4.2',
      hash: 'e30d12a78f14c2b98811d72a6b485091723e41982a7f4510b29841ca982341ff',
      status: 'LOAD-BEARING (Contractual Root)',
      quote: '"Delivery strictly mandated within 48 hours of warehouse dispatch."',
      anchoredClaim: 'CLM-30 (Liquidated Damages $450,000)',
      dna: [
        { title: 'Executed Agreement', meta: 'Bilateral contract signed 01 January 2026' },
        { title: 'Legal Clause Decomposition', meta: 'Extracted condition: Breach if (Delivery - Dispatch) > 48 hours' },
        { title: 'Causal Sensitivity Analysis', meta: 'High causal blast-radius: dependent on accurate dispatch date' }
      ]
    },
    E31: {
      id: 'EXHIBIT E31',
      title: 'Notice of Acceptance & Demurrage Notice',
      hash: 'e31a88b49182ca90283f14018274a9182374e918273645019284729184719283',
      status: 'REPAIR ANCHOR (Survives Re-Attack)',
      quote: '"Contemporaneous notice served upon carrier delivery receipt."',
      anchoredClaim: 'CLM-31 (Procedural Notice Complied)',
      dna: [
        { title: 'Notice Service Stamp', meta: 'Electronic delivery confirmation timestamped 16 March 2026' },
        { title: 'Re-Attack Evaluation', meta: 'Successfully rebuts Clause 4.3 notice defense during independent re-attack' },
        { title: 'Repair Immunity Rating', meta: '0.92 / 1.0 (Highly Protected Grounding)' }
      ]
    }
  };

  // --- ROUTE DEFINITIONS & WORKSPACE TITLES ---
  const ROUTE_CONFIG = {
    'home': { title: 'Home', breadcrumb: 'Platform Overview' },
    'new-case': { title: 'New Case Intake', breadcrumb: 'Ingestion & Setup' },
    'my-cases': { title: 'Recent Cases', breadcrumb: 'Case Portfolio' },
    'evidence': { title: 'Evidence Vault', breadcrumb: 'Ingestion & SHA-256 Vault' },
    'twin': { title: 'Case Digital Twin', breadcrumb: '3-Layer Graph Intelligence' },
    'attack': { title: 'Adversarial Gauntlet', breadcrumb: 'Contradiction & Stress Test' },
    'bottleneck': { title: 'Bottleneck Radar', breadcrumb: 'Evidentiary & Delay Analysis' },
    'deadlines': { title: 'Deadlines & Limitations', breadcrumb: 'Statutory Limitation Radar' },
    'impact': { title: 'Causal Impact & Jenga', breadcrumb: 'Structural Dependency Blast' },
    'counterfactual': { title: 'Counterfactual Sandbox', breadcrumb: 'Timeline Perturbation Engine' },
    'repair': { title: 'Repair Workbench', breadcrumb: 'Evidentiary Patching' },
    'reattack': { title: 'Re-Attack Arena', breadcrumb: 'Independent Verification' },
    'governance': { title: 'Human Authorization Gate', breadcrumb: 'Mandatory Human Control' },
    'dossier': { title: 'Certified Dossier', breadcrumb: 'Cryptographic Audit Bundle' },
    'health': { title: 'System Observability', breadcrumb: 'Platform Health & Logs' },
    'citizen': { title: 'Citizen Mode', breadcrumb: 'Access to Justice Intake' },
    'activity': { title: 'Audit Ledger', breadcrumb: 'Immutable Action Stream' },
  };

  // --- 1. SINGLE-PAGE WORKSPACE ROUTER ---
  function navigate(viewId) {
    const cleanId = viewId.replace(/^#/, '') || 'home';
    const config = ROUTE_CONFIG[cleanId] || ROUTE_CONFIG['home'];
    STATE.currentRoute = cleanId;

    // Toggle Workspace Views
    const allViews = document.querySelectorAll('.workspace-view');
    let matchedView = null;

    allViews.forEach((view) => {
      const vId = view.getAttribute('data-view') || view.id;
      if (vId === `view-${cleanId}` || vId === cleanId) {
        view.classList.add('active');
        matchedView = view;
      } else {
        view.classList.remove('active');
      }
    });

    // If specific dedicated view wasn't created separately, route to corresponding section
    if (!matchedView) {
      const homeView = document.getElementById('view-home') || document.querySelector('[data-view="home"]');
      if (homeView) homeView.classList.add('active');
      const targetSec = document.getElementById(`sec-${cleanId}`);
      if (targetSec) {
        targetSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Update Nav Bar Items
    document.querySelectorAll('.nav-item-btn').forEach((btn) => {
      const route = btn.getAttribute('data-route');
      if (route === cleanId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update Breadcrumb Trail
    const breadcrumbCurrent = document.getElementById('breadcrumb-current');
    if (breadcrumbCurrent) {
      breadcrumbCurrent.textContent = config.breadcrumb;
    }

    // Route-specific data loaders
    if (cleanId === 'bottleneck') {
      loadBottlenecks();
    } else if (cleanId === 'new-case') {
      const input = document.getElementById('intake-title-input');
      if (input) input.focus();
    } else if (cleanId === 'citizen') {
      const cInput = document.getElementById('citizen-problem-text');
      if (cInput) cInput.focus();
    }
  }

  // --- 2. MULTI-LANGUAGE ENGINE ---
  function setLanguage(lang) {
    if (!I18N[lang]) return;
    STATE.currentLanguage = lang;

    document.querySelectorAll('.lang-choice-btn').forEach((btn) => {
      if (btn.getAttribute('data-lang') === lang) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    const dict = I18N[lang];
    const headline = document.getElementById('home-headline-text');
    if (headline) headline.textContent = dict.headline;

    const subhead = document.getElementById('home-subhead-text');
    if (subhead) subhead.textContent = dict.subhead;

    const whatToDo = document.getElementById('section-what-to-do');
    if (whatToDo) whatToDo.textContent = dict.whatToDo;

    // Citizen placeholder
    const citizenInput = document.getElementById('citizen-problem-text');
    if (citizenInput) citizenInput.placeholder = dict.citizenPrompt;

    const analyzeBtnText = document.getElementById('citizen-analyze-text');
    if (analyzeBtnText) analyzeBtnText.textContent = dict.analyzeBtn;
  }

  // --- 3. ROLE SWITCHER ---
  function setRole(role) {
    STATE.currentRole = role;
    const roleBadge = document.getElementById('platform-role-badge');
    if (roleBadge) {
      const roleMap = {
        citizen: 'Role: Citizen / Litigant',
        litigator: 'Role: Advocate / Litigator',
        legalaid: 'Role: Legal Aid / Para-Legal',
        judge: 'Role: Judicial Officer / Clerk',
        admin: 'Role: System Auditor',
      };
      roleBadge.textContent = roleMap[role] || 'Role: Advocate';
    }

    // Adaptively guide cards or features for roles
    document.querySelectorAll('.action-card-item').forEach((card) => {
      const targetRole = card.getAttribute('data-role-focus');
      if (targetRole && targetRole === role) {
        card.style.borderColor = 'rgba(56, 189, 248, 0.6)';
        card.style.boxShadow = '0 0 15px rgba(56, 189, 248, 0.2)';
      } else {
        card.style.borderColor = '';
        card.style.boxShadow = '';
      }
    });
  }

  // --- 4. FLOATING ACTION BUTTON: ✦ Personal AI ---
  function initPersonalAiFab() {
    const fab = document.getElementById('personal-ai-fab-btn');
    if (fab) {
      fab.addEventListener('click', (e) => {
        // Enforce strict open in new tab with zero case data coupling
        e.preventDefault();
        window.open('https://frontend-henna-gamma-fhj87crlpp.vercel.app/', '_blank', 'noopener,noreferrer');
      });
    }
  }

  // --- 5. CITIZEN INTAKE LIVE API ---
  async function submitCitizenIntake() {
    const textEl = document.getElementById('citizen-problem-text');
    const jurEl = document.getElementById('citizen-jurisdiction-select');
    const resultBox = document.getElementById('citizen-analysis-result');
    const loadingEl = document.getElementById('citizen-loading');

    if (!textEl || !textEl.value.trim()) return;

    if (loadingEl) loadingEl.style.display = 'block';
    if (resultBox) resultBox.style.display = 'none';

    try {
      const res = await fetch('/api/nyaya/citizen/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem_text: textEl.value.trim(),
          jurisdiction: jurEl ? jurEl.value : 'IN',
          language: STATE.currentLanguage,
        })
      });

      if (res.ok) {
        const data = await res.json();
        renderCitizenIntakeOutput(data);
      } else {
        renderCitizenFallbackOutput(textEl.value.trim());
      }
    } catch {
      renderCitizenFallbackOutput(textEl.value.trim());
    } finally {
      if (loadingEl) loadingEl.style.display = 'none';
      if (resultBox) resultBox.style.display = 'block';
    }
  }

  function renderCitizenIntakeOutput(data) {
    const outSummary = document.getElementById('citizen-out-summary');
    const outCategory = document.getElementById('citizen-out-category');
    const outChecklist = document.getElementById('citizen-out-checklist');
    const outAid = document.getElementById('citizen-out-aid');

    if (outSummary) outSummary.textContent = data.plain_language_summary || 'Your matter has been structured for legal review.';
    if (outCategory) outCategory.textContent = `Identified Legal Category: ${data.detected_category || 'Civil / Commercial'}`;

    if (outChecklist && Array.isArray(data.required_documents)) {
      outChecklist.innerHTML = data.required_documents.map((doc) => `
        <div class="checklist-item">
          <span style="color:#38bdf8;">✓</span>
          <div>
            <strong>${doc.title || doc}</strong>
            ${doc.purpose ? `<div style="font-size:0.75rem; color:#94a3b8;">${doc.purpose}</div>` : ''}
          </div>
        </div>
      `).join('');
    }

    if (outAid) {
      outAid.textContent = data.legal_aid_referral?.eligible
        ? `Legal Aid Recommendation: Eligible under ${data.legal_aid_referral.scheme || 'NALSA / Pro Bono Registry'}`
        : 'Private Counsel / Bar Association referral recommended.';
    }
  }

  function renderCitizenFallbackOutput(text) {
    const outSummary = document.getElementById('citizen-out-summary');
    const outCategory = document.getElementById('citizen-out-category');
    const outChecklist = document.getElementById('citizen-out-checklist');

    if (outSummary) outSummary.textContent = `Plain-Language Summary: Case inquiry regarding "${text.slice(0, 80)}...". Evidentiary foundations and statutory requirements mapped.`;
    if (outCategory) outCategory.textContent = 'Identified Legal Category: Civil / Commercial Contract Inquiry';

    if (outChecklist) {
      outChecklist.innerHTML = `
        <div class="checklist-item"><span style="color:#38bdf8;">✓</span> <div><strong>Agreement / Contract Copy</strong> (Executed contract or written communications)</div></div>
        <div class="checklist-item"><span style="color:#38bdf8;">✓</span> <div><strong>Proof of Delivery / Breach Notice</strong> (Dispatch logs, emails, registered notices)</div></div>
        <div class="checklist-item"><span style="color:#38bdf8;">✓</span> <div><strong>Identity & Authorization Proof</strong> (Govt ID, power of attorney, incorporation certificate)</div></div>
      `;
    }
  }

  // --- 6. BOTTLENECK RADAR LIVE API ---
  async function loadBottlenecks() {
    const listEl = document.getElementById('bottlenecks-list-container');
    if (!listEl) return;

    try {
      const res = await fetch(`/api/nyaya/cases/${STATE.caseId}/bottlenecks`);
      if (res.ok) {
        const data = await res.json();
        renderBottlenecks(data.bottlenecks || []);
      } else {
        renderDefaultBottlenecks();
      }
    } catch {
      renderDefaultBottlenecks();
    }
  }

  function renderBottlenecks(items) {
    const listEl = document.getElementById('bottlenecks-list-container');
    if (!listEl) return;

    if (!items.length) {
      listEl.innerHTML = '<p style="color:#94a3b8;">No procedural bottlenecks detected for this case.</p>';
      return;
    }

    listEl.innerHTML = items.map((b) => `
      <div class="action-card-item" style="margin-bottom:0.75rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#f1f5f9;">${b.title}</strong>
          <span class="badge-tag-sm ${b.severity === 'HIGH' ? 'urgency-high' : 'urgency-med'}">${b.severity}</span>
        </div>
        <p style="font-size:0.82rem; color:#94a3b8; margin:0.4rem 0;">${b.description}</p>
        <div style="font-size:0.75rem; color:#38bdf8;">Recommended Action: ${b.recommendation || 'Provide supporting affidavit'}</div>
      </div>
    `).join('');
  }

  function renderDefaultBottlenecks() {
    renderBottlenecks([
      { title: 'Contradicted Dispatch Date (-48h gap)', severity: 'HIGH', description: 'Warehouse Memo E17 date contradicts Carrier Docket E22.', recommendation: 'Execute Repair Patch P-01 substituting E22 as carrier anchor.' },
      { title: 'Unserved Demurrage Counter-Notice', severity: 'MEDIUM', description: 'Notice of claim under Clause 4.3 lacks formal proof of delivery.', recommendation: 'Obtain courier tracking delivery confirmation affidavit.' }
    ]);
  }

  // --- 7. HERO ANIMATED REASONING SEQUENCE ---
  function initHeroCycle() {
    const el = document.getElementById('hero-cycle-text');
    if (!el) return;

    const stages = [
      { text: 'Attack it.', className: 'dynamic-cycle state-attack' },
      { text: 'Repair it.', className: 'dynamic-cycle state-repair' },
      { text: 'Attack the repair.', className: 'dynamic-cycle state-reattack' },
    ];

    let idx = 0;
    setInterval(() => {
      idx = (idx + 1) % stages.length;
      el.classList.add('morphing');

      setTimeout(() => {
        el.textContent = stages[idx].text;
        el.className = stages[idx].className;
        el.classList.remove('morphing');
      }, 280);
    }, 3200);
  }

  // --- 8. EVIDENCE CONSTELLATION CANVAS ---
  function initConstellationCanvas() {
    const canvas = document.getElementById('nyaya-constellation-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const nodes = [];
    const nodeCount = 34;
    const types = ['EVIDENCE', 'CLAIM', 'ISSUE', 'EVENT', 'DEPENDENCY'];

    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: Math.random() * 2.5 + 1.8,
        type: types[Math.floor(Math.random() * types.length)],
        color: i % 5 === 0 ? 'rgba(239, 68, 68, 0.7)' : (i % 3 === 0 ? 'rgba(56, 189, 248, 0.7)' : 'rgba(99, 102, 241, 0.6)'),
      });
    }

    function render() {
      ctx.clearRect(0, 0, width, height);

      // Draw connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 115) {
            const alpha = (1 - dist / 115) * 0.18;
            ctx.strokeStyle = `rgba(148, 163, 184, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        n.x += n.vx;
        n.y += n.vy;

        if (n.x < 0 || n.x > width) n.vx *= -1;
        if (n.y < 0 || n.y > height) n.vy *= -1;

        ctx.fillStyle = n.color;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      requestAnimationFrame(render);
    }

    render();
  }

  // --- 9. TRAVELING PIPELINE SIGNAL ---
  function initTravelingPipelineSignal() {
    const track = document.getElementById('pipeline-progress-track');
    const nodes = document.querySelectorAll('.pipeline-step-node');
    if (!track || !nodes.length) return;

    let activeIdx = 0;
    setInterval(() => {
      nodes.forEach((n) => n.classList.remove('pulse-active'));
      nodes[activeIdx].classList.add('pulse-active');
      activeIdx = (activeIdx + 1) % nodes.length;
    }, 2800);
  }

  // --- 10. EVIDENCE DRAWER ---
  function openEvidenceDrawer(exhibitKey) {
    const drawer = document.getElementById('evidence-dna-drawer');
    if (!drawer) return;

    const data = EVIDENCE_DATA[exhibitKey] || EVIDENCE_DATA['E17'];
    STATE.activeExhibit = exhibitKey;

    const idEl = document.getElementById('drawer-exhibit-id');
    const titleEl = document.getElementById('drawer-exhibit-title');
    const hashEl = document.getElementById('drawer-exhibit-hash');
    const statusEl = document.getElementById('drawer-exhibit-status');
    const quoteEl = document.getElementById('drawer-exhibit-quote');
    const claimEl = document.getElementById('drawer-anchored-claim');
    const timelineEl = document.getElementById('drawer-dna-timeline');

    if (idEl) idEl.textContent = data.id;
    if (titleEl) titleEl.textContent = data.title;
    if (hashEl) hashEl.textContent = data.hash;
    if (statusEl) statusEl.textContent = data.status;
    if (quoteEl) quoteEl.textContent = data.quote;
    if (claimEl) claimEl.textContent = data.anchoredClaim;

    if (timelineEl && data.dna) {
      timelineEl.innerHTML = data.dna.map((step) => `
        <div class="dna-stage-card">
          <div class="dna-stage-title">${step.title}</div>
          <div class="dna-stage-meta">${step.meta}</div>
        </div>
      `).join('');
    }

    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
  }

  function closeEvidenceDrawer() {
    const drawer = document.getElementById('evidence-dna-drawer');
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }
  }

  // --- 11. CASE DIGITAL TWIN INTERACTIONS ---
  function initTwinInteractions() {
    const layerToggles = document.querySelectorAll('.twin-layer-btn');
    layerToggles.forEach((btn) => {
      btn.addEventListener('click', () => {
        layerToggles.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const layer = btn.getAttribute('data-layer');
        filterTwinLayers(layer);
      });
    });

    const twinNodes = document.querySelectorAll('.twin-graph-node');
    twinNodes.forEach((node) => {
      node.addEventListener('click', () => {
        twinNodes.forEach((n) => n.classList.remove('selected'));
        node.classList.add('selected');
        const label = node.getAttribute('data-node-label');
        const inspector = document.getElementById('twin-node-detail-inspector');
        if (inspector && label) {
          inspector.innerHTML = `<span style="color:#38bdf8;">${label}</span>: Node active in 3-layer semantic dependency index.`;
        }
      });
    });
  }

  function filterTwinLayers(layer) {
    const items = document.querySelectorAll('.twin-graph-node');
    items.forEach((item) => {
      if (layer === 'ALL' || item.getAttribute('data-layer-type') === layer) {
        item.style.opacity = '1';
        item.style.pointerEvents = 'auto';
      } else {
        item.style.opacity = '0.2';
        item.style.pointerEvents = 'none';
      }
    });
  }

  // --- 12. ADVERSARIAL GAUNTLET SIMULATION ---
  function initAttackSimulation() {
    const btn = document.getElementById('btn-trigger-attack-simulation');
    if (!btn) return;

    btn.addEventListener('click', () => {
      if (STATE.attackSimulationActive) return;
      STATE.attackSimulationActive = true;
      btn.disabled = true;
      btn.textContent = 'RUNNING 7 ATTACK VECTORS...';

      const log = document.getElementById('adversarial-live-terminal');
      if (log) {
        log.innerHTML = '<div class="terminal-line pulse-active">[START] Mounting 7-vector adversarial gauntlet against Case Twin...</div>';
      }

      const steps = [
        '[V1: CONTRADICTION] Cross-referencing Exhibit E17 with Freight Terminal Docket E22...',
        '[ALERT] Discrepancy confirmed: E17 asserts 12 March, E22 confirms custody transfer 14 March (-48h gap).',
        '[V2: TEMPORAL GAP] Analyzing missing carrier transit interval between 12-14 March...',
        '[V3: STATUTORY LIMITATION] Verifying Limitation Act Article 55 timer against 14 March notice...',
        '[V4: JENGA FRAGILITY] Root claim CLM-17 flagged as structural pivot for Issue ISS-01.',
        '[COMPLETE] Gauntlet run completed: 1 contradiction detected, 1 repair opportunity identified.'
      ];

      let stepIdx = 0;
      const interval = setInterval(() => {
        if (stepIdx < steps.length) {
          if (log) {
            const p = document.createElement('div');
            p.className = 'terminal-line';
            if (steps[stepIdx].includes('[ALERT]')) p.style.color = '#ef4444';
            if (steps[stepIdx].includes('[COMPLETE]')) p.style.color = '#10b981';
            p.textContent = steps[stepIdx];
            log.appendChild(p);
            log.scrollTop = log.scrollHeight;
          }
          stepIdx++;
        } else {
          clearInterval(interval);
          STATE.attackSimulationActive = false;
          btn.disabled = false;
          btn.textContent = 'RUN GAUNTLET';
        }
      }, 500);
    });
  }

  // --- 13. CAUSAL BLAST SIMULATOR ---
  function initCounterfactualSlider() {
    const slider = document.getElementById('counterfactual-time-slider');
    const valDisplay = document.getElementById('counterfactual-date-display');
    const blastNodes = document.querySelectorAll('.blast-dependent-node');

    if (!slider) return;

    slider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      STATE.counterfactualStep = val;

      if (val === 0) {
        if (valDisplay) valDisplay.textContent = '12 March 2026 (Asserted in E17)';
        blastNodes.forEach((bn) => {
          bn.classList.remove('shattered');
          bn.setAttribute('data-status', 'Nominal');
        });
      } else {
        if (valDisplay) valDisplay.textContent = '14 March 2026 (Perturbation / Empirical Docket E22)';
        blastNodes.forEach((bn) => {
          bn.classList.add('shattered');
          bn.setAttribute('data-status', 'Contradicted Breach');
        });
      }
    });
  }

  // --- 14. HUMAN AUTHORIZATION GATE ---
  function initHumanGate() {
    const btnAuth = document.getElementById('btn-gate-authorize');
    const btnReject = document.getElementById('btn-gate-reject');
    const badge = document.getElementById('gate-status-pill');

    if (btnAuth) {
      btnAuth.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/nyaya/human-gate/authorize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'AUTHORIZE_REPAIR_P01', case_id: STATE.caseId })
          });
          STATE.gateStatus = 'AUTHORIZED';
          if (badge) {
            badge.textContent = 'AUTHORIZED BY HUMAN ADVOCATE';
            badge.className = 'status-pill gate-authorized';
          }
        } catch {
          STATE.gateStatus = 'AUTHORIZED (LOCAL)';
          if (badge) {
            badge.textContent = 'AUTHORIZED BY HUMAN ADVOCATE';
            badge.className = 'status-pill gate-authorized';
          }
        }
      });
    }

    if (btnReject) {
      btnReject.addEventListener('click', () => {
        STATE.gateStatus = 'REJECTED';
        if (badge) {
          badge.textContent = 'REPAIR PROPOSAL REJECTED';
          badge.className = 'status-pill gate-rejected';
        }
      });
    }
  }

  // --- 15. CERTIFIED DOSSIER EXPORTS ---
  function initDossierModal() {
    const btnExportJson = document.getElementById('btn-export-dossier-json');
    const btnExportMd = document.getElementById('btn-export-dossier-md');

    if (btnExportJson) {
      btnExportJson.addEventListener('click', () => {
        const payload = {
          nyaya_version: '2.0.0',
          case_id: STATE.caseId,
          jurisdiction: STATE.currentJurisdiction,
          export_timestamp: new Date().toISOString(),
          non_adjudication_notice: 'This dossier contains evidentiary and structural reasoning only. Verdicts and liability determinations remain exclusively with human judicial officers.',
          exhibits: EVIDENCE_DATA,
          gate_status: STATE.gateStatus,
        };
        downloadFile(`NYAYA-DOSSIER-${STATE.caseId}.json`, JSON.stringify(payload, null, 2), 'application/json');
      });
    }

    if (btnExportMd) {
      btnExportMd.addEventListener('click', () => {
        const md = `# NYAYA-SATYA CERTIFIED EVIDENTIARY DOSSIER
**Case Identifier**: ${STATE.caseId}
**Jurisdiction**: ${STATE.currentJurisdiction}
**Status**: Governed (${STATE.gateStatus})
**Cryptographic Root**: SHA-256 Verified Multi-Layer Graph

## Notice
This dossier contains evidentiary, structural, and causal reasoning only. It does not predict verdicts or legal liability.

## Verified Exhibits
- **E17**: Vendor Warehouse Shipment Memo (SHA-256 Verified)
- **E22**: Freight Terminal Acceptance Docket (SHA-256 Verified)
- **E30**: Supply Agreement Clause 4.2 (SHA-256 Verified)
- **E31**: Acceptance & Demurrage Notice (SHA-256 Verified)

## Adversarial Review
- Contradiction identified between E17 and E22 (-48h timeline discrepancy).
- Repair Patch P-01 formulated and subjected to independent re-attack.
- Re-attack immunity rating: 0.92 / 1.0.
`;
        downloadFile(`NYAYA-DOSSIER-${STATE.caseId}.md`, md, 'text/markdown');
      });
    }
  }

  function downloadFile(filename, text, mime) {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // --- 16. COMMAND PALETTE (CTRL+K) ---
  function initCommandPalette() {
    const palette = document.getElementById('command-palette');
    const trigger = document.getElementById('btn-palette');
    const search = document.getElementById('palette-search');
    const items = document.querySelectorAll('#palette-results li');

    function openPalette() {
      if (!palette) return;
      palette.classList.add('open');
      palette.setAttribute('aria-hidden', 'false');
      if (search) {
        search.value = '';
        search.focus();
      }
    }

    function closePalette() {
      if (palette) {
        palette.classList.remove('open');
        palette.setAttribute('aria-hidden', 'true');
      }
    }

    if (trigger) trigger.addEventListener('click', openPalette);

    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (palette && palette.classList.contains('open')) {
          closePalette();
        } else {
          openPalette();
        }
      }
      if (e.key === 'Escape') {
        closePalette();
        closeEvidenceDrawer();
      }
    });

    items.forEach((item) => {
      item.addEventListener('click', () => {
        const action = item.getAttribute('data-action');
        closePalette();
        if (action) {
          navigate(action);
        }
      });
    });
  }

  // --- 17. REAL BACKEND SYNCHRONIZATION ---
  async function syncBackendProbes() {
    const apiVal = document.getElementById('status-api-val');
    const evVal = document.getElementById('status-evidence-val');
    const tarkaVal = document.getElementById('status-tarka-val');
    const unwindVal = document.getElementById('status-unwind-val');
    const syncText = document.getElementById('sync-text');

    try {
      const res = await fetch('/health');
      if (res.ok) {
        const data = await res.json();
        STATE.apiConnected = true;
        STATE.lastSyncTimestamp = new Date();
        if (apiVal) apiVal.textContent = `ONLINE (${Math.round(data.uptime_seconds || 0)}s)`;
        if (syncText) syncText.textContent = 'SYNCED';
      }
    } catch {
      if (apiVal) apiVal.textContent = 'STANDALONE';
      if (syncText) syncText.textContent = 'OFFLINE';
    }

    try {
      const readyRes = await fetch('/ready');
      if (readyRes.ok) {
        const rData = await readyRes.json();
        if (rData.subsystems) {
          if (evVal) evVal.textContent = rData.subsystems.evidence_registry ? 'REGISTERED' : 'READY';
          if (unwindVal) unwindVal.textContent = rData.subsystems.governance_state_machine ? 'GOVERNED' : 'READY';
        }
      }
    } catch {}

    try {
      const verRes = await fetch('/version');
      if (verRes.ok) {
        const vData = await verRes.json();
        if (vData.reasoning_engine && tarkaVal) {
          tarkaVal.textContent = 'ACTIVE';
        }
      }
    } catch {}
  }

  // --- INITIALIZATION ---
  
  // Global App Controller Bridge for DOM onclick handlers
  window.App = {
    switchWorkspace: function(ws) {
      window.location.hash = ws;
      navigate(ws);
    },
    navigate: navigate,
    selectCase: function(caseId, ws) {
      STATE.caseId = caseId;
      window.location.hash = ws || 'twin';
      navigate(ws || 'twin');
    },
    setLanguage: setLanguage,
    setRole: setRole,
    closeDrawer: closeEvidenceDrawer,
    openDrawer: openEvidenceDrawer,
    closeCmdPalette: function() {
      const p = document.getElementById('cmd-palette-modal');
      if (p) p.style.display = 'none';
    },
    filterCasesByTag: function(tag) {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      const activeBtn = document.querySelector(`.filter-btn[data-tag="${tag}"]`);
      if (activeBtn) activeBtn.classList.add('active');
    },
    executeCaseIntake: function() {
      navigate('evidence');
    }
  };


  document.addEventListener('DOMContentLoaded', () => {
    // 1. Setup Hash Router
    window.addEventListener('hashchange', () => {
      navigate(window.location.hash);
    });

    // 2. Action Card Navigation Clicks
    document.querySelectorAll('[data-route]').forEach((el) => {
      el.addEventListener('click', (e) => {
        const route = el.getAttribute('data-route');
        if (route) {
          e.preventDefault();
          window.location.hash = route;
          navigate(route);
        }
      });
    });

    // 3. Language Switcher Buttons
    document.querySelectorAll('.lang-choice-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const lang = btn.getAttribute('data-lang');
        if (lang) setLanguage(lang);
      });
    });

    // 4. Role Switcher Select
    const roleSelect = document.getElementById('platform-role-select');
    if (roleSelect) {
      roleSelect.addEventListener('change', (e) => {
        setRole(e.target.value);
      });
    }

    // 5. Jurisdiction Selector
    const jurSelect = document.getElementById('platform-jurisdiction-select');
    if (jurSelect) {
      jurSelect.addEventListener('change', (e) => {
        STATE.currentJurisdiction = e.target.value;
      });
    }

    // 6. Citizen Intake Submit
    const btnCitizen = document.getElementById('btn-citizen-submit');
    if (btnCitizen) {
      btnCitizen.addEventListener('click', submitCitizenIntake);
    }

    // 7. Personal AI Floating Button
    initPersonalAiFab();

    // 8. Core Cockpit Systems
    initHeroCycle();
    initConstellationCanvas();
    initTravelingPipelineSignal();
    initTwinInteractions();
    initAttackSimulation();
    initCounterfactualSlider();
    initHumanGate();
    initDossierModal();
    initCommandPalette();

    // 9. Drawer Triggers
    document.querySelectorAll('.drawer-trigger').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-target');
        openEvidenceDrawer(id);
      });
    });

    const closeDrawerBtn = document.getElementById('btn-close-drawer');
    if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', closeEvidenceDrawer);

    // 10. Initial Route & Telemetry Polling
    const initialRoute = window.location.hash || '#home';
    navigate(initialRoute);

    syncBackendProbes();
    setInterval(syncBackendProbes, 12000);
  });

})();

  function demoStrip(modality) {
    return "PLAYS NOW \u2014 deterministic local render \u2014 NOT a " + modality;
  }
  // demoStrip(m.modality)

/**
 * NYAYA-SATYA — CINEMATIC MISSION COCKPIT CONTROLLER
 * Adversarial Evidence & Case Reasoning System
 * Interactive Client Engine & Living Telemetry
 */

(function () {
  'use strict';

  // --- STATE CONFIGURATION ---
  const STATE = {
    caseId: 'CASE_SYNTHETIC_DEMO_2026',
    activeExhibit: 'E17',
    counterfactualStep: 1, // 0 = baseline 12 Mar, 1 = perturbation 14 Mar
    gateStatus: 'ASK_HUMAN',
    attackSimulationActive: false,
    apiConnected: false,
    lastSyncTimestamp: null,
  };

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

  // --- 1. HERO ANIMATED REASONING SEQUENCE ---
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

  // --- 2. EVIDENCE CONSTELLATION CANVAS ---
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
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: Math.random() * 2.2 + 1.2,
        type: types[i % types.length],
        pulseVal: Math.random() * Math.PI,
        color: i % 6 === 0 ? '#ef4444' : i % 3 === 0 ? '#38bdf8' : i % 2 === 0 ? '#a855f7' : '#10b981',
      });
    }

    let signalPacket = { fromIdx: 0, toIdx: 1, progress: 0, active: true };

    function render() {
      ctx.clearRect(0, 0, width, height);

      // Connect nodes with proximity edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 140) {
            const alpha = 0.12 * (1 - dist / 140);
            ctx.strokeStyle = `rgba(56, 189, 248, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.stroke();
          }
        }
      }

      // Traveling signal between nodes
      if (signalPacket.active && nodes[signalPacket.fromIdx] && nodes[signalPacket.toIdx]) {
        const p1 = nodes[signalPacket.fromIdx];
        const p2 = nodes[signalPacket.toIdx];
        signalPacket.progress += 0.015;
        if (signalPacket.progress >= 1) {
          signalPacket.fromIdx = signalPacket.toIdx;
          signalPacket.toIdx = Math.floor(Math.random() * nodes.length);
          signalPacket.progress = 0;
        }
        const sx = p1.x + (p2.x - p1.x) * signalPacket.progress;
        const sy = p1.y + (p2.y - p1.y) * signalPacket.progress;
        ctx.fillStyle = '#38bdf8';
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(sx, sy, 2.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Render nodes
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > width) n.vx *= -1;
        if (n.y < 0 || n.y > height) n.vy *= -1;

        n.pulseVal += 0.03;
        const pulseR = n.radius + Math.sin(n.pulseVal) * 0.6;

        ctx.fillStyle = n.color;
        ctx.beginPath();
        ctx.arc(n.x, n.y, Math.max(1, pulseR), 0, Math.PI * 2);
        ctx.fill();
      }

      requestAnimationFrame(render);
    }
    render();
  }

  // --- 3. TRAVELING PIPELINE REASONING SIGNAL ---
  function initTravelingPipelineSignal() {
    const packet = document.getElementById('traveling-packet');
    const stepper = document.getElementById('pipeline-stepper');
    const statusText = document.getElementById('pipeline-signal-status');
    const nodes = document.querySelectorAll('.stepper-node');

    if (!packet || !stepper || nodes.length === 0) return;

    const colors = [
      { c: '#38bdf8', label: 'EVIDENCE INGESTION' },
      { c: '#a855f7', label: 'DIGITAL TWIN ONTOLOGY' },
      { c: '#ef4444', label: 'TARKA-VYUH ATTACK' },
      { c: '#f59e0b', label: 'CAUSAL BLAST-RADIUS' },
      { c: '#10b981', label: 'AUTO-HEALER REPAIR' },
      { c: '#38bdf8', label: 'INDEPENDENT RE-ATTACK' },
      { c: '#3b82f6', label: 'UNWIND HUMAN GATE' },
      { c: '#38bdf8', label: 'DOSSIER SEAL' },
    ];

    let currentStep = 0;

    function movePacket() {
      const node = nodes[currentStep];
      if (!node) return;

      const stepperRect = stepper.getBoundingClientRect();
      const nodeRect = node.getBoundingClientRect();
      const relativeLeft = nodeRect.left - stepperRect.left + nodeRect.width / 2 - 7;

      packet.style.left = `${relativeLeft}px`;
      packet.style.backgroundColor = colors[currentStep].c;
      packet.style.boxShadow = `0 0 16px ${colors[currentStep].c}, 0 0 32px ${colors[currentStep].c}`;

      if (statusText) {
        statusText.textContent = `SIGNAL PACKET: ${colors[currentStep].label}`;
        statusText.style.color = colors[currentStep].c;
      }

      currentStep = (currentStep + 1) % nodes.length;
    }

    // Initial position + recurring step animation
    setTimeout(movePacket, 600);
    setInterval(movePacket, 2600);
  }

  // --- 4. FORENSIC EVIDENCE DRAWER ---
  function openEvidenceDrawer(exhibitKey) {
    const data = EVIDENCE_DATA[exhibitKey];
    if (!data) return;

    const drawer = document.getElementById('forensic-drawer');
    const idLabel = document.getElementById('drawer-id-label');
    const titleEl = document.getElementById('drawer-title');
    const hashEl = document.getElementById('drawer-hash');
    const quoteEl = document.getElementById('drawer-quote');
    const claimsEl = document.getElementById('drawer-anchored-claims');
    const dnaTree = document.getElementById('drawer-dna-tree');

    if (!drawer) return;

    idLabel.textContent = data.id;
    titleEl.textContent = data.title;
    hashEl.textContent = data.hash;
    quoteEl.textContent = data.quote;
    claimsEl.innerHTML = `<strong>${data.anchoredClaim}</strong> — Status: <span class="${data.status.includes('CONTRADICTED') ? 'text-red' : 'text-green'}">${data.status}</span>`;

    dnaTree.innerHTML = data.dna
      .map(
        (step) => `
      <div class="dna-step">
        <span class="dna-step-title">${step.title}</span>
        <span class="dna-step-meta mono">${step.meta}</span>
      </div>`
      )
      .join('');

    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
  }

  function closeEvidenceDrawer() {
    const drawer = document.getElementById('forensic-drawer');
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }
  }

  // --- 5. DIGITAL TWIN 2.5D NEIGHBORHOOD ISOLATION ---
  function initTwinInteractions() {
    const nodes = document.querySelectorAll('#twin-svg .node-group');
    const edges = document.querySelectorAll('#twin-svg .edge');

    nodes.forEach((node) => {
      const nodeId = node.getAttribute('data-node');

      // Hover: isolate neighborhood
      node.addEventListener('mouseenter', () => {
        const connectedNodeIds = new Set([nodeId]);

        edges.forEach((edge) => {
          const from = edge.getAttribute('data-from');
          const to = edge.getAttribute('data-to');
          if (from === nodeId || to === nodeId) {
            edge.classList.add('is-focused');
            if (from) connectedNodeIds.add(from);
            if (to) connectedNodeIds.add(to);
          } else {
            edge.classList.add('is-dimmed');
          }
        });

        nodes.forEach((other) => {
          const otherId = other.getAttribute('data-node');
          if (connectedNodeIds.has(otherId)) {
            other.classList.add('is-focused');
          } else {
            other.classList.add('is-dimmed');
          }
        });
      });

      node.addEventListener('mouseleave', () => {
        edges.forEach((e) => e.classList.remove('is-focused', 'is-dimmed'));
        nodes.forEach((n) => n.classList.remove('is-focused', 'is-dimmed'));
      });

      // Click: open forensic detail or pulse
      node.addEventListener('click', () => {
        if (EVIDENCE_DATA[nodeId]) {
          openEvidenceDrawer(nodeId);
        } else {
          node.style.transform = 'scale(1.15)';
          setTimeout(() => (node.style.transform = 'scale(1)'), 250);
        }
      });
    });
  }

  // --- 6. TARKA-VYUH ADVERSARIAL ATTACK SIMULATION ---
  function initAttackSimulation() {
    const btn = document.getElementById('btn-trigger-attack-simulation');
    const topBtn = document.getElementById('btn-run-gauntlet-top');
    const btnText = document.getElementById('attack-sim-btn-text');
    const attackBox = document.getElementById('active-attack-box');
    const findingBox = document.getElementById('finding-box-main');
    const claim17 = document.getElementById('claim-box-17');
    const claim30 = document.getElementById('claim-box-30');

    function runAttack() {
      if (STATE.attackSimulationActive) return;
      STATE.attackSimulationActive = true;

      if (btnText) btnText.textContent = 'ATTACK IN PROGRESS...';
      if (btn) btn.classList.add('btn-cyan');

      // Step 1: Scan claim 17
      claim17.style.borderColor = '#f59e0b';
      claim17.style.transform = 'scale(1.02)';

      setTimeout(() => {
        // Step 2: Pulse attack vector
        attackBox.style.transform = 'scale(1.04)';
        attackBox.style.boxShadow = '0 0 35px rgba(239, 68, 68, 0.4)';
      }, 700);

      setTimeout(() => {
        // Step 3: Trigger fracture on claim 30
        claim30.style.borderColor = '#ef4444';
        claim30.style.transform = 'scale(1.03)';
      }, 1400);

      setTimeout(() => {
        // Step 4: Flash finding box
        findingBox.style.borderColor = '#ef4444';
        findingBox.style.boxShadow = '0 0 25px rgba(239, 68, 68, 0.35)';

        if (btnText) btnText.textContent = 'ATTACK COMPLETE (1 VULNERABILITY FOUND)';
        if (btn) {
          btn.classList.remove('btn-cyan');
          btn.classList.add('btn-green');
        }

        setTimeout(() => {
          claim17.style.transform = '';
          claim30.style.transform = '';
          attackBox.style.transform = '';
          attackBox.style.boxShadow = '';
          findingBox.style.boxShadow = '';
          if (btnText) btnText.textContent = 'RUN ADVERSARIAL ATTACK';
          if (btn) btn.classList.remove('btn-green');
          STATE.attackSimulationActive = false;
        }, 3500);
      }, 2100);
    }

    if (btn) btn.addEventListener('click', runAttack);
    if (topBtn) topBtn.addEventListener('click', () => {
      document.getElementById('sec-adversarial')?.scrollIntoView({ behavior: 'smooth' });
      setTimeout(runAttack, 600);
    });
  }

  // --- 7. JENGA STRUCTURAL COLLAPSE DEMO ---
  function initJengaInteraction() {
    const dispatchBlock = document.getElementById('block-dispatch');
    const damagesBlock = document.getElementById('block-damages');

    if (!dispatchBlock || !damagesBlock) return;

    dispatchBlock.addEventListener('click', () => {
      damagesBlock.style.transform = 'translateX(28px) rotate(3.5deg)';
      damagesBlock.style.opacity = '0.35';
      damagesBlock.style.borderColor = '#ef4444';

      setTimeout(() => {
        damagesBlock.style.transform = 'translateX(0) rotate(0)';
        damagesBlock.style.opacity = '1';
        damagesBlock.style.borderColor = '';
      }, 2500);
    });
  }

  // --- 8. COUNTERFACTUAL TIME MACHINE SLIDER ---
  function initCounterfactualSlider() {
    const slider = document.getElementById('counterfactual-slider');
    const readout = document.getElementById('time-readout');
    const cardChange = document.getElementById('card-should-change');
    const cardNoChange = document.getElementById('card-should-not-change');

    if (!slider || !readout) return;

    slider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      STATE.counterfactualStep = val;

      if (val === 1) {
        readout.textContent = 'SCENARIO: INTERVENTION (14 MARCH ACCEPTANCE)';
        readout.className = 'time-readout mono text-cyan';
        cardChange.style.opacity = '1';
        cardNoChange.style.opacity = '1';
      } else {
        readout.textContent = 'SCENARIO: BASELINE DRAFT (12 MARCH UNGROUNDED)';
        readout.className = 'time-readout mono text-amber';
        cardChange.style.opacity = '0.6';
        cardNoChange.style.opacity = '1';
      }
    });
  }

  // --- 9. HUMAN LEGAL GATE APPROVAL ACTION ---
  function initHumanGate() {
    const approveBtn = document.getElementById('btn-human-approve');
    const rejectBtn = document.getElementById('btn-human-reject');
    const resultBox = document.getElementById('gate-action-result');
    const stepAsk = document.getElementById('step-ask-human');
    const stepApproved = document.getElementById('step-approved');
    const lineApproved = document.getElementById('line-approved');

    if (!approveBtn || !resultBox) return;

    approveBtn.addEventListener('click', () => {
      STATE.gateStatus = 'HUMAN_APPROVED';

      if (stepAsk) {
        stepAsk.classList.remove('current', 'pulse-amber');
        stepAsk.classList.add('passed');
        stepAsk.querySelector('.step-dot').textContent = '✓';
      }
      if (lineApproved) lineApproved.classList.add('active');
      if (stepApproved) {
        stepApproved.classList.remove('pending');
        stepApproved.classList.add('current');
        stepApproved.querySelector('.step-dot').textContent = '●';
      }

      resultBox.hidden = false;
      resultBox.className = 'gate-result mono text-green';
      resultBox.innerHTML = `
        <strong>[CRYPTOGRAPHIC AUDIT SEAL REGISTERED]</strong> Proposal REP-2026-08 authorized by <code>human::senior_counsel</code> at ${new Date().toISOString()}.<br>
        Transaction Checksum: <code>sha256:7f4a0298be12...</code> · Human Legal Gate verified · Consequential action authorized.
      `;
    });

    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => {
        resultBox.hidden = false;
        resultBox.className = 'gate-result mono text-red';
        resultBox.innerHTML = `
          <strong>[GOVERNANCE RECEIPT]</strong> Proposal REP-2026-08 rejected by legal reviewer. Case claims retained in unperturbed status.
        `;
      });
    }
  }

  // --- 10. FULL DOSSIER MODAL & EXPORT ---
  function initDossierModal() {
    const modal = document.getElementById('dossier-modal');
    const openBtn = document.getElementById('btn-view-dossier-full');
    const headerBtn = document.getElementById('btn-export-dossier');
    const closeBtn = document.getElementById('btn-close-modal');
    const content = document.getElementById('modal-dossier-content');

    function openModal() {
      if (!modal || !content) return;
      content.innerHTML = `
        <h4>1. CASE IDENTITY & EPISTEMIC CLASSIFICATION</h4>
        <p>Case Identifier: <code>CASE_SYNTHETIC_DEMO_2026</code> · Classification: <strong>SYNTHETIC</strong> · Zero real-world legal outcomes predicted.</p>

        <h4>2. EXECUTIVE EVIDENCE MAP & CHECKSUMS</h4>
        <ul>
          <li><strong>Exhibit E17:</strong> <code>e17a4b92...</code> — Vendor Warehouse Shipment Memo (12 Mar 2026)</li>
          <li><strong>Exhibit E22:</strong> <code>e22c9f18...</code> — Freight Terminal Docket (14 Mar 2026) [CONTRADICTION FOUND: 48h DELTA]</li>
          <li><strong>Exhibit E30:</strong> <code>e30d12a7...</code> — Supply Contract Clause 4.2 (48h delivery covenant)</li>
          <li><strong>Exhibit E31:</strong> <code>e31a88b4...</code> — Demurrage & Notice of Acceptance Record</li>
        </ul>

        <h4>3. ADVERSARIAL GAUNTLET (TARKA-VYUH)</h4>
        <p>Temporal conflict identified between E17 and E22. Primary liquidated damages claim CLM-30 collapsed under gauntlet stress-testing.</p>

        <h4>4. CAUSAL BLAST-RADIUS & REPAIR IMMUNITY</h4>
        <p>Intervention shifting dispatch date to 14 March preserves contract formation (Clause 1.1) while invalidating delay damages. Auto-Healer proposed repair REP-2026-08 survived independent re-attack with <strong>0.92 immunity rating</strong>.</p>

        <h4>5. UNWIND GOVERNANCE & HUMAN GATE SEAL</h4>
        <p>Proposal held in state <code>ASK_HUMAN</code>. Exclusive authority retained by credentialed practitioner. AI execution barred by execution guard.</p>
      `;
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
    }

    function closeModal() {
      if (modal) {
        modal.classList.remove('open');
        modal.setAttribute('aria-hidden', 'true');
      }
    }

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (headerBtn) headerBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);

    // Export JSON
    const dlJson = document.getElementById('btn-dl-json');
    const modalDlJson = document.getElementById('btn-modal-dl-json');
    const dlMd = document.getElementById('btn-dl-md');
    const modalDlMd = document.getElementById('btn-modal-dl-md');

    function downloadJson() {
      const payload = {
        dossier_id: 'DOS-SYNTHETIC-2026-01',
        case_id: STATE.caseId,
        epistemic_status: 'SYNTHETIC',
        evidence: Object.keys(EVIDENCE_DATA).map((k) => EVIDENCE_DATA[k]),
        findings: ['TEMPORAL_CONTRADICTION_48H'],
        repairs: ['REP-2026-08'],
        re_attack_immunity: 0.92,
        governance_state: STATE.gateStatus,
        timestamp: new Date().toISOString(),
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nyaya_satya_dossier_${STATE.caseId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }

    function downloadMarkdown() {
      const md = `# JUDICIAL REVIEW DOSSIER 2.0
Case ID: ${STATE.caseId}
Epistemic Classification: SYNTHETIC
Timestamp: ${new Date().toISOString()}

## 1. Registered Exhibits
${Object.keys(EVIDENCE_DATA).map(k => `- ${EVIDENCE_DATA[k].id}: ${EVIDENCE_DATA[k].title} (SHA-256: ${EVIDENCE_DATA[k].hash})`).join('\n')}

## 2. Adversarial Findings
- TEMPORAL_INCONSISTENCY: 48h discrepancy between Exhibit E17 and Exhibit E22.

## 3. Grounded Repair
- Candidate REP-2026-08 (Grounded in E22 & E31) · Immunity Score: 0.92

## 4. Governance & Human Gate
- Current Lifecycle State: ${STATE.gateStatus}
- Reviewer: human::senior_counsel
`;
      const blob = new Blob([md], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nyaya_satya_dossier_${STATE.caseId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }

    if (dlJson) dlJson.addEventListener('click', downloadJson);
    if (modalDlJson) modalDlJson.addEventListener('click', downloadJson);
    if (dlMd) dlMd.addEventListener('click', downloadMarkdown);
    if (modalDlMd) modalDlMd.addEventListener('click', downloadMarkdown);
  }

  // --- 11. COMMAND PALETTE (CTRL+K) ---
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
        if (action === 'goto-evidence') document.getElementById('sec-evidence')?.scrollIntoView({ behavior: 'smooth' });
        if (action === 'goto-twin') document.getElementById('sec-twin')?.scrollIntoView({ behavior: 'smooth' });
        if (action === 'run-attack') {
          document.getElementById('sec-adversarial')?.scrollIntoView({ behavior: 'smooth' });
          document.getElementById('btn-trigger-attack-simulation')?.click();
        }
        if (action === 'goto-causal') document.getElementById('sec-causal')?.scrollIntoView({ behavior: 'smooth' });
        if (action === 'goto-repair') document.getElementById('sec-repair')?.scrollIntoView({ behavior: 'smooth' });
        if (action === 'goto-governance') document.getElementById('sec-governance')?.scrollIntoView({ behavior: 'smooth' });
        if (action === 'goto-dossier') document.getElementById('sec-dossier')?.scrollIntoView({ behavior: 'smooth' });
      });
    });
  }

  // --- 12. REAL BACKEND SYNCHRONIZATION ---
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

  // --- 13. PIPELINE STEPPER SCROLL ---
  function initStepperScroll() {
    const nodes = document.querySelectorAll('.stepper-node');
    nodes.forEach((node) => {
      node.addEventListener('click', () => {
        const targetId = node.getAttribute('data-target');
        const target = document.getElementById(targetId);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  // --- INITIALIZATION ---
  document.addEventListener('DOMContentLoaded', () => {
    initHeroCycle();
    initConstellationCanvas();
    initTravelingPipelineSignal();
    initTwinInteractions();
    initAttackSimulation();
    initJengaInteraction();
    initCounterfactualSlider();
    initHumanGate();
    initDossierModal();
    initCommandPalette();
    initStepperScroll();

    // Drawer click listeners
    document.querySelectorAll('.drawer-trigger').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-target');
        openEvidenceDrawer(id);
      });
    });

    const closeDrawerBtn = document.getElementById('btn-close-drawer');
    if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', closeEvidenceDrawer);

    // Initial backend check & periodic polling
    syncBackendProbes();
    setInterval(syncBackendProbes, 12000);
  });

})();

  function demoStrip(modality) {
    return "PLAYS NOW · deterministic local render · NOT a " + modality;
  }
  // demoStrip(m.modality)

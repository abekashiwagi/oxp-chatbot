document.addEventListener('DOMContentLoaded', () => {

  // Mobile menu toggle
  const menuBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', () => {
      mobileMenu.classList.toggle('hidden');
    });
  }

  // Floor plan filter (units.html)
  const filterBtns = document.querySelectorAll('.filter-btn');
  const unitCards = document.querySelectorAll('.unit-card');
  const unitCount = document.getElementById('unit-count');
  const emptyState = document.getElementById('empty-state');
  const unitGrid = document.getElementById('unit-grid');

  if (filterBtns.length && unitCards.length) {
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;

        filterBtns.forEach(b => {
          b.classList.remove('active', 'bg-primary', 'text-white', 'border-primary');
          b.classList.add('text-ink-muted');
        });
        btn.classList.add('active', 'bg-primary', 'text-white', 'border-primary');
        btn.classList.remove('text-ink-muted');

        let visible = 0;
        unitCards.forEach(card => {
          const match = filter === 'all' || card.dataset.type === filter;
          card.classList.toggle('hidden-filtered', !match);
          if (match) visible++;
        });

        if (unitCount) unitCount.textContent = visible;
        if (emptyState && unitGrid) {
          emptyState.classList.toggle('hidden', visible > 0);
          unitGrid.classList.toggle('hidden', visible === 0);
        }
      });
    });
  }

  // ============================================================
  // Apply page: Tab switching, multi-step create, password logic
  // ============================================================

  const tabBtns = document.querySelectorAll('.tab-btn');
  const panelCreate = document.getElementById('panel-create');
  const panelLogin = document.getElementById('panel-login');
  const createLoginLink = document.getElementById('create-login-link');

  function switchTab(tabName) {
    tabBtns.forEach(btn => {
      const isActive = btn.dataset.tab === tabName;
      btn.classList.toggle('bg-white', isActive);
      btn.classList.toggle('text-primary', isActive);
      btn.classList.toggle('shadow-sm', isActive);
      btn.classList.toggle('text-ink-muted', !isActive);
    });

    if (panelCreate) panelCreate.classList.toggle('hidden', tabName !== 'create');
    if (panelLogin) panelLogin.classList.toggle('hidden', tabName !== 'login');
    if (createLoginLink) createLoginLink.classList.toggle('hidden', tabName !== 'create');
  }

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  const switchToCreate = document.getElementById('switch-to-create');
  const switchToLogin = document.getElementById('switch-to-login');
  if (switchToCreate) switchToCreate.addEventListener('click', () => switchTab('create'));
  if (switchToLogin) switchToLogin.addEventListener('click', () => switchTab('login'));

  const routesSwitchToCreate = document.getElementById('routes-switch-to-create');
  const routesSwitchToLogin = document.getElementById('routes-switch-to-login');
  if (routesSwitchToCreate) routesSwitchToCreate.addEventListener('click', () => switchTab('create'));
  if (routesSwitchToLogin) routesSwitchToLogin.addEventListener('click', () => switchTab('login'));

  // --- Create Account: Step Navigation ---

  const step1 = document.getElementById('step-1');
  const step2 = document.getElementById('step-2');
  const btnNext = document.getElementById('btn-next-step');
  const btnBack = document.getElementById('btn-back-step');
  const appOptions = document.querySelectorAll('.app-option');
  const selectedAppLabel = document.getElementById('selected-app-label');

  let selectedApp = null;

  const appLabels = {
    standard: 'Standard Application',
    roommate: 'Roommate Application',
  };

  appOptions.forEach(opt => {
    opt.addEventListener('click', () => {
      selectedApp = opt.dataset.app;

      appOptions.forEach(o => {
        const isSelected = o === opt;
        o.classList.toggle('border-cta', isSelected);
        o.classList.toggle('bg-cta/5', isSelected);
        o.classList.toggle('border-transparent', !isSelected);
        o.querySelector('.app-check').classList.toggle('hidden', !isSelected);
      });

      if (btnNext) btnNext.disabled = false;
    });
  });

  function goToStep(step) {
    if (step === 2) {
      step1.classList.add('hidden');
      step2.classList.remove('hidden');
      if (selectedAppLabel) selectedAppLabel.textContent = appLabels[selectedApp] || selectedApp;
    } else {
      step2.classList.add('hidden');
      step1.classList.remove('hidden');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (btnNext) btnNext.addEventListener('click', () => { if (selectedApp) goToStep(2); });
  if (btnBack) btnBack.addEventListener('click', () => goToStep(1));

  // ============================================================
  // Apply Routes page: Questionnaire Logic (apply-routes.html)
  // ============================================================

  const routeQ1 = document.getElementById('route-q1');
  const routeQ2 = document.getElementById('route-q2');
  const routeResult = document.getElementById('route-result');
  const routeCreateAccount = document.getElementById('route-create-account');
  const routeResultLabel = document.getElementById('route-result-label');
  const routeAnswers = document.querySelectorAll('.route-answer');
  const btnRouteBackQ1 = document.getElementById('btn-route-back-q1');
  const btnRouteContinue = document.getElementById('btn-route-continue');
  const btnRouteRestart = document.getElementById('btn-route-back-restart');
  const btnRouteBackResult = document.getElementById('btn-route-back-result');
  const routeSelectedAppLabel = document.getElementById('route-selected-app-label');

  let routeData = { isStudent: null, needsGuarantor: null };

  const routeSteps = [routeQ1, routeQ2, routeResult, routeCreateAccount];

  function showRouteStep(step) {
    routeSteps.forEach(el => { if (el) el.classList.add('hidden'); });
    if (step === 'q1' && routeQ1) routeQ1.classList.remove('hidden');
    if (step === 'q2' && routeQ2) routeQ2.classList.remove('hidden');
    if (step === 'result' && routeResult) routeResult.classList.remove('hidden');
    if (step === 'create' && routeCreateAccount) routeCreateAccount.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function resetRoutes() {
    routeData = { isStudent: null, needsGuarantor: null };
    routeAnswers.forEach(btn => {
      btn.classList.remove('border-cta', 'bg-cta/5');
      btn.classList.add('border-border');
      const check = btn.querySelector('.route-check');
      if (check) check.classList.add('hidden');
    });
    showRouteStep('q1');
  }

  function getRoutedAppLabel() {
    if (routeData.isStudent && routeData.needsGuarantor) return 'Student Application (with Guarantor)';
    if (routeData.isStudent) return 'Student Application';
    return 'Standard Application';
  }

  routeAnswers.forEach(btn => {
    btn.addEventListener('click', () => {
      const question = btn.dataset.question;
      const answer = btn.dataset.answer;

      document.querySelectorAll(`.route-answer[data-question="${question}"]`).forEach(b => {
        const isSelected = b === btn;
        b.classList.toggle('border-cta', isSelected);
        b.classList.toggle('bg-cta/5', isSelected);
        b.classList.toggle('border-border', !isSelected);
        const check = b.querySelector('.route-check');
        if (check) check.classList.toggle('hidden', !isSelected);
      });

      if (question === 'q1') {
        routeData.isStudent = answer === 'yes';
        setTimeout(() => {
          if (routeData.isStudent) {
            showRouteStep('q2');
          } else {
            if (routeResultLabel) routeResultLabel.textContent = getRoutedAppLabel();
            showRouteStep('result');
          }
        }, 350);
      }

      if (question === 'q2') {
        routeData.needsGuarantor = answer === 'yes';
        setTimeout(() => {
          if (routeResultLabel) routeResultLabel.textContent = getRoutedAppLabel();
          showRouteStep('result');
        }, 350);
      }
    });
  });

  if (btnRouteBackQ1) btnRouteBackQ1.addEventListener('click', () => showRouteStep('q1'));
  if (btnRouteRestart) btnRouteRestart.addEventListener('click', () => resetRoutes());

  if (btnRouteContinue) {
    btnRouteContinue.addEventListener('click', () => {
      if (routeSelectedAppLabel) routeSelectedAppLabel.textContent = getRoutedAppLabel();
      showRouteStep('create');
    });
  }

  if (btnRouteBackResult) btnRouteBackResult.addEventListener('click', () => showRouteStep('result'));

  // --- Password show/hide toggle ---

  document.querySelectorAll('.toggle-pw').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('input');
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      btn.querySelector('.pw-show').classList.toggle('hidden', isPassword);
      btn.querySelector('.pw-hide').classList.toggle('hidden', !isPassword);
    });
  });

  // --- Password strength validation ---

  const pwInput = document.getElementById('ca-password');
  const confirmInput = document.getElementById('ca-confirm-password');
  const mismatchMsg = document.getElementById('pw-mismatch');

  const rules = {
    'pw-length':  (v) => v.length >= 8,
    'pw-number':  (v) => /\d/.test(v),
    'pw-lower':   (v) => /[a-z]/.test(v),
    'pw-upper':   (v) => /[A-Z]/.test(v),
    'pw-special': (v) => /[!@#$%^&*()_+\-]/.test(v),
  };

  function validatePassword() {
    if (!pwInput) return;
    const val = pwInput.value;

    Object.entries(rules).forEach(([id, test]) => {
      const el = document.getElementById(id);
      if (!el) return;
      const passed = test(val);
      const icon = el.querySelector('.rule-icon');
      const checkSvg = el.querySelector('.check-icon');

      if (passed) {
        el.classList.remove('text-ink-muted');
        el.classList.add('text-success');
        icon.classList.remove('border-border');
        icon.classList.add('bg-success', 'border-success');
        checkSvg.classList.remove('hidden');
      } else {
        el.classList.add('text-ink-muted');
        el.classList.remove('text-success');
        icon.classList.add('border-border');
        icon.classList.remove('bg-success', 'border-success');
        checkSvg.classList.add('hidden');
      }
    });

    validateConfirm();
  }

  function validateConfirm() {
    if (!confirmInput || !pwInput || !mismatchMsg) return;
    if (confirmInput.value.length === 0) {
      mismatchMsg.classList.add('hidden');
      confirmInput.classList.remove('border-destructive');
      return;
    }
    const match = pwInput.value === confirmInput.value;
    mismatchMsg.classList.toggle('hidden', match);
    confirmInput.classList.toggle('border-destructive', !match);
    confirmInput.classList.toggle('border-border', match);
  }

  if (pwInput) pwInput.addEventListener('input', validatePassword);
  if (confirmInput) confirmInput.addEventListener('input', validateConfirm);

  // --- Form submissions ---

  document.querySelectorAll('#login-form, #routes-login-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      btn.textContent = 'Signing in...';
      btn.disabled = true;
      btn.classList.add('opacity-70');

      setTimeout(() => {
        btn.textContent = 'Signed In!';
        btn.classList.remove('opacity-70', 'bg-cta', 'hover:bg-blue-700');
        btn.classList.add('bg-primary');
      }, 1200);
    });
  });

  const createForm = document.getElementById('create-account-form');
  if (createForm) {
    createForm.addEventListener('submit', (e) => {
      e.preventDefault();

      if (pwInput && confirmInput && pwInput.value !== confirmInput.value) {
        validateConfirm();
        confirmInput.focus();
        return;
      }

      const allPassed = Object.values(rules).every(test => test(pwInput ? pwInput.value : ''));
      if (!allPassed) {
        pwInput.focus();
        return;
      }

      const btn = createForm.querySelector('button[type="submit"]');
      btn.textContent = 'Creating Account...';
      btn.disabled = true;
      btn.classList.add('opacity-70');

      setTimeout(() => {
        btn.textContent = 'Account Created!';
        btn.classList.remove('opacity-70', 'bg-cta', 'hover:bg-blue-700');
        btn.classList.add('bg-primary');
      }, 1500);
    });
  }

});

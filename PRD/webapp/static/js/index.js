/* ── Count-up animation for stat numbers ── */
function countUp(el, target, duration) {
    if (!el || !target) return;
    var start = performance.now();
    function step(now) {
        var p    = Math.min((now - start) / duration, 1);
        var ease = 1 - Math.pow(1 - p, 3); // ease-out cubic
        var val  = Math.round(target * ease);
        if      (target >= 1e6) el.textContent = (val / 1e6).toFixed(1) + 'M';
        else if (target >= 1e3) el.textContent = Math.round(val / 1e3)  + 'k';
        else                    el.textContent = val.toLocaleString();
        if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

/* ── Scroll-reveal: add .reveal class via JS (graceful degradation without JS) ── */
(function () {
    /* Targets: section labels, tool cards, coverage metrics, state buttons */
    document.querySelectorAll(
        '.section-eyebrow, .section-heading, .section-lead, .coverage-metric'
    ).forEach(function (el) { el.classList.add('reveal'); });

    /* Stagger tool cards */
    document.querySelectorAll('.tool-card').forEach(function (el, i) {
        el.classList.add('reveal');
        el.style.transitionDelay = (i * 0.1) + 's';
    });

    /* Stagger coverage metrics */
    document.querySelectorAll('.coverage-metric').forEach(function (el, i) {
        el.style.transitionDelay = (i * 0.07) + 's';
    });

    /* IntersectionObserver fires reveal */
    var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
            if (e.isIntersecting) {
                e.target.classList.add('visible');
                io.unobserve(e.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -32px 0px' });

    document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
})();

/* ── Number formatter ── */
function fmt(n) {
    if (!n && n !== 0) return '—';
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(0) + 'k';
    return n.toLocaleString();
}

function setTxt(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

/* ── Stats API fetch + state grid + modal creation ── */
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        // Stats band — animated count-up
        countUp(document.getElementById('sb-addresses'), stats.total_addresses, 1400);
        countUp(document.getElementById('sb-localities'), stats.total_localities, 1200);
        countUp(document.getElementById('sb-streets'),   stats.total_streets,   1300);

        // Coverage metrics — slightly longer for visual distinction
        countUp(document.getElementById('cv-addresses'), stats.total_addresses, 1600);
        countUp(document.getElementById('cv-localities'), stats.total_localities, 1400);
        countUp(document.getElementById('cv-streets'),   stats.total_streets,   1500);

        // State grid
        if (stats.localities_by_state) {
            const grid = document.getElementById('state-grid');
            grid.innerHTML = stats.localities_by_state.map(s => `
                <button class="state-btn" onclick="openStateModal('${s.state_abbreviation}')">
                    ${s.state_abbreviation}
                    <span class="state-btn-count">${s.count.toLocaleString()}</span>
                </button>
            `).join('');
        }

        // Create modal once
        const modal = document.createElement('div');
        modal.id = 'state-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="modal-title">Loading&hellip;</h2>
                    <button class="modal-close" onclick="closeModal()">&times;</button>
                </div>
                <div id="modal-body" class="modal-body"></div>
            </div>
        `;
        document.body.appendChild(modal);

    } catch (err) {
        console.error('Stats load error:', err);
    }
});

/* ── State modal ── */
async function openStateModal(state) {
    const modal = document.getElementById('state-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody  = document.getElementById('modal-body');

    modal.classList.add('active');
    modalTitle.textContent = `${state} — Loading…`;
    modalBody.innerHTML = '<div class="loading">Loading suburbs…</div>';

    try {
        const response = await fetch(`/api/suburbs/by-state?state=${encodeURIComponent(state)}`);
        const data = await response.json();

        modalTitle.textContent = `${state} (${data.count.toLocaleString()} Suburbs)`;

        if (data.suburbs && data.suburbs.length > 0) {
            modalBody.innerHTML = `
                <div class="modal-search">
                    <input type="text" id="suburb-filter" placeholder="Filter suburbs…" class="search-input">
                    <span id="filter-count">${data.count.toLocaleString()} results</span>
                </div>
                <div class="suburbs-table">
                    <table id="suburbs-table">
                        <thead><tr><th>Suburb</th><th>Postcode</th></tr></thead>
                        <tbody>
                            ${data.suburbs.map(s => `
                                <tr class="clickable-row" data-suburb="${s.suburb}" data-postcode="${s.postcode}">
                                    <td>${s.suburb}</td>
                                    <td>${s.postcode}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            const searchInput = document.getElementById('suburb-filter');
            const filterCount = document.getElementById('filter-count');
            const rows = Array.from(document.querySelectorAll('#suburbs-table tbody tr'));

            searchInput.addEventListener('input', e => {
                const term = e.target.value.toLowerCase().trim();
                let count = 0;
                rows.forEach(row => {
                    const match =
                        row.cells[0].textContent.toLowerCase().includes(term) ||
                        row.cells[1].textContent.toLowerCase().includes(term);
                    row.style.display = match ? '' : 'none';
                    if (match) count++;
                });
                filterCount.textContent = `${count.toLocaleString()} result${count !== 1 ? 's' : ''}`;
            });

            rows.forEach(row => {
                row.addEventListener('click', () => {
                    window.location.href = `/address-lookup?suburb=${encodeURIComponent(row.dataset.suburb)}&postcode=${encodeURIComponent(row.dataset.postcode)}&auto=true`;
                });
            });

            setTimeout(() => searchInput.focus(), 100);
        } else {
            modalBody.innerHTML = '<p>No suburbs found for this state.</p>';
        }
    } catch (err) {
        console.error(err);
        modalBody.innerHTML = '<p class="error">Error loading suburbs. Please try again.</p>';
    }
}

function closeModal() {
    document.getElementById('state-modal').classList.remove('active');
}

window.addEventListener('click', e => {
    const modal = document.getElementById('state-modal');
    if (modal && e.target === modal) closeModal();
});

/* ── Flying data chips canvas ── */
(function () {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var canvas = document.getElementById('hero-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');

    var LABELS = [
        'NSW','VIC','QLD','WA','SA','TAS','ACT','NT',
        '14.8M','2077','2000','98%','GNAF','15k','875k',
        '2119','2076','2125','Address','Suburb','School',
        'Postcode','Street','National','Australia'
    ];

    var chips = [];
    var COUNT = 32;
    var FONT  = '700 9px Inter,system-ui,sans-serif';

    function resize() {
        canvas.width  = canvas.parentElement.offsetWidth;
        canvas.height = canvas.parentElement.offsetHeight;
    }

    function makeChip(randomY) {
        ctx.font = FONT;
        var label = LABELS[Math.floor(Math.random() * LABELS.length)];
        var tw    = ctx.measureText(label).width;
        var w = tw + 22;
        var h = 19;
        return {
            label : label,
            w     : w,
            h     : h,
            x     : Math.random() * (canvas.width + w * 2) - w,
            y     : randomY ? Math.random() * canvas.height : canvas.height + h + Math.random() * 60,
            vx    : (Math.random() - 0.5) * 0.28,
            vy    : -(0.18 + Math.random() * 0.38),
            alpha : 0.055 + Math.random() * 0.085,
        };
    }

    function init() {
        resize();
        chips = [];
        for (var i = 0; i < COUNT; i++) chips.push(makeChip(true));
    }

    function drawChip(c) {
        var r = c.h / 2;
        ctx.beginPath();
        ctx.moveTo(c.x + r, c.y);
        ctx.lineTo(c.x + c.w - r, c.y);
        ctx.arc(c.x + c.w - r, c.y + r, r, -Math.PI / 2,  Math.PI / 2);
        ctx.lineTo(c.x + r, c.y + c.h);
        ctx.arc(c.x + r,       c.y + r, r,  Math.PI / 2, -Math.PI / 2);
        ctx.closePath();

        ctx.globalAlpha = c.alpha * 0.35;
        ctx.fillStyle   = '#1e40af';
        ctx.fill();

        ctx.globalAlpha = c.alpha;
        ctx.strokeStyle = '#60a5fa';
        ctx.lineWidth   = 0.8;
        ctx.stroke();

        ctx.fillStyle    = '#93c5fd';
        ctx.font         = FONT;
        ctx.textBaseline = 'middle';
        ctx.fillText(c.label, c.x + 11, c.y + c.h / 2);
    }

    var raf;
    function loop() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        chips.forEach(function (c) {
            ctx.save();
            drawChip(c);
            ctx.restore();

            c.x += c.vx;
            c.y += c.vy;

            // respawn at bottom when chip leaves top
            if (c.y + c.h < 0) { Object.assign(c, makeChip(false)); }
            if (c.x > canvas.width  + c.w) c.x = -c.w - 5;
            if (c.x + c.w < 0)              c.x = canvas.width + 5;
        });

        raf = requestAnimationFrame(loop);
    }

    // pause when tab hidden, resume when visible (battery/perf)
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) { cancelAnimationFrame(raf); }
        else                 { loop(); }
    });

    window.addEventListener('resize', function () {
        resize();
        chips.forEach(function (c) {
            if (c.x > canvas.width) c.x = Math.random() * canvas.width;
        });
    });

    init();
    loop();
})();

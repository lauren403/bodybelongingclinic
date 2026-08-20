/* Body Belonging Clinic — mobile nav toggle (accessible, progressive) */
(function(){
  document.addEventListener('click', function(e){
    var nav = document.getElementById('primary-nav');
    if(!nav) return;
    var btn = e.target.closest && e.target.closest('.nav-toggle');
    if(btn){
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      return;
    }
    // tapping a link inside the open menu closes it
    if(nav.classList.contains('open') && e.target.closest && e.target.closest('#primary-nav a')){
      nav.classList.remove('open');
      var b = document.querySelector('.nav-toggle');
      if(b) b.setAttribute('aria-expanded','false');
    }
  });
  // close on Escape
  document.addEventListener('keydown', function(e){
    if(e.key!=='Escape') return;
    var nav = document.getElementById('primary-nav');
    if(nav && nav.classList.contains('open')){
      nav.classList.remove('open');
      var b = document.querySelector('.nav-toggle');
      if(b){ b.setAttribute('aria-expanded','false'); b.focus(); }
    }
  });
})();

/* Body Belonging Clinic — booking widget analytics (GA4)
   Fires two events wherever a .booking-embed booking widget exists:
   - booking_widget_view: widget scrolled into view (once per page)
   - booking_widget_engage: visitor clicks/taps into the widget iframe
     (cross-origin, so detected via window blur + focused iframe; once per page)
   Mark booking_widget_engage + booking_click as key events in GA4. */
(function(){
  var embed = document.querySelector('.booking-embed');
  if(!embed) return;
  function track(name){ if(typeof window.gtag === 'function'){ window.gtag('event', name, {event_category:'booking', page: location.pathname}); } }
  // view
  if('IntersectionObserver' in window){
    var seen = false;
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ if(e.isIntersecting && !seen){ seen = true; track('booking_widget_view'); io.disconnect(); } });
    }, {threshold: 0.4});
    io.observe(embed);
  }
  // engage (first interaction with the iframe)
  var engaged = false;
  window.addEventListener('blur', function(){
    if(engaged) return;
    var el = document.activeElement;
    if(el && el.tagName === 'IFRAME' && embed.contains(el)){
      engaged = true;
      track('booking_widget_engage');
    }
  });
})();

/* ─────────────────────────────────────────────────────────────
   Meta Pixel (for Instagram/Facebook ads) — CONSENT-GATED.
   Only fires after the visitor accepts cookies. The consent banner
   calls window.bbcActivateMeta() on Accept; on later visits where
   consent is already stored, it auto-activates below.
   Maps existing actions to Meta events: Schedule (bookings), Contact
   (emails), Lead (enquiry form + guide sign-up), CompleteRegistration
   (guide confirmation page).
   ───────────────────────────────────────────────────────────── */
(function(){
  var META_PIXEL_ID = "1340307787512399"; // Body Belonging Clinic Meta Pixel
  window.bbcActivateMeta = function(){
    if(!META_PIXEL_ID || window.fbq) return; // idempotent
    if(!/(^|\.)bodybelongingclinic\.com\.au$/i.test(location.hostname)) return; // production domains only
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
    n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script',
    'https://connect.facebook.net/en_US/fbevents.js');
    try{
      fbq('init', META_PIXEL_ID);
      fbq('track', 'PageView');
      if(location.pathname.indexOf('guide-ready') > -1){ fbq('track','CompleteRegistration',{content_name:'ADHD eating starter guide'}); }
    }catch(e){}
  };
  // Event mapping — listeners always attached; no-op until the pixel is activated.
  document.addEventListener('click', function(e){
    if(!window.fbq || !e.target.closest) return;
    var a = e.target.closest('a[href]'); if(!a) return;
    var h = a.getAttribute('href') || '';
    try{
      if(h.indexOf('zandahealth.com') > -1) fbq('track','Schedule');
      else if(h.indexOf('mailto:') === 0) fbq('track','Contact');
      else if(h.indexOf('preview.mailerlite.io') > -1) fbq('track','Lead',{content_name:'starter guide'});
    }catch(err){}
  }, true);
  document.addEventListener('submit', function(e){
    if(!window.fbq) return;
    var f = e.target;
    if(f && f.getAttribute && f.getAttribute('name') === 'enquiry'){ try{ fbq('track','Lead',{content_name:'enquiry form'}); }catch(err){} }
  }, true);
  // Auto-activate on repeat visits where consent is already stored.
  if(/(?:^|;\s*)bbc_consent=granted/.test(document.cookie)) window.bbcActivateMeta();
})();

/* sticky mobile "Book" button, injected site-wide */
(function(){
  function add(){
    if(document.querySelector('.sticky-book'))return;
    var d=document.createElement('div'); d.className='sticky-book';
    d.innerHTML='<a href="https://clientportal.zandahealth.com/clientportal/bodybelongingclinic/appointment-booking" rel="noopener" target="_blank" aria-label="Book a session">Book a session →</a>';
    document.body.appendChild(d);
  }
  if(document.readyState!=='loading')add(); else document.addEventListener('DOMContentLoaded',add);
})();

/* theme toggle (dark mode) — respects saved choice + system default */
(function(){
  try{
    var nav=document.getElementById('primary-nav')||document.querySelector('.site-header nav')||document.querySelector('header nav');
    if(!nav||nav.querySelector('.theme-toggle'))return;
    var btn=document.createElement('button');
    btn.className='theme-toggle';btn.type='button';btn.setAttribute('aria-label','Toggle dark mode');
    btn.innerHTML='<svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg><svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.4 1.4M17.6 17.6 19 19M19 5l-1.4 1.4M6.4 17.6 5 19"/></svg>';
    function sync(){var d=document.documentElement.getAttribute('data-theme')==='dark';btn.setAttribute('aria-pressed',d?'true':'false');}
    var book=nav.querySelector('a.pill');
    if(book)nav.insertBefore(btn,book);else nav.appendChild(btn);
    sync();
    btn.addEventListener('click',function(){
      var next=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
      document.documentElement.setAttribute('data-theme',next);
      try{localStorage.setItem('bbc-theme',next);}catch(e){}
      sync();
    });
  }catch(e){}
})();

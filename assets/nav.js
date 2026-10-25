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

/* sticky mobile "Book" button, injected site-wide */
(function(){
  function add(){
    if(document.querySelector('.sticky-book'))return;
    var d=document.createElement('div'); d.className='sticky-book';
    d.innerHTML='<a href="https://clientportal.zandahealth.com/clientportal/bodybelongingclinic/appointment-booking" rel="noopener" target="_blank" aria-label="Book a free 15-minute call">Book a free call →</a>';
    document.body.appendChild(d);
    /* step aside while another booking button is already on screen */
    try{
      var t=document.querySelectorAll('.actions-row,.cta-final,.site-footer');
      if(!t.length||!('IntersectionObserver' in window))return;
      var on=new Set();
      var io=new IntersectionObserver(function(es){
        es.forEach(function(e){ if(e.isIntersecting)on.add(e.target); else on.delete(e.target); });
        var h=on.size>0; d.classList.toggle('is-hidden',h);
        var l=d.querySelector('a'); if(h){d.setAttribute('aria-hidden','true');l.setAttribute('tabindex','-1');}else{d.removeAttribute('aria-hidden');l.removeAttribute('tabindex');}
      },{rootMargin:'0px 0px -40px 0px'});
      t.forEach(function(el){io.observe(el);});
    }catch(err){}
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

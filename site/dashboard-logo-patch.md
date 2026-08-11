# Dashboard official-logo patch

Apply this after the concurrent `dashboard.html` work lands. Replace the current text wordmark with:

```html
<a class="wordmark" href="index.html" aria-label="Omo home">
  <img class="wordmark-logo" src="logo-sweet-pastel.svg" alt="">
</a>
```

Use this CSS (and remove the obsolete `.wordmark-dot` rule):

```css
.wordmark {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}
.wordmark-logo {
  display: block;
  width: auto;
  height: 34px;
}
.footer-brand .wordmark-logo { height: 36px; }
```

Favicon/head note: keep `favicon.svg`, `favicon-16.png`, `favicon-32.png`, `apple-touch-icon.png`, and `site.webmanifest` references. The filenames are unchanged and now resolve to the Sweet &amp; Pastel identity. Set `<meta name="theme-color" content="#4F3F59">`.

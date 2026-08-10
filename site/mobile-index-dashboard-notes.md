# Index/dashboard mobile integration notes

The CSS source is [`mobile-index-dashboard.css`](mobile-index-dashboard.css). Follow its header exactly: paste the whole block immediately before the existing `</style>` in both `index.html` and `dashboard.html`, after the demo redesign has landed.

## HTML changes

1. In both pages, enable the safe-area values used by the override:

   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
   ```

2. In `dashboard.html`, add `<meta name="theme-color" content="#1E3A34">`, then place the MCP link between API and Sign out so the four controls stay in a predictable order. The `mcp.html` page now exists, so use it as the real destination. Reuse the API pill treatment so the override remains compatible:

   ```html
   <a class="api-link mcp-link auth-only" href="mcp.html" title="Connect Omo helpers through MCP">MCP</a>
   ```

3. Change the dashboard Balance pill from a passive `<span>` to a real button while keeping `id="balance-pill"` and the `balance-pill auth-only` classes:

   ```html
   <button class="balance-pill auth-only" id="balance-pill" type="button">Balance …</button>
   ```

   This gives mobile users a direct route to credits instead of making them pass every catalogue card.

4. Change the dashboard mobile sidebar kicker to “Browse by niche”. The override hides its duplicated Content/Leads/Save/Ops buttons because those remain in the outcome rail below the search box.

5. Keep the dialog close button as the first child of `<dialog>` and `.dialog-body` as its scrolling sibling. The bottom-sheet CSS relies on that structure for a sticky 44px close target.

6. Both pages currently make each `.listing-card` a keyboard `role="button"` while nesting real upvote/run/details buttons inside it. Replace that nested interactive pattern with a noninteractive `<article>` plus a dedicated full-card details link/button; keep the three actions as siblings.

7. In `index.html`, the rotating tool name should not announce a new live-region message every few seconds. Make the animated word visual-only (`aria-hidden="true"`) and add one static screen-reader phrase. Replace the footer's Terms/Privacy/Support `#top` placeholders with real destinations or non-link text.

## JavaScript changes

`scrollIntoView({ block: 'center' })` is unreliable inside the mobile `<dialog>` scroller and currently leaves the run panel below the viewport. In both pages, use the dialog body as the explicit scroll owner after `showModal()`:

```js
function revealRunPanel(panel, firstControl) {
  requestAnimationFrame(function () {
    dialogBody.scrollTo({
      top: Math.max(0, panel.offsetTop - 64),
      behavior: 'auto'
    });
    if (firstControl) firstControl.focus({ preventScroll: true });
  });
}
```

- `index.html`: call it with `.run-handoff` and its first `a, button` from `openDialog(..., true)`.
- `dashboard.html`: call it with `.demo-box` and its first `[data-demo-field]` from `openDialog(..., true)`. Reuse the same helper when a `[data-action="demo"]` button inside the open dialog is pressed.
- After a filter/niche selection, call `activeChip.scrollIntoView({ block: 'nearest', inline: 'center' })` so the selected chip never remains half offscreen.
- On dashboard startup, bind the Balance button so it opens and reveals the credit workspace:

  ```js
  el('balance-pill').addEventListener('click', function () {
    var credits = el('credits-panel');
    if (!credits) return;
    credits.open = true;
    credits.scrollIntoView({ block: 'start', behavior: 'smooth' });
  });
  ```

The existing close handler already restores focus to the launching control; preserve that behavior.

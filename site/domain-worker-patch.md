# Deferred worker and dashboard domain patch

Apply this patch after the concurrent changes to `site/deploy/worker.js` and `site/dashboard.html` land. Those files were audited read-only during the domain migration.

```diff
--- a/site/deploy/worker.js
+++ b/site/deploy/worker.js
@@
-  params.set('success_url', `https://omo.best/?purchased=${encodeURIComponent(slug)}`);
-  params.set('cancel_url', 'https://omo.best/?purchased=cancelled');
+  params.set('success_url', `https://omo.space/?purchased=${encodeURIComponent(slug)}`);
+  params.set('cancel_url', 'https://omo.space/?purchased=cancelled');
@@
-  params.set('success_url', 'https://omo.best/dashboard.html?topup=success');
-  params.set('cancel_url', 'https://omo.best/dashboard.html?topup=cancelled');
+  params.set('success_url', 'https://omo.space/dashboard.html?topup=success');
+  params.set('cancel_url', 'https://omo.space/dashboard.html?topup=cancelled');
@@
 function isAllowedStorefrontOrigin(origin) {
-  return origin === 'https://omo.best' || /^http:\/\/localhost(?::\d{1,5})?$/.test(origin);
+  return origin === 'https://omo.space' ||
+    origin === 'https://omo.best' ||
+    /^http:\/\/localhost(?::\d{1,5})?$/.test(origin);
 }
--- a/site/dashboard.html
+++ b/site/dashboard.html
@@
-  <meta property="og:url" content="https://omo.best/dashboard.html">
+  <meta property="og:url" content="https://omo.space/dashboard.html">
@@
-      function workerBase() { return API_BASE || 'https://cognition-demo.pages.dev'; }
+      function workerBase() { return API_BASE || 'https://omo.space'; }
@@
-              return fetch((API_BASE || 'https://cognition-demo.pages.dev') + '/api/run', { method: 'POST', headers: headers, body: JSON.stringify(payload) });
+              return fetch((API_BASE || 'https://omo.space') + '/api/run', { method: 'POST', headers: headers, body: JSON.stringify(payload) });
```

The legacy `https://omo.best` CORS origin stays temporarily because that hostname remains live on the same deployment. Remove it when `omo.best` becomes a strict redirect and no browser clients originate there.


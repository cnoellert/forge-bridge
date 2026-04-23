# Vendored frontend assets

These files are served at `/ui/static/vendor/*` by Starlette's `StaticFiles`.
Version is in the filename (htmx-2.0.10.min.js, not htmx.min.js) so bumps are
detectable by `git log` alone.

## Update procedure

1. Drop the new file with the bumped version in the filename:
   `htmx-<version>.min.js` or `alpinejs-<version>.min.js`.
2. Recompute the SRI hash:
   `openssl dgst -sha384 -binary < <file> | openssl base64 -A`
3. Bump the `<script>` `src` + `integrity` attributes in
   `forge_bridge/console/templates/base.html`.

No build step. No lockfile. The previous version file may be deleted in the
same commit once the template reference is flipped.

## Current versions

- htmx-2.0.10.min.js (upstream: https://unpkg.com/htmx.org@2.0.10/dist/htmx.min.js)
- alpinejs-3.14.1.min.js (upstream: https://unpkg.com/alpinejs@3.14.1/dist/cdn.min.js)

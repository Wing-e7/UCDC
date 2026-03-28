# Staffer ↔ UCDC — integration bundle

Copy this directory into **`The_Staffer_UCDC`** (suggested path: `integrations/ucdc/` at repo root) and wire your app to `UCDCClient`.

## Quick merge (from a local Staffer clone)

```bash
# In your Staffer repo root
mkdir -p integrations/ucdc
cp -R /path/to/UCDC/docs/staffer-ucdc-bundle/integrations/ucdc_client.py integrations/ucdc/
cp /path/to/UCDC/docs/staffer-ucdc-bundle/COMPATIBILITY.md integrations/ucdc/
```

Then:

1. Add env vars (see `COMPATIBILITY.md`).
2. Replace any ad-hoc `requests`/`httpx` calls to UCDC with `UCDCClient`.
3. Ensure your **adapter** deployment reports the same **`agent_id`** you use in consent + jobs (configure `CapabilitiesResponse` / Staffer adapter code accordingly).

## UCDC repository

Platform contracts and services: **https://github.com/Wing-e7/UCDC**

Staffer agent repo (this integration targets): **https://github.com/Wing-e7/The_Staffer_UCDC**

## Support

If UCDC APIs change, update this bundle in the **UCDC** repo first, then copy into Staffer.

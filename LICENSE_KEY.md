LICENSE KEYS & Technical Options (Guidance)

This file explains approaches to a *technical* license key system. Note: a technical key system does not replace a legal license; use both.

Goals you stated:
- Users can edit and modify the code
- Users may not sell the software
- Users may not claim authorship of the original

Options:
1) No technical restriction (recommended legal-first approach)
   - Use a legal license (e.g., CC BY-NC-SA 4.0) in `LICENSE` to prohibit commercial use and require attribution.
   - Advantages: legally clear for non-commercial use; easy for users.
   - Disadvantages: enforcement requires legal action; some platforms do not accept CC for software.

2) Source-available + simple key check (lightweight)
   - Keep code open in repo, but optionally provide "premium" features or installer requiring a license key.
   - Add a small check in the application that requires a key for certain restricted features (e.g., auto-update, packaged installer).
   - Implementation note: keys can be just strings validated locally (weak) or signed tokens validated against your server (stronger).
   - Pros: discourages casual commercial redistribution; Cons: can be bypassed by determined users if code is open.

3) Binary distribution + key enforcement (stronger)
   - Distribute compiled binaries (not full source) to paid users; include key validation against license server.
   - Keep repo source-available but flagged as non-commercial; commercial/paid users get a different license and binaries.
   - Pros: stronger control; Cons: more overhead and less open.

4) Dual licensing (recommended for monetization control)
   - Offer the project under a non-commercial license (e.g., CC BY-NC-SA) for community use and a commercial license for paying customers.
   - This allows you to forbid resale while offering a paid commercial license to customers who want to sell/use commercially.

Practical key types & format
- Simple token: random UUID-like string stored in a config file. (Easy but weak.)
- Signed JWT: key contains info and is signed by your private key; app verifies signature. (Strong if using server validation.)
- Server-issued activation: app contacts your server and receives activation. (Strongest; requires server.)

Quick example (local, weak) - Python pseudocode:

```python
# load license from disk
license_key = load_config().get('license_key')
if license_key not in allowed_keys:
    print('Unlicensed or non-commercial license required for this feature')
else:
    enable_feature()
```

Caveats & legal note
- Technical enforcement is never a substitute for a legal license. If someone re-distributes your code illegally, you need legal steps to enforce the license.
- Creative Commons licenses are not recommended for software by the CC team, but many projects use CC BY-NC-SA for non-commercial intentions. Consult legal counsel for production use.

If you want, I can:
- Replace `LICENSE` with a different text (AGPLv3, custom language, or dual-license header)
- Add a basic `license_check.py` that demonstrates a local-license-key check
- Add wording to `README.md` that describes the license and how to obtain a commercial license

Tell me which of the above you want me to implement next.

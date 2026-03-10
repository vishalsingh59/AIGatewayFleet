# Security Notes

## What is protected

The update flow is designed to prevent robots from installing tampered or untrusted software.

## Signing

The current implementation signs release files with RSA keys using `openssl`.

Signed files:

- artifact
- SBOM
- attestation
- manifest

## Verification

Both gateway and client verify files with local public keys.

This happens offline, so robots do not need internet access to validate updates.

## Integrity checks

The manifest includes checksums.

Gateway and client verify checksums before accepting files.

## Threats considered

- malicious artifact injection
- file tampering in transit or at rest
- compromised gateway serving bad files
- replay/downgrade attempts

## Key rotation plan

1. publish new public key in signed metadata
2. distribute keys through gateway sync
3. update trusted keys on robots
4. deprecate old key after migration

## Future options

If needed later, you can switch signing backend to tools like Cosign, GPG, or in-toto.

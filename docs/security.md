# Security Notes

## Signing approach

Release metadata and payloads are signed in CI with an RSA keypair generated locally by `ci/scripts/sign_artifact.sh`.

Signed files:

- artifact
- SBOM
- attestation
- manifest

The private key is generated on demand and is intentionally ignored by git. Only the public key is copied to the gateway and robot trust stores during release publication.

## Offline verification

All trust decisions work without internet access:

- the gateway verifies manifest, artifact, SBOM, attestation, and all signatures before caching a release
- the robot verifies the manifest signature, SBOM signature, attestation signature, attestation contents, artifact checksum, and artifact signature before install
- downgrade attempts are blocked by storing the highest accepted version on each robot

## Threat model

Threats addressed by the prototype:

- tampered artifact, SBOM, attestation, or manifest in transit or at rest
- compromised or buggy gateway trying to serve modified release content
- replay or downgrade attempts from stale cached manifests
- intermittent network failures between robot, gateway, and dashboard

Threats not fully addressed in this prototype:

- compromise of the CI signing environment
- theft of a robot or gateway trust store from the host filesystem
- insider misuse of local shell access on the demo machine
- transport-layer interception between components; mTLS is left as a documented future enhancement

## Key rotation plan

1. Generate a new signing keypair in CI.
2. Publish the new public key alongside the current one in a signed release.
3. Sync both trusted public keys to gateways.
4. Let robots accept signatures from either key during the transition window.
5. Start signing new releases with the new private key.
6. Publish one final dual-trust release that removes the old key from the trusted set.

This prototype does not automate multi-key trust sets yet, but the rollout sequence above is the intended production path.

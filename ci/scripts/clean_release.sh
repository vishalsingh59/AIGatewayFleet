#!/usr/bin/env bash
set -e

rm -f ci/manifests/*.json
rm -f ci/artifacts/*.bin
rm -f ci/sbom/*.json
rm -f ci/attestations/*.json
rm -f ci/signatures/*.sig

echo "CI release outputs cleaned"

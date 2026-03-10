#!/usr/bin/env bash
set -e

echo "Resetting demo state..."

# Clean gateway data
rm -rf gateway/data
rm -rf gateway/data-gw1
rm -rf gateway/data-gw2

mkdir -p gateway/data-gw1/cache gateway/data-gw1/metrics
mkdir -p gateway/data-gw2/cache gateway/data-gw2/metrics

echo "Gateway state reset"

# Clean dashboard data
rm -rf dashboard/data
mkdir -p dashboard/data
echo "Dashboard state reset"

# Reset robot states (each robot keeps independent runtime state)
reset_robot_state() {
  local robot_state_dir="$1"

  rm -rf "${robot_state_dir}"
  mkdir -p "${robot_state_dir}/downloads"
  mkdir -p "${robot_state_dir}/installed"
  mkdir -p "${robot_state_dir}/backup"

  cat > "${robot_state_dir}/version_state.json" <<EOF
{
  "current_version": "1.0.0",
  "previous_version": "1.0.0",
  "highest_version": "1.0.0"
}
EOF

  echo "robot software version 1.0.0" > "${robot_state_dir}/installed/robot-app-1.0.0.bin"
  echo "status=healthy" >> "${robot_state_dir}/installed/robot-app-1.0.0.bin"
}

reset_robot_state "client/state/robot-1"
reset_robot_state "client/state/robot-2"
reset_robot_state "client/state/robot-3"
reset_robot_state "client/state/robot-4"
reset_robot_state "client/state/robot-5"
reset_robot_state "client/state/robot-6"

echo "Client robot states reset"

# Clean CI outputs (optional but safer)
rm -rf ci/artifacts/*
rm -rf ci/manifests/*
rm -rf ci/sbom/*
rm -rf ci/attestations/*
rm -rf ci/signatures/*

echo "CI outputs cleared"

echo "Demo environment reset complete"

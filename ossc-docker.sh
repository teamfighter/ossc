#!/usr/bin/env bash
# OSSC Docker wrapper
# Usage: source ./ossc-docker.sh; ossc <args>

ossc() {
  # Avoid setting -e/-u globally in user's shell; handle errors manually
  local cfg_base
  if [ -n "${XDG_CONFIG_HOME:-}" ]; then
    cfg_base="$XDG_CONFIG_HOME"
  else
    cfg_base="$HOME/.config"
  fi
  local cfg_dir="$cfg_base/ossc"
  mkdir -p "$cfg_dir"
  [ -e "$cfg_dir/profiles.json" ] || : > "$cfg_dir/profiles.json"

  # Image tag (override with OSSC_IMAGE)
  local image_name="${OSSC_IMAGE:-ossc:latest}"

  docker run --rm -it \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e XDG_CONFIG_HOME=/tmp/.config \
    -v "$cfg_dir:/tmp/.config/ossc" \
    -v "$(pwd):/workspace" \
    -w /workspace \
    "$image_name" "$@"
  return $?
}

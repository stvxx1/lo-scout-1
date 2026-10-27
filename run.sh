#!/usr/bin/env bash
# Local launcher: creates a venv on first run, installs deps, starts the app.
set -euo pipefail

cd "$(dirname "$0")"

# Termux (Android) is a bionic environment: Streamlit needs pyarrow and pandas,
# pip cannot use the manylinux wheels without glibc, and neither library has a
# Termux package. Say so up front instead of failing twenty minutes into a
# source build of Arrow. See "Running on Android (Termux)" in the README.
is_termux() {
    if [ -n "${TERMUX_VERSION:-}" ]; then
        return 0
    fi
    case "${PREFIX:-}" in
        *com.termux*) return 0 ;;
    esac
    return 1
}

if is_termux && [ "${LO_SCOUT_ALLOW_TERMUX:-0}" != "1" ]; then
    cat >&2 <<'EOF'
This is Termux (Android), where Streamlit cannot be installed: pyarrow and
pandas have no Termux package, and pip cannot use the manylinux wheels without
glibc. Run inside proot-distro instead:

    pkg install proot-distro
    proot-distro install ubuntu
    proot-distro login ubuntu
    apt install -y python3 python3-venv git libjpeg62 zlib1g

then clone the repo inside that Ubuntu and run ./run.sh there.

Set LO_SCOUT_ALLOW_TERMUX=1 to try anyway.
EOF
    exit 1
fi

if [ ! -d .venv ]; then
    echo "Creating .venv ..."
    python3 -m venv .venv
    ./.venv/bin/pip install --quiet --upgrade pip
    ./.venv/bin/pip install --quiet -r requirements.txt
fi

exec ./.venv/bin/streamlit run lo-scout/app.py "$@"

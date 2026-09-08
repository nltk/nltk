#!/usr/bin/env bash
# Best-effort, cross-platform SENNA acquisition for the tool-integration CI.
#
# third-party.sh only fetches SENNA on Linux (it ships a prebuilt binary per
# platform: senna-linux64 / senna-win32.exe / senna-osx). This extends that to
# macOS and Windows so the SENNA wrapper is exercised on real I/O there too:
#
#   Linux    -> shipped senna-linux64 (already fetched by third-party.sh)
#   Windows  -> shipped senna-win32.exe (32-bit, runs on x64 via WOW64)
#   macOS    -> shipped senna-osx is 32-bit and will not run on modern macOS, so
#               recompile the bundled C source to a 64-bit senna-osx (best effort)
#
# SENNA is exported (to $GITHUB_ENV) only when the binary THIS platform's wrapper
# will pick actually exists, so a failed/absent build makes the SENNA tests skip
# cleanly instead of erroring on an unrunnable binary. This whole step is invoked
# with continue-on-error, so a download/build failure never reds the job.
set -u

: "${THIRD_PARTY_DIR:?THIRD_PARTY_DIR must be set by the workflow}"
SENNA_DIR="${THIRD_PARTY_DIR}/senna"
os="$(uname -s)"

emit_senna() {
    # Only trust the dir if the platform-specific binary is present.
    if [[ -n "${GITHUB_ENV:-}" ]]; then
        echo "SENNA=${SENNA_DIR}" >>"${GITHUB_ENV}"
    fi
    echo "SENNA set to ${SENNA_DIR}"
}

# 1) Ensure the senna tree exists (third-party.sh already did this on Linux).
if [[ ! -d "${SENNA_DIR}" ]]; then
    mkdir -p "${THIRD_PARTY_DIR}"
    pushd "${THIRD_PARTY_DIR}" >/dev/null || exit 0
    senna_file_name="$(curl -s 'https://ronan.collobert.com/senna/download.html' \
        | grep -o 'senna-v.*\.tgz' | head -n1)"
    if [[ -z "${senna_file_name}" ]]; then
        echo "Could not resolve the SENNA download name; skipping SENNA."
        popd >/dev/null || true
        exit 0
    fi
    if ! curl -fL "https://ronan.collobert.com/senna/${senna_file_name}" \
        -o "${senna_file_name}"; then
        echo "SENNA download failed; skipping SENNA."
        popd >/dev/null || true
        exit 0
    fi
    tar -xzf "${senna_file_name}" && rm -f "${senna_file_name}"
    popd >/dev/null || true
fi
[[ -d "${SENNA_DIR}" ]] || { echo "No SENNA dir after fetch; skipping."; exit 0; }

# 2) Per-platform binary selection (mirrors nltk.classify.senna.Senna.executable).
case "${os}" in
Linux)
    [[ -x "${SENNA_DIR}/senna-linux64" ]] && emit_senna
    ;;
MINGW* | MSYS* | CYGWIN*)
    # Windows runner under git-bash: the shipped 32-bit exe runs on x64 via WOW64.
    [[ -f "${SENNA_DIR}/senna-win32.exe" ]] && emit_senna
    ;;
Darwin)
    # The shipped senna-osx is 32-bit (exec fails on modern macOS). Recompile the
    # bundled C source to a 64-bit senna-osx; only trust it if a 64-bit binary
    # results. This is the "(b) best-effort build" arm; if it fails, SENNA stays
    # unset and the SENNA tests skip.
    if [[ -f "${SENNA_DIR}/senna-osx" ]] && file "${SENNA_DIR}/senna-osx" \
        | grep -q '64-bit'; then
        emit_senna
    elif [[ -d "${SENNA_DIR}/src" ]]; then
        echo "Recompiling SENNA for macOS x86_64 (best effort)..."
        if ( cd "${SENNA_DIR}/src" && make ) 2>/dev/null \
            && [[ -x "${SENNA_DIR}/senna-osx" ]] \
            && file "${SENNA_DIR}/senna-osx" | grep -q '64-bit'; then
            emit_senna
        elif cc -O3 -o "${SENNA_DIR}/senna-osx" "${SENNA_DIR}"/src/*.c -lm 2>/dev/null \
            && file "${SENNA_DIR}/senna-osx" | grep -q '64-bit'; then
            emit_senna
        else
            echo "macOS SENNA recompile did not produce a 64-bit binary; skipping SENNA."
        fi
    else
        echo "No bundled SENNA source to recompile on macOS; skipping SENNA."
    fi
    ;;
*)
    echo "Unknown OS ${os}; skipping SENNA."
    ;;
esac
exit 0

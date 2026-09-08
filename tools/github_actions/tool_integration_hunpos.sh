#!/usr/bin/env bash
# Best-effort, POSIX-only hunpos build for the tool-integration CI.
#
# hunpos ships no cross-platform binary; it is built from the mivoq/hunpos OCaml
# source with cmake. This compiles it on Linux/macOS to prove it still builds and,
# when it does, exports HUNPOS_TAGGER / HUNPOS_TRAINER so the hunpos wrapper can be
# exercised on real I/O. Windows is skipped by the workflow (no practical OCaml
# toolchain there); this script is invoked with continue-on-error, so a missing
# toolchain or a build failure never reds the job. It builds the tool but does not
# train a model (that is a separate, heavier step left for a follow-up).
set -u

: "${THIRD_PARTY_DIR:?THIRD_PARTY_DIR must be set by the workflow}"
BUILD_ROOT="${THIRD_PARTY_DIR}/hunpos-src"
BIN_DIR="${THIRD_PARTY_DIR}/hunpos/bin"
os="$(uname -s)"

# 1) Toolchain (best effort; ignore failures, the build step will just skip).
if [[ "${os}" == "Linux" ]]; then
    sudo apt-get update -qq || true
    sudo apt-get install -y -qq ocaml-nox cmake make || true
elif [[ "${os}" == "Darwin" ]]; then
    brew install ocaml cmake >/dev/null 2>&1 || true
fi
command -v ocaml >/dev/null 2>&1 || { echo "no ocaml toolchain; skipping hunpos."; exit 0; }
command -v cmake >/dev/null 2>&1 || { echo "no cmake; skipping hunpos."; exit 0; }

# 2) Source.
if [[ ! -d "${BUILD_ROOT}" ]]; then
    git clone --depth 1 https://github.com/mivoq/hunpos "${BUILD_ROOT}" 2>/dev/null \
        || { echo "hunpos clone failed; skipping."; exit 0; }
fi

# 3) Build (best effort; both the cmake and the ocamlbuild layouts exist in the
#    wild, so try cmake first then fall back to the bundled build.sh).
mkdir -p "${BIN_DIR}"
built=""
if ( cd "${BUILD_ROOT}" && cmake -S . -B _cmb >/dev/null 2>&1 \
        && cmake --build _cmb >/dev/null 2>&1 ); then
    built=1
elif ( cd "${BUILD_ROOT}" && [[ -f build.sh ]] && bash build.sh >/dev/null 2>&1 ); then
    built=1
fi
[[ -n "${built}" ]] || { echo "hunpos build did not complete; skipping."; exit 0; }

# 4) Collect the produced binaries under a stable name the wrapper expects.
found=""
for cand in tagger.native hunpos-tag; do
    src="$(find "${BUILD_ROOT}" -name "${cand}" -type f -perm -u+x 2>/dev/null | head -n1)"
    [[ -n "${src}" ]] && { cp "${src}" "${BIN_DIR}/hunpos-tag"; found=1; break; }
done
for cand in trainer.native hunpos-train; do
    src="$(find "${BUILD_ROOT}" -name "${cand}" -type f -perm -u+x 2>/dev/null | head -n1)"
    [[ -n "${src}" ]] && { cp "${src}" "${BIN_DIR}/hunpos-train"; break; }
done
if [[ -n "${found}" && -n "${GITHUB_ENV:-}" ]]; then
    chmod +x "${BIN_DIR}/hunpos-tag" 2>/dev/null || true
    echo "HUNPOS_TAGGER=${BIN_DIR}/hunpos-tag" >>"${GITHUB_ENV}"
    [[ -f "${BIN_DIR}/hunpos-train" ]] && echo "HUNPOS_TRAINER=${BIN_DIR}/hunpos-train" >>"${GITHUB_ENV}"
    echo "hunpos built at ${BIN_DIR}/hunpos-tag"
else
    echo "hunpos binary not found after build; skipping."
fi
exit 0

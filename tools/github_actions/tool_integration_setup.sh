#!/usr/bin/env bash
# Best-effort, cross-platform acquisition for EVERY external tool NLTK wraps.
#
# third-party.sh (reused by the workflow first) covers the JVM tools on all OSes
# and the compiled tools (SENNA/PROVER9+MACE4/MEGAM) on Linux only. This fills
# every remaining gap so the tool wrappers are exercised on real I/O on macOS and
# Windows too:
#
#   senna     Linux: shipped senna-linux64 | Windows: shipped senna-win32.exe
#             macOS: recompile the bundled C source to 64-bit (shipped is 32-bit)
#   hunpos    Linux/macOS: build from the mivoq OCaml source (Windows: skipped)
#   stanford-segmenter   jar + models, all OSes (third-party.sh does not fetch it)
#   prover9 + mace4      Linux: shipped p9m4 | macOS/Windows: build LADR from source
#   megam     Linux: shipped megam_i686 | macOS: build from OCaml source (best effort)
#   boxer/candc          build the C&C tools from source, all OSes (best effort)
#   repp      build the REPP tokenizer from source (best effort)
#   dot       graphviz, installed by the workflow's package step (translate.api)
#   tadm      intentionally skipped (needs PETSc; see third-party.sh)
#
# Each tool is independent and best effort: a failed download/build never aborts
# the others (the whole script exits 0), and the matching env var is exported to
# $GITHUB_ENV only when a usable binary/jar exists, so that tool's tests skip
# cleanly instead of erroring. The workflow invokes this with continue-on-error.
set -u

: "${THIRD_PARTY_DIR:?THIRD_PARTY_DIR must be set by the workflow}"
OS="$(uname -s)"
mkdir -p "${THIRD_PARTY_DIR}"

emit() { # emit VAR VALUE  -> export to later steps and log it
    [[ -n "${GITHUB_ENV:-}" ]] && echo "$1=$2" >>"${GITHUB_ENV}"
    echo "  exported $1=$2"
}
is_windows() { [[ "${OS}" == MINGW* || "${OS}" == MSYS* || "${OS}" == CYGWIN* ]]; }

# =========================================================================== #
setup_senna() {
    echo "== senna =="
    local dir="${THIRD_PARTY_DIR}/senna"
    if [[ ! -d "${dir}" ]]; then
        ( cd "${THIRD_PARTY_DIR}" \
            && name="$(curl -s 'https://ronan.collobert.com/senna/download.html' \
                | grep -o 'senna-v.*\.tgz' | head -n1)" \
            && [[ -n "${name}" ]] \
            && curl -fL "https://ronan.collobert.com/senna/${name}" -o "${name}" \
            && tar -xzf "${name}" && rm -f "${name}" ) || {
            echo "  senna fetch failed; skipping."; return 0; }
    fi
    [[ -d "${dir}" ]] || return 0
    if [[ "${OS}" == "Linux" && -x "${dir}/senna-linux64" ]]; then
        emit SENNA "${dir}"
    elif is_windows && [[ -f "${dir}/senna-win32.exe" ]]; then
        emit SENNA "${dir}"  # 32-bit exe runs on x64 Windows via WOW64
    elif [[ "${OS}" == "Darwin" ]]; then
        if [[ -f "${dir}/senna-osx" ]] && file "${dir}/senna-osx" | grep -q '64-bit'; then
            emit SENNA "${dir}"
        elif [[ -d "${dir}/src" ]] \
            && { ( cd "${dir}/src" && make ) >/dev/null 2>&1 \
                 || cc -O3 -o "${dir}/senna-osx" "${dir}"/src/*.c -lm >/dev/null 2>&1; } \
            && file "${dir}/senna-osx" 2>/dev/null | grep -q '64-bit'; then
            emit SENNA "${dir}"
        else
            echo "  macOS senna recompile unavailable; skipping."
        fi
    fi
}

# =========================================================================== #
setup_hunpos() {
    echo "== hunpos =="
    is_windows && { echo "  Windows: no practical OCaml toolchain; skipping."; return 0; }
    local bindir="${THIRD_PARTY_DIR}/hunpos/bin" src="${THIRD_PARTY_DIR}/hunpos-src"
    command -v ocaml >/dev/null 2>&1 || { echo "  no ocaml; skipping."; return 0; }
    command -v cmake >/dev/null 2>&1 || { echo "  no cmake; skipping."; return 0; }
    mkdir -p "${bindir}"
    [[ -d "${src}" ]] || git clone --depth 1 https://github.com/mivoq/hunpos "${src}" \
        >/dev/null 2>&1 || { echo "  clone failed; skipping."; return 0; }
    ( cd "${src}" && cmake -S . -B _cmb >/dev/null 2>&1 && cmake --build _cmb >/dev/null 2>&1 ) \
        || ( cd "${src}" && [[ -f build.sh ]] && bash build.sh >/dev/null 2>&1 ) \
        || { echo "  build failed; skipping."; return 0; }
    local tag
    tag="$(find "${src}" -type f \( -name tagger.native -o -name hunpos-tag \) 2>/dev/null | head -n1)"
    [[ -n "${tag}" ]] || { echo "  no hunpos-tag produced; skipping."; return 0; }
    cp "${tag}" "${bindir}/hunpos-tag"; chmod +x "${bindir}/hunpos-tag" 2>/dev/null || true
    emit HUNPOS_TAGGER "${bindir}/hunpos-tag"
}

# =========================================================================== #
setup_segmenter() {
    echo "== stanford-segmenter =="
    local dir="${THIRD_PARTY_DIR}/stanford-segmenter"
    local sha="abf5e34e36244719b5393036d479780c58b0195324498a93838a55c74b8bbb7f"
    if [[ ! -f "${dir}/stanford-segmenter-4.2.0.jar" ]]; then
        ( cd "${THIRD_PARTY_DIR}" \
            && curl -fL "https://nlp.stanford.edu/software/stanford-segmenter-4.2.0.zip" \
                 -o seg.zip \
            && unzip -q seg.zip && rm -f seg.zip \
            && mv stanford-segmenter-2020-11-17 stanford-segmenter ) \
            || { echo "  segmenter fetch failed; skipping."; return 0; }
    fi
    if [[ -f "${dir}/stanford-segmenter-4.2.0.jar" ]]; then
        # Do NOT set STANFORD_MODELS here: the POS tagger uses it for its own
        # models. The segmenter takes its model paths from default_config('zh').
        emit STANFORD_SEGMENTER "${dir}"
        emit NLTK_SEGMENTER_ALLOW_SHA256 "${sha}"
    fi
}

# =========================================================================== #
setup_prover9_mace4() {
    echo "== prover9 + mace4 (LADR) =="
    local p9="${THIRD_PARTY_DIR}/prover9/bin"
    if [[ -x "${p9}/prover9" && -x "${p9}/mace4" ]]; then emit PROVER9 "${p9}"; return 0; fi
    is_windows && { echo "  Windows LADR build not attempted; skipping."; return 0; }
    # macOS (Linux prebuilt is handled by third-party.sh): build LADR from source.
    local src="${THIRD_PARTY_DIR}/LADR"
    if [[ ! -d "${src}" ]]; then
        ( cd "${THIRD_PARTY_DIR}" \
            && curl -fL "https://www.cs.unm.edu/~mccune/prover9/download/LADR-2009-11A.tar.gz" \
                 -o ladr.tgz \
            && tar -xzf ladr.tgz && rm -f ladr.tgz && mv LADR-2009-11A LADR ) \
            || { echo "  LADR fetch failed; skipping."; return 0; }
    fi
    ( cd "${src}" && make all ) >/dev/null 2>&1 || { echo "  LADR build failed; skipping."; return 0; }
    if [[ -x "${src}/bin/prover9" ]]; then
        emit PROVER9 "${src}/bin"
    else
        echo "  LADR bin/prover9 missing after build; skipping."
    fi
}

# =========================================================================== #
setup_megam() {
    echo "== megam =="
    local dir="${THIRD_PARTY_DIR}/megam"
    if [[ -d "${dir}" ]] && find "${dir}" -type f -perm -u+x | grep -q .; then
        emit MEGAM "${dir}"; return 0
    fi
    is_windows && { echo "  Windows megam build not attempted; skipping."; return 0; }
    [[ "${OS}" == "Darwin" ]] || { echo "  non-macOS handled by third-party.sh; skipping."; return 0; }
    command -v ocaml >/dev/null 2>&1 || { echo "  no ocaml for macOS megam; skipping."; return 0; }
    ( cd "${THIRD_PARTY_DIR}" \
        && curl -fL "http://hal3.name/megam/megam_src.tgz" -o megam_src.tgz \
        && tar -xzf megam_src.tgz && rm -f megam_src.tgz \
        && cd megam_* && make >/dev/null 2>&1 ) || { echo "  megam build failed; skipping."; return 0; }
    local bin
    bin="$(find "${THIRD_PARTY_DIR}" -type d -name 'megam_*' | head -n1)"
    [[ -n "${bin}" ]] && emit MEGAM "${bin}"
}

# =========================================================================== #
setup_boxer_candc() {
    echo "== boxer / C&C tools =="
    local dir="${THIRD_PARTY_DIR}/candc"
    if [[ -x "${dir}/bin/boxer" ]]; then emit CANDC "${dir}"; return 0; fi
    is_windows && { echo "  Windows C&C build not attempted; skipping."; return 0; }
    local src="${THIRD_PARTY_DIR}/candc-src"
    [[ -d "${src}" ]] || git clone --depth 1 https://github.com/chzyer/candc "${src}" \
        >/dev/null 2>&1 || { echo "  C&C source unavailable; skipping (boxer needs the C&C toolkit)."; return 0; }
    ( cd "${src}" && make bin/boxer bin/candc ) >/dev/null 2>&1 || { echo "  C&C build failed; skipping."; return 0; }
    if [[ -x "${src}/bin/boxer" ]]; then mkdir -p "${dir}"; cp -R "${src}/bin" "${dir}/bin"; emit CANDC "${dir}"; fi
}

# =========================================================================== #
setup_repp() {
    echo "== repp =="
    local dir="${THIRD_PARTY_DIR}/repp"
    if [[ -x "${dir}/src/repp" || -x "${dir}/repp" ]]; then emit REPP_TOKENIZER "${dir}"; return 0; fi
    is_windows && { echo "  Windows REPP build not attempted; skipping."; return 0; }
    local src="${THIRD_PARTY_DIR}/repp-src"
    [[ -d "${src}" ]] || git clone --depth 1 https://github.com/delph-in/repp "${src}" \
        >/dev/null 2>&1 || { echo "  REPP source unavailable; skipping."; return 0; }
    ( cd "${src}" && [[ -d src ]] && cd src && make ) >/dev/null 2>&1 || { echo "  REPP build failed; skipping."; return 0; }
    if [[ -x "${src}/src/repp" ]]; then emit REPP_TOKENIZER "${src}"; fi
}

# =========================================================================== #
# tadm: needs libtaopetsc.so from PETSc (see third-party.sh); intentionally not
# built here. Its tests skip when TADM is unset.

setup_senna
setup_hunpos
setup_segmenter
setup_prover9_mace4
setup_megam
setup_boxer_candc
setup_repp
echo "== tool acquisition finished (best effort) =="
exit 0

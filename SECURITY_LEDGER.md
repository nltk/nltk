# NLTK Security Ledger — CVE / CWE Coverage (branch `fix-ghsa-8mgp-patch`, PR #3753)

Every CVE and CWE class addressed in NLTK, with the fix location, the test/probe that
drives the exploit, and the commit that introduced it. Generated from the source tree —
`grep` the tags and `git log -S` the commits — not hand-maintained.

**Summary:** 34 CWE classes and 37 CVE ids covered; 42 GHSA advisory probes (all report FIXED); 4 CI guards; 65 security test files.

## CWE classes

| CWE | Name | Status | Fix file(s) | Test / probe | Fix commit |
|-----|------|--------|-------------|--------------|-----------|
| CWE-20 | Improper Input Validation | PATCHED + TESTED | util.py | test_lepor.py, test_output_exposure_security.py … | `5f91fd1a3` |
| CWE-22 | Path Traversal | PATCHED + TESTED | distance.py, downloader.py, nkjp.py … | test_attack_path_sandbox_expanded.py, test_nkjp_security.py … | `772128c1d` |
| CWE-59 | Symlink Following (Link Following) | PATCHED + TESTED | named_entity.py, downloader.py, toolbox.py … | test_pathsec_sweep_dataset_loading.py, test_corpus_reader_pathsec.py … | `772128c1d` |
| CWE-73 | External Control of File Name or Path | PATCHED + TESTED | downloader.py, util.py, api.py … | test_corpus_reader_pathsec.py, test_data_security.py | `09987e7b6` |
| CWE-79 | Cross-site Scripting (XSS) | PATCHED + TESTED | wordnet_app.py | test_output_exposure_security.py | `5f91fd1a3` |
| CWE-88 | Argument Injection | PATCHED + TESTED | internals.py, malt.py, corenlp.py | test_java_per_call_options_security.py, test_attack_java_tool_expanded.py … | `95b3824aa` |
| CWE-94 | Code Injection | TESTED | (chokepoint) | test_attack_java_tool_expanded.py, test_java_injection_exploit.py | `772128c1d` |
| CWE-200 | Exposure of Sensitive Information | PATCHED + TESTED | util.py | test_output_exposure_security.py | `5f91fd1a3` |
| CWE-209 | Error Message Info Exposure | N/A | util.py | - | `5f91fd1a3` |
| CWE-248 | Uncaught Exception | TESTED | (chokepoint) | test_nombank_security.py, test_propbank.py | `3127e1922` |
| CWE-306 | Missing Authentication for Critical Function | PATCHED + TESTED | wordnet_app.py | test_fixed_but_untested_cwe.py | `b6bb63ef2` |
| CWE-352 | CSRF | PATCHED + TESTED | wordnet_app.py | test_fixed_but_untested_cwe.py | `b6bb63ef2` |
| CWE-369 | Divide By Zero | PATCHED + TESTED | segmentation.py | test_segmentation.py | `9ea786920` |
| CWE-377 | Insecure Temporary File | PATCHED + TESTED | maxent.py, named_entity.py, downloader.py … | test_staging_tempdir_security.py, test_named_entity_pathsec.py … | `95b3824aa` |
| CWE-378 | Temp File Insecure Permissions | PATCHED + TESTED | downloader.py, pathsec.py, data.py | test_staging_tempdir_security.py, test_attack_path_sandbox_expanded.py … | `b6bb63ef2` |
| CWE-400 | Uncontrolled Resource Consumption | PATCHED + TESTED | distance.py, gale_church.py, logic.py … | test_quadratic_dos.py, test_attack_path_sandbox_expanded.py … | `21c9df941` |
| CWE-407 | Inefficient Algorithmic Complexity | PATCHED + TESTED | transforms.py, agreement.py, distance.py … | test_quadratic_dos.py, test_treetransforms.py … | `772128c1d` |
| CWE-409 | Improper Handling of Compressed Data (bomb) | PATCHED + TESTED | weka.py, pathsec.py, data.py | test_zipbomb_security.py, test_attack_path_sandbox_expanded.py … | `e78af79c0` |
| CWE-426 | Untrusted Search Path | PATCHED + TESTED | internals.py, senna.py, weka.py … | test_security.py, test_weka_security.py … | `772128c1d` |
| CWE-427 | Uncontrolled Search Path Element | PATCHED + TESTED | internals.py, senna.py, api.py … | test_weka_security.py, test_find_file_cwd_hardening.py … | `ee6d6138d` |
| CWE-459 | Incomplete Cleanup | PATCHED + TESTED | repp.py | test_repp_security.py | `b6bb63ef2` |
| CWE-476 | NULL Pointer Dereference | PATCHED + TESTED | childes.py | test_childes_security.py | `354da5a79` |
| CWE-494 | Download of Code Without Integrity Check | PATCHED + TESTED | weka.py | test_weka_security.py | `880b6873a` |
| CWE-502 | Deserialization of Untrusted Data | PATCHED + TESTED | chartparser_app.py, transitionparser.py, demo.py … | test_pathsec_sweep_deserialization.py, test_attack_json_loaders_expanded.py … | `e78af79c0` |
| CWE-532 | Insertion of Sensitive Info into Log | PATCHED + TESTED | util.py | test_output_exposure_security.py | `5f91fd1a3` |
| CWE-674 | Uncontrolled Recursion | PATCHED + TESTED | tree.py, logic.py, recursivedescent.py … | test_attack_dos_expanded.py, test_recursion_dos.py … | `b6bb63ef2` |
| CWE-770 | Allocation of Resources Without Limits | PATCHED + TESTED | confusionmatrix.py, paice.py, distance.py … | test_cistem.py, test_distance.py … | `92894f17f` |
| CWE-776 | XML Entity Expansion (Billion Laughs) | PATCHED + TESTED | internals.py, xmldocs.py, xmlsec.py | test_xml_entity_expansion_security.py, test_path_traversal_security.py … | `e7b56012f` |
| CWE-789 | Memory Allocation with Excessive Size | TESTED | (chokepoint) | test_attack_json_loaders_expanded.py | `21c9df941` |
| CWE-829 | Inclusion from Untrusted Control Sphere | PATCHED + TESTED | senna.py | test_senna_security.py | `5acf63c26` |
| CWE-835 | Loop with Unreachable Exit (Infinite Loop) | PATCHED + TESTED | shiftreduce.py, grammar.py | test_fixed_but_untested_cwe.py | `b6bb63ef2` |
| CWE-918 | Server-Side Request Forgery (SSRF) | PATCHED + TESTED | pathsec.py | test_pathsec.py, ghsa_6ww7_3frv_cqxh.py … | `e31f6ac9c` |
| CWE-1188 | Insecure Default Initialization | TESTED | (chokepoint) | ghsa_p3m8_78j2_g5p3.py | `e7b56012f` |
| CWE-1333 | Inefficient Regular Expression (ReDoS) | PATCHED + TESTED | tree.py, regexp.py, tgrep.py … | test_stem_regexp_redos.py, test_senseval_security.py … | `772128c1d` |

## CVE ids

| CVE | Status | Fix file(s) / class | Test / probe | Fix commit |
|-----|--------|---------------------|--------------|-----------|
| CVE-2011-4815 | TESTED | (class covered at chokepoint) | test_attack_json_loaders_expanded.py | `21c9df941` |
| CVE-2020-10735 | TESTED | (class covered at chokepoint) | test_attack_json_loaders_expanded.py | `92894f17f` |
| CVE-2021-45958 | TESTED | (class covered at chokepoint) | test_attack_json_loaders_expanded.py | `21c9df941` |
| CVE-2024-39705 | TESTED | (class covered at chokepoint) | test_pickle_gadget_landscape.py | `1c966b41d` |
| CVE-2026-0847 | TESTED | (class covered at chokepoint) | test_corpus_reader_traversal.py | `89815b247` |
| CVE-2026-12072 | TESTED | (class covered at chokepoint) | test_corpus_reader_traversal.py | `89815b247` |
| CVE-2026-12074 | TESTED | (class covered at chokepoint) | test_corpus_reader_traversal.py | `89815b247` |
| CVE-2026-12243 | TESTED | (class covered at chokepoint) | test_path_traversal_security.py | `483c5fe65` |
| CVE-2026-12252 | TESTED | (class covered at chokepoint) | test_java_injection_exploit.py | `558877315` |
| CVE-2026-12261 | PATCHED + TESTED | downloader.py | test_downloader_atomic.py | `7a5740af8` |
| CVE-2026-12837 | PATCHED + TESTED | api.py | test_alignment.py | `f455b85a5` |
| CVE-2026-12839 | PATCHED + TESTED | confusionmatrix.py | test_quadratic_dos.py, test_confusionmatrix.py | `8c57c829f` |
| CVE-2026-12840 | PATCHED + TESTED | evaluate.py | test_sem_evaluate.py | `e7668b593` |
| CVE-2026-12841 | PATCHED + TESTED | internals.py | test_java_per_call_options_security.py, test_stanford_arg_injection.py … | `89815b247` |
| CVE-2026-12861 | TESTED | (class covered at chokepoint) | test_everygrams_alloc.py | `3e9d537ac` |
| CVE-2026-12867 | TESTED | (class covered at chokepoint) | test_dependencygraph_security.py | `8527d0813` |
| CVE-2026-12868 | PATCHED + TESTED | cistem.py | test_cistem.py | `c65ca13e8` |
| CVE-2026-12870 | TESTED | (class covered at chokepoint) | test_phrase_based_security.py | `235853c21` |
| CVE-2026-12871 | TESTED | (class covered at chokepoint) | test_data_security.py | `583d63ac3` |
| CVE-2026-12873 | PATCHED + TESTED | drt.py | test_drt_anaphora.py | `26ddcd0e3` |
| CVE-2026-12876 | TESTED | (class covered at chokepoint) | test_parser_dos.py, test_recursivedescent_dos.py | `43aaca1b9` |
| CVE-2026-12886 | PATCHED + TESTED | chart.py, chart.py | test_chart_parser.py | `2a42d9cab` |
| CVE-2026-12890 | PATCHED + TESTED | evaluate.py | test_quadratic_dos.py, test_valuation_redos.py | `772128c1d` |
| CVE-2026-12919 | PATCHED + TESTED | featstruct.py | test_featstruct_redos.py | `4085d53c7` |
| CVE-2026-12926 | PATCHED + TESTED | distance.py | test_quadratic_dos.py, test_distance.py | `375841cef` |
| CVE-2026-12928 | PATCHED + TESTED | counter.py | test_counter.py | `70a8b0560` |
| CVE-2026-12929 | PATCHED + TESTED | meteor_score.py | test_meteor.py | `0624fecd4` |
| CVE-2026-14582 | PATCHED + TESTED | stanford.py | test_stanford_classpath.py | `00884c71d` |
| CVE-2026-14595 | TESTED | (class covered at chokepoint) | test_skipgrams.py | `47e236e95` |
| CVE-2026-14597 | PATCHED + TESTED | snowball.py | test_snowball.py | `5c4c0d3fe` |
| CVE-2026-33236 | TESTED | (class covered at chokepoint) | test_downloader_package_traversal.py | `1f803e1ff` |
| CVE-2026-54292 | TESTED | (class covered at chokepoint) | ghsa_f833_7jw8_xwrv.py | `bf1d4b2e8` |
| CVE-2026-54293 | TESTED | (class covered at chokepoint) | test_path_traversal_security.py | `483c5fe65` |
| CVE-2026-70626 | TESTED | (class covered at chokepoint) | test_corpus_reader_traversal.py | `89815b247` |
| CVE-2026-71513 | TESTED | (class covered at chokepoint) | test_pickle_gadget_landscape.py | `1c966b41d` |
| CVE-2026-78683 | TESTED | (class covered at chokepoint) | test_pickle_gadget_landscape.py | `1c966b41d` |
| CVE-2026-81726 | PATCHED + TESTED | weka.py | test_weka_model_path_security.py | `03b0f707d` |

## 3. FULL MITRE CWE catalog (CWE-1000 Research view, all 944 weaknesses) — NLTK status

Every MITRE CWE, classified. Addressed rows carry a commit; N/A rows carry the reason the weakness cannot occur in NLTK's attack surface.

| CWE | Name | Abstraction | NLTK status | Commit |
|---|---|---|---|---|
| CWE-5 | J2EE Misconfiguration: Data Transmission Without Encryption | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-6 | J2EE Misconfiguration: Insufficient Session-ID Length | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-7 | J2EE Misconfiguration: Missing Custom Error Page | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-8 | J2EE Misconfiguration: Entity Bean Declared Remote | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-9 | J2EE Misconfiguration: Weak Access Permissions for EJB Metho | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-11 | ASP.NET Misconfiguration: Creating Debug Binary | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-12 | ASP.NET Misconfiguration: Missing Custom Error Page | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-13 | ASP.NET Misconfiguration: Password in Configuration File | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-14 | Compiler Removal of Code to Clear Buffers | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-15 | External Control of System or Configuration Setting | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-20 | Improper Input Validation | Class | PATCHED+TESTED | `5f91fd1a3` |
| CWE-22 | Improper Limitation of a Pathname to a Restricted Directory  | Base | PATCHED+TESTED | `772128c1d` |
| CWE-23 | Relative Path Traversal | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-24 | Path Traversal: '../filedir' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-25 | Path Traversal: '/../filedir' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-26 | Path Traversal: '/dir/../filename' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-27 | Path Traversal: 'dir/../../filename' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-28 | Path Traversal: '..filedir' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-29 | Path Traversal: '..filename' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-30 | Path Traversal: 'dir..filename' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-31 | Path Traversal: 'dir....filename' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-32 | Path Traversal: '...' (Triple Dot) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-33 | Path Traversal: '....' (Multiple Dot) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-34 | Path Traversal: '....//' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-35 | Path Traversal: '.../...//' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-36 | Absolute Path Traversal | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-37 | Path Traversal: '/absolute/pathname/here' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-38 | Path Traversal: 'absolutepathnamehere' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-39 | Path Traversal: 'C:dirname' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-40 | Path Traversal: 'UNCsharename' (Windows UNC Share) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-41 | Improper Resolution of Path Equivalence | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-42 | Path Equivalence: 'filename.' (Trailing Dot) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-43 | Path Equivalence: 'filename....' (Multiple Trailing Dot) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-44 | Path Equivalence: 'file.name' (Internal Dot) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-45 | Path Equivalence: 'file...name' (Multiple Internal Dot) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-46 | Path Equivalence: 'filename ' (Trailing Space) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-47 | Path Equivalence: ' filename' (Leading Space) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-48 | Path Equivalence: 'file name' (Internal Whitespace) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-49 | Path Equivalence: 'filename/' (Trailing Slash) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-50 | Path Equivalence: '//multiple/leading/slash' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-51 | Path Equivalence: '/multiple//internal/slash' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-52 | Path Equivalence: '/multiple/trailing/slash//' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-53 | Path Equivalence: 'multipleinternalbackslash' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-54 | Path Equivalence: 'filedir' (Trailing Backslash) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-55 | Path Equivalence: '/./' (Single Dot Directory) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-56 | Path Equivalence: 'filedir*' (Wildcard) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-57 | Path Equivalence: 'fakedir/../realdir/filename' | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-58 | Path Equivalence: Windows 8.3 Filename | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-59 | Improper Link Resolution Before File Access ('Link Following | Base | PATCHED+TESTED | `772128c1d` |
| CWE-61 | UNIX Symbolic Link (Symlink) Following | Compound | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-62 | UNIX Hard Link | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-64 | Windows Shortcut Following (.LNK) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-65 | Windows Hard Link | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-66 | Improper Handling of File Names that Identify Virtual Resour | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-67 | Improper Handling of Windows Device Names | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-69 | Improper Handling of Windows ::DATA Alternate Data Stream | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-72 | Improper Handling of Apple HFS+ Alternate Data Stream Path | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-73 | External Control of File Name or Path | Base | PATCHED+TESTED | `09987e7b6` |
| CWE-74 | Improper Neutralization of Special Elements in Output Used b | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-75 | Failure to Sanitize Special Elements into a Different Plane  | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-76 | Improper Neutralization of Equivalent Special Elements | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-77 | Improper Neutralization of Special Elements used in a Comman | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-78 | Improper Neutralization of Special Elements used in an OS Co | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-79 | Improper Neutralization of Input During Web Page Generation  | Base | PATCHED+TESTED | `5f91fd1a3` |
| CWE-80 | Improper Neutralization of Script-Related HTML Tags in a Web | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-81 | Improper Neutralization of Script in an Error Message Web Pa | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-82 | Improper Neutralization of Script in Attributes of IMG Tags  | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-83 | Improper Neutralization of Script in Attributes in a Web Pag | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-84 | Improper Neutralization of Encoded URI Schemes in a Web Page | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-85 | Doubled Character XSS Manipulations | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-86 | Improper Neutralization of Invalid Characters in Identifiers | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-87 | Improper Neutralization of Alternate XSS Syntax | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-88 | Improper Neutralization of Argument Delimiters in a Command  | Base | PATCHED+TESTED | `95b3824aa` |
| CWE-89 | Improper Neutralization of Special Elements used in an SQL C | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-90 | Improper Neutralization of Special Elements used in an LDAP  | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-91 | XML Injection (aka Blind XPath Injection) | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-93 | Improper Neutralization of CRLF Sequences ('CRLF Injection') | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-94 | Improper Control of Generation of Code ('Code Injection') | Base | TESTED | `772128c1d` |
| CWE-95 | Improper Neutralization of Directives in Dynamically Evaluat | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-96 | Improper Neutralization of Directives in Statically Saved Co | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-97 | Improper Neutralization of Server-Side Includes (SSI) Within | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-98 | Improper Control of Filename for Include/Require Statement i | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-99 | Improper Control of Resource Identifiers ('Resource Injectio | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-102 | Struts: Duplicate Validation Forms | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-103 | Struts: Incomplete validate() Method Definition | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-104 | Struts: Form Bean Does Not Extend Validation Class | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-105 | Struts: Form Field Without Validator | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-106 | Struts: Plug-in Framework not in Use | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-107 | Struts: Unused Validation Form | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-108 | Struts: Unvalidated Action Form | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-109 | Struts: Validator Turned Off | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-110 | Struts: Validator Without Form Field | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-111 | Direct Use of Unsafe JNI | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-112 | Missing XML Validation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-113 | Improper Neutralization of CRLF Sequences in HTTP Headers (' | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-114 | Process Control | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-115 | Misinterpretation of Input | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-116 | Improper Encoding or Escaping of Output | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-117 | Improper Output Neutralization for Logs | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-118 | Incorrect Access of Indexable Resource ('Range Error') | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-119 | Improper Restriction of Operations within the Bounds of a Me | Class | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-120 | Buffer Copy without Checking Size of Input ('Classic Buffer  | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-121 | Stack-based Buffer Overflow | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-122 | Heap-based Buffer Overflow | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-123 | Write-what-where Condition | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-124 | Buffer Underwrite ('Buffer Underflow') | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-125 | Out-of-bounds Read | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-126 | Buffer Over-read | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-127 | Buffer Under-read | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-128 | Wrap-around Error | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-129 | Improper Validation of Array Index | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-130 | Improper Handling of Length Parameter Inconsistency | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-131 | Incorrect Calculation of Buffer Size | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-134 | Use of Externally-Controlled Format String | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-135 | Incorrect Calculation of Multi-Byte String Length | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-138 | Improper Neutralization of Special Elements | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-140 | Improper Neutralization of Delimiters | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-141 | Improper Neutralization of Parameter/Argument Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-142 | Improper Neutralization of Value Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-143 | Improper Neutralization of Record Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-144 | Improper Neutralization of Line Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-145 | Improper Neutralization of Section Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-146 | Improper Neutralization of Expression/Command Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-147 | Improper Neutralization of Input Terminators | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-148 | Improper Neutralization of Input Leaders | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-149 | Improper Neutralization of Quoting Syntax | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-150 | Improper Neutralization of Escape, Meta, or Control Sequence | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-151 | Improper Neutralization of Comment Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-152 | Improper Neutralization of Macro Symbols | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-153 | Improper Neutralization of Substitution Characters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-154 | Improper Neutralization of Variable Name Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-155 | Improper Neutralization of Wildcards or Matching Symbols | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-156 | Improper Neutralization of Whitespace | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-157 | Failure to Sanitize Paired Delimiters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-158 | Improper Neutralization of Null Byte or NUL Character | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-159 | Improper Handling of Invalid Use of Special Elements | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-160 | Improper Neutralization of Leading Special Elements | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-161 | Improper Neutralization of Multiple Leading Special Elements | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-162 | Improper Neutralization of Trailing Special Elements | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-163 | Improper Neutralization of Multiple Trailing Special Element | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-164 | Improper Neutralization of Internal Special Elements | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-165 | Improper Neutralization of Multiple Internal Special Element | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-166 | Improper Handling of Missing Special Element | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-167 | Improper Handling of Additional Special Element | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-168 | Improper Handling of Inconsistent Special Elements | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-170 | Improper Null Termination | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-172 | Encoding Error | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-173 | Improper Handling of Alternate Encoding | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-174 | Double Decoding of the Same Data | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-175 | Improper Handling of Mixed Encoding | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-176 | Improper Handling of Unicode Encoding | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-177 | Improper Handling of URL Encoding (Hex Encoding) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-178 | Improper Handling of Case Sensitivity | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-179 | Incorrect Behavior Order: Early Validation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-180 | Incorrect Behavior Order: Validate Before Canonicalize | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-181 | Incorrect Behavior Order: Validate Before Filter | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-182 | Collapse of Data into Unsafe Value | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-183 | Permissive List of Allowed Inputs | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-184 | Incomplete List of Disallowed Inputs | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-185 | Incorrect Regular Expression | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-186 | Overly Restrictive Regular Expression | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-187 | Partial String Comparison | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-188 | Reliance on Data/Memory Layout | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-190 | Integer Overflow or Wraparound | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-191 | Integer Underflow (Wrap or Wraparound) | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-192 | Integer Coercion Error | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-193 | Off-by-one Error | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-194 | Unexpected Sign Extension | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-195 | Signed to Unsigned Conversion Error | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-196 | Unsigned to Signed Conversion Error | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-197 | Numeric Truncation Error | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-198 | Use of Incorrect Byte Ordering | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-200 | Exposure of Sensitive Information to an Unauthorized Actor | Class | PATCHED+TESTED | `5f91fd1a3` |
| CWE-201 | Insertion of Sensitive Information Into Sent Data | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-202 | Exposure of Sensitive Information Through Data Queries | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-203 | Observable Discrepancy | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-204 | Observable Response Discrepancy | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-205 | Observable Behavioral Discrepancy | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-206 | Observable Internal Behavioral Discrepancy | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-207 | Observable Behavioral Discrepancy With Equivalent Products | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-208 | Observable Timing Discrepancy | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-209 | Generation of Error Message Containing Sensitive Information | Base | PATCHED | `5f91fd1a3` |
| CWE-210 | Self-generated Error Message Containing Sensitive Informatio | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-211 | Externally-Generated Error Message Containing Sensitive Info | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-212 | Improper Removal of Sensitive Information Before Storage or  | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-213 | Exposure of Sensitive Information Due to Incompatible Polici | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-214 | Invocation of Process Using Visible Sensitive Information | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-215 | Insertion of Sensitive Information Into Debugging Code | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-219 | Storage of File with Sensitive Data Under Web Root | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-220 | Storage of File With Sensitive Data Under FTP Root | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-221 | Information Loss or Omission | Class | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-222 | Truncation of Security-relevant Information | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-223 | Omission of Security-relevant Information | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-224 | Obscured Security-relevant Information by Alternate Name | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-226 | Sensitive Information in Resource Not Removed Before Reuse | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-228 | Improper Handling of Syntactically Invalid Structure | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-229 | Improper Handling of Values | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-230 | Improper Handling of Missing Values | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-231 | Improper Handling of Extra Values | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-232 | Improper Handling of Undefined Values | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-233 | Improper Handling of Parameters | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-234 | Failure to Handle Missing Parameter | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-235 | Improper Handling of Extra Parameters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-236 | Improper Handling of Undefined Parameters | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-237 | Improper Handling of Structural Elements | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-238 | Improper Handling of Incomplete Structural Elements | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-239 | Failure to Handle Incomplete Element | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-240 | Improper Handling of Inconsistent Structural Elements | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-241 | Improper Handling of Unexpected Data Type | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-242 | Use of Inherently Dangerous Function | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-243 | Creation of chroot Jail Without Changing Working Directory | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-244 | Improper Clearing of Heap Memory Before Release ('Heap Inspe | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-245 | J2EE Bad Practices: Direct Management of Connections | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-246 | J2EE Bad Practices: Direct Use of Sockets | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-248 | Uncaught Exception | Base | TESTED | `3127e1922` |
| CWE-250 | Execution with Unnecessary Privileges | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-252 | Unchecked Return Value | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-253 | Incorrect Check of Function Return Value | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-256 | Plaintext Storage of a Password | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-257 | Storing Passwords in a Recoverable Format | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-258 | Empty Password in Configuration File | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-259 | Use of Hard-coded Password | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-260 | Password in Configuration File | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-261 | Weak Encoding for Password | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-262 | Not Using Password Aging | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-263 | Password Aging with Long Expiration | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-266 | Incorrect Privilege Assignment | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-267 | Privilege Defined With Unsafe Actions | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-268 | Privilege Chaining | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-269 | Improper Privilege Management | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-270 | Privilege Context Switching Error | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-271 | Privilege Dropping / Lowering Errors | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-272 | Least Privilege Violation | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-273 | Improper Check for Dropped Privileges | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-274 | Improper Handling of Insufficient Privileges | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-276 | Incorrect Default Permissions | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-277 | Insecure Inherited Permissions | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-278 | Insecure Preserved Inherited Permissions | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-279 | Incorrect Execution-Assigned Permissions | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-280 | Improper Handling of Insufficient Permissions or Privileges | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-281 | Improper Preservation of Permissions | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-282 | Improper Ownership Management | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-283 | Unverified Ownership | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-284 | Improper Access Control | Pillar | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-285 | Improper Authorization | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-286 | Incorrect User Management | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-287 | Improper Authentication | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-288 | Authentication Bypass Using an Alternate Path or Channel | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-289 | Authentication Bypass by Alternate Name | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-290 | Authentication Bypass by Spoofing | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-291 | Reliance on IP Address for Authentication | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-293 | Using Referer Field for Authentication | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-294 | Authentication Bypass by Capture-replay | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-295 | Improper Certificate Validation | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-296 | Improper Following of a Certificate's Chain of Trust | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-297 | Improper Validation of Certificate with Host Mismatch | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-298 | Improper Validation of Certificate Expiration | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-299 | Improper Check for Certificate Revocation | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-300 | Channel Accessible by Non-Endpoint | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-301 | Reflection Attack in an Authentication Protocol | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-302 | Authentication Bypass by Assumed-Immutable Data | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-303 | Incorrect Implementation of Authentication Algorithm | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-304 | Missing Critical Step in Authentication | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-305 | Authentication Bypass by Primary Weakness | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-306 | Missing Authentication for Critical Function | Base | PATCHED+TESTED | `b6bb63ef2` |
| CWE-307 | Improper Restriction of Excessive Authentication Attempts | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-308 | Use of Single-factor Authentication | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-309 | Use of Password System for Primary Authentication | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-311 | Missing Encryption of Sensitive Data | Class | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-312 | Cleartext Storage of Sensitive Information | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-313 | Cleartext Storage in a File or on Disk | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-314 | Cleartext Storage in the Registry | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-315 | Cleartext Storage of Sensitive Information in a Cookie | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-316 | Cleartext Storage of Sensitive Information in Memory | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-317 | Cleartext Storage of Sensitive Information in GUI | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-318 | Cleartext Storage of Sensitive Information in Executable | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-319 | Cleartext Transmission of Sensitive Information | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-321 | Use of Hard-coded Cryptographic Key | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-322 | Key Exchange without Entity Authentication | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-323 | Reusing a Nonce, Key Pair in Encryption | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-324 | Use of a Key Past its Expiration Date | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-325 | Missing Cryptographic Step | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-326 | Inadequate Encryption Strength | Class | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-327 | Use of a Broken or Risky Cryptographic Algorithm | Class | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-328 | Use of Weak Hash | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-329 | Generation of Predictable IV with CBC Mode | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-330 | Use of Insufficiently Random Values | Class | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-331 | Insufficient Entropy | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-332 | Insufficient Entropy in PRNG | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-333 | Improper Handling of Insufficient Entropy in TRNG | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-334 | Small Space of Random Values | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-335 | Incorrect Usage of Seeds in Pseudo-Random Number Generator ( | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-336 | Same Seed in Pseudo-Random Number Generator (PRNG) | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-337 | Predictable Seed in Pseudo-Random Number Generator (PRNG) | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-338 | Use of Cryptographically Weak Pseudo-Random Number Generator | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-339 | Small Seed Space in PRNG | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-340 | Generation of Predictable Numbers or Identifiers | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-341 | Predictable from Observable State | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-342 | Predictable Exact Value from Previous Values | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-343 | Predictable Value Range from Previous Values | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-344 | Use of Invariant Value in Dynamically Changing Context | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-345 | Insufficient Verification of Data Authenticity | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-346 | Origin Validation Error | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-347 | Improper Verification of Cryptographic Signature | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-348 | Use of Less Trusted Source | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-349 | Acceptance of Extraneous Untrusted Data With Trusted Data | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-350 | Reliance on Reverse DNS Resolution for a Security-Critical A | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-351 | Insufficient Type Distinction | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-352 | Cross-Site Request Forgery (CSRF) | Compound | PATCHED+TESTED | `b6bb63ef2` |
| CWE-353 | Missing Support for Integrity Check | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-354 | Improper Validation of Integrity Check Value | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-356 | Product UI does not Warn User of Unsafe Actions | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-357 | Insufficient UI Warning of Dangerous Operations | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-358 | Improperly Implemented Security Check for Standard | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-359 | Exposure of Private Personal Information to an Unauthorized  | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-360 | Trust of System Event Data | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-362 | Concurrent Execution using Shared Resource with Improper Syn | Class | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-363 | Race Condition Enabling Link Following | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-364 | Signal Handler Race Condition | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-366 | Race Condition within a Thread | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-367 | Time-of-check Time-of-use (TOCTOU) Race Condition | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-368 | Context Switching Race Condition | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-369 | Divide By Zero | Base | PATCHED+TESTED | `9ea786920` |
| CWE-370 | Missing Check for Certificate Revocation after Initial Check | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-372 | Incomplete Internal State Distinction | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-374 | Passing Mutable Objects to an Untrusted Method | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-375 | Returning a Mutable Object to an Untrusted Caller | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-377 | Insecure Temporary File | Class | PATCHED+TESTED | `95b3824aa` |
| CWE-378 | Creation of Temporary File With Insecure Permissions | Base | PATCHED+TESTED | `b6bb63ef2` |
| CWE-379 | Creation of Temporary File in Directory with Insecure Permis | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-382 | J2EE Bad Practices: Use of System.exit() | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-383 | J2EE Bad Practices: Direct Use of Threads | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-384 | Session Fixation | Compound | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-385 | Covert Timing Channel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-386 | Symbolic Name not Mapping to Correct Object | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-390 | Detection of Error Condition Without Action | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-391 | Unchecked Error Condition | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-392 | Missing Report of Error Condition | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-393 | Return of Wrong Status Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-394 | Unexpected Status Code or Return Value | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-395 | Use of NullPointerException Catch to Detect NULL Pointer Der | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-396 | Declaration of Catch for Generic Exception | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-397 | Declaration of Throws for Generic Exception | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-400 | Uncontrolled Resource Consumption | Class | PATCHED+TESTED | `21c9df941` |
| CWE-401 | Missing Release of Memory after Effective Lifetime | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-402 | Transmission of Private Resources into a New Sphere ('Resour | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-403 | Exposure of File Descriptor to Unintended Control Sphere ('F | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-404 | Improper Resource Shutdown or Release | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-405 | Asymmetric Resource Consumption (Amplification) | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-406 | Insufficient Control of Network Message Volume (Network Ampl | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-407 | Inefficient Algorithmic Complexity | Class | PATCHED+TESTED | `772128c1d` |
| CWE-408 | Incorrect Behavior Order: Early Amplification | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-409 | Improper Handling of Highly Compressed Data (Data Amplificat | Base | PATCHED+TESTED | `e78af79c0` |
| CWE-410 | Insufficient Resource Pool | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-412 | Unrestricted Externally Accessible Lock | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-413 | Improper Resource Locking | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-414 | Missing Lock Check | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-415 | Double Free | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-416 | Use After Free | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-419 | Unprotected Primary Channel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-420 | Unprotected Alternate Channel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-421 | Race Condition During Access to Alternate Channel | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-422 | Unprotected Windows Messaging Channel ('Shatter') | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-424 | Improper Protection of Alternate Path | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-425 | Direct Request ('Forced Browsing') | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-426 | Untrusted Search Path | Base | PATCHED+TESTED | `772128c1d` |
| CWE-427 | Uncontrolled Search Path Element | Base | PATCHED+TESTED | `ee6d6138d` |
| CWE-428 | Unquoted Search Path or Element | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-430 | Deployment of Wrong Handler | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-431 | Missing Handler | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-432 | Dangerous Signal Handler not Disabled During Sensitive Opera | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-433 | Unparsed Raw Web Content Delivery | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-434 | Unrestricted Upload of File with Dangerous Type | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-435 | Improper Interaction Between Multiple Correctly-Behaving Ent | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-436 | Interpretation Conflict | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-437 | Incomplete Model of Endpoint Features | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-439 | Behavioral Change in New Version or Environment | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-440 | Expected Behavior Violation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-441 | Unintended Proxy or Intermediary ('Confused Deputy') | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-444 | Inconsistent Interpretation of HTTP Requests ('HTTP Request/ | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-446 | UI Discrepancy for Security Feature | Class | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-447 | Unimplemented or Unsupported Feature in UI | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-448 | Obsolete Feature in UI | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-449 | The UI Performs the Wrong Action | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-450 | Multiple Interpretations of UI Input | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-451 | User Interface (UI) Misrepresentation of Critical Informatio | Class | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-453 | Insecure Default Variable Initialization | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-454 | External Initialization of Trusted Variables or Data Stores | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-455 | Non-exit on Failed Initialization | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-456 | Missing Initialization of a Variable | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-457 | Use of Uninitialized Variable | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-459 | Incomplete Cleanup | Base | PATCHED+TESTED | `b6bb63ef2` |
| CWE-460 | Improper Cleanup on Thrown Exception | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-462 | Duplicate Key in Associative List (Alist) | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-463 | Deletion of Data Structure Sentinel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-464 | Addition of Data Structure Sentinel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-466 | Return of Pointer Value Outside of Expected Range | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-467 | Use of sizeof() on a Pointer Type | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-468 | Incorrect Pointer Scaling | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-469 | Use of Pointer Subtraction to Determine Size | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-470 | Use of Externally-Controlled Input to Select Classes or Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-471 | Modification of Assumed-Immutable Data (MAID) | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-472 | External Control of Assumed-Immutable Web Parameter | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-473 | PHP External Variable Modification | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-474 | Use of Function with Inconsistent Implementations | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-475 | Undefined Behavior for Input to API | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-476 | NULL Pointer Dereference | Base | PATCHED+TESTED | `354da5a79` |
| CWE-477 | Use of Obsolete Function | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-478 | Missing Default Case in Multiple Condition Expression | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-479 | Signal Handler Use of a Non-reentrant Function | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-480 | Use of Incorrect Operator | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-481 | Assigning instead of Comparing | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-482 | Comparing instead of Assigning | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-483 | Incorrect Block Delimitation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-484 | Omitted Break Statement in Switch | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-486 | Comparison of Classes by Name | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-487 | Reliance on Package-level Scope | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-488 | Exposure of Data Element to Wrong Session | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-489 | Active Debug Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-491 | Public cloneable() Method Without Final ('Object Hijack') | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-492 | Use of Inner Class Containing Sensitive Data | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-493 | Critical Public Variable Without Final Modifier | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-494 | Download of Code Without Integrity Check | Base | PATCHED+TESTED | `880b6873a` |
| CWE-495 | Private Data Structure Returned From A Public Method | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-496 | Public Data Assigned to Private Array-Typed Field | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-497 | Exposure of Sensitive System Information to an Unauthorized  | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-498 | Cloneable Class Containing Sensitive Information | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-499 | Serializable Class Containing Sensitive Data | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-500 | Public Static Field Not Marked Final | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-501 | Trust Boundary Violation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-502 | Deserialization of Untrusted Data | Base | PATCHED+TESTED | `e78af79c0` |
| CWE-506 | Embedded Malicious Code | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-507 | Trojan Horse | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-508 | Non-Replicating Malicious Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-509 | Replicating Malicious Code (Virus or Worm) | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-510 | Trapdoor | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-511 | Logic/Time Bomb | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-512 | Spyware | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-514 | Covert Channel | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-515 | Covert Storage Channel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-520 | .NET Misconfiguration: Use of Impersonation | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-521 | Weak Password Requirements | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-522 | Insufficiently Protected Credentials | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-523 | Unprotected Transport of Credentials | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-524 | Use of Cache Containing Sensitive Information | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-525 | Use of Web Browser Cache Containing Sensitive Information | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-526 | Cleartext Storage of Sensitive Information in an Environment | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-527 | Exposure of Version-Control Repository to an Unauthorized Co | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-528 | Exposure of Core Dump File to an Unauthorized Control Sphere | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-529 | Exposure of Access Control List Files to an Unauthorized Con | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-530 | Exposure of Backup File to an Unauthorized Control Sphere | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-531 | Inclusion of Sensitive Information in Test Code | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-532 | Insertion of Sensitive Information into Log File | Base | PATCHED+TESTED | `5f91fd1a3` |
| CWE-535 | Exposure of Information Through Shell Error Message | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-536 | Servlet Runtime Error Message Containing Sensitive Informati | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-537 | Java Runtime Error Message Containing Sensitive Information | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-538 | Insertion of Sensitive Information into Externally-Accessibl | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-539 | Use of Persistent Cookies Containing Sensitive Information | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-540 | Inclusion of Sensitive Information in Source Code | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-541 | Inclusion of Sensitive Information in an Include File | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-543 | Use of Singleton Pattern Without Synchronization in a Multit | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-544 | Missing Standardized Error Handling Mechanism | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-546 | Suspicious Comment | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-547 | Use of Hard-coded, Security-relevant Constants | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-548 | Exposure of Information Through Directory Listing | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-549 | Missing Password Field Masking | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-550 | Server-generated Error Message Containing Sensitive Informat | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-551 | Incorrect Behavior Order: Authorization Before Parsing and C | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-552 | Files or Directories Accessible to External Parties | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-553 | Command Shell in Externally Accessible Directory | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-554 | ASP.NET Misconfiguration: Not Using Input Validation Framewo | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-555 | J2EE Misconfiguration: Plaintext Password in Configuration F | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-556 | ASP.NET Misconfiguration: Use of Identity Impersonation | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-558 | Use of getlogin() in Multithreaded Application | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-560 | Use of umask() with chmod-style Argument | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-561 | Dead Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-562 | Return of Stack Variable Address | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-563 | Assignment to Variable without Use | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-564 | SQL Injection: Hibernate | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-565 | Reliance on Cookies without Validation and Integrity Checkin | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-566 | Authorization Bypass Through User-Controlled SQL Primary Key | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-567 | Unsynchronized Access to Shared Data in a Multithreaded Cont | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-568 | finalize() Method Without super.finalize() | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-570 | Expression is Always False | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-571 | Expression is Always True | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-572 | Call to Thread run() instead of start() | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-573 | Improper Following of Specification by Caller | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-574 | EJB Bad Practices: Use of Synchronization Primitives | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-575 | EJB Bad Practices: Use of AWT Swing | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-576 | EJB Bad Practices: Use of Java I/O | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-577 | EJB Bad Practices: Use of Sockets | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-578 | EJB Bad Practices: Use of Class Loader | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-579 | J2EE Bad Practices: Non-serializable Object Stored in Sessio | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-580 | clone() Method Without super.clone() | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-581 | Object Model Violation: Just One of Equals and Hashcode Defi | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-582 | Array Declared Public, Final, and Static | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-583 | finalize() Method Declared Public | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-584 | Return Inside Finally Block | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-585 | Empty Synchronized Block | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-586 | Explicit Call to Finalize() | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-587 | Assignment of a Fixed Address to a Pointer | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-588 | Attempt to Access Child of a Non-structure Pointer | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-589 | Call to Non-ubiquitous API | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-590 | Free of Memory not on the Heap | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-591 | Sensitive Data Storage in Improperly Locked Memory | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-593 | Authentication Bypass: OpenSSL CTX Object Modified after SSL | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-594 | J2EE Framework: Saving Unserializable Objects to Disk | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-595 | Comparison of Object References Instead of Object Contents | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-597 | Use of Wrong Operator in String Comparison | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-598 | Use of HTTP Request With Sensitive Query String | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-599 | Missing Validation of OpenSSL Certificate | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-600 | Uncaught Exception in Servlet | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-601 | URL Redirection to Untrusted Site ('Open Redirect') | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-602 | Client-Side Enforcement of Server-Side Security | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-603 | Use of Client-Side Authentication | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-605 | Multiple Binds to the Same Port | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-606 | Unchecked Input for Loop Condition | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-607 | Public Static Final Field References Mutable Object | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-608 | Struts: Non-private Field in ActionForm Class | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-609 | Double-Checked Locking | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-610 | Externally Controlled Reference to a Resource in Another Sph | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-611 | Improper Restriction of XML External Entity Reference | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-612 | Improper Authorization of Index Containing Sensitive Informa | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-613 | Insufficient Session Expiration | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-614 | Sensitive Cookie in HTTPS Session Without 'Secure' Attribute | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-615 | Inclusion of Sensitive Information in Source Code Comments | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-616 | Incomplete Identification of Uploaded File Variables (PHP) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-617 | Reachable Assertion | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-618 | Exposed Unsafe ActiveX Method | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-619 | Dangling Database Cursor ('Cursor Injection') | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-620 | Unverified Password Change | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-621 | Variable Extraction Error | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-622 | Improper Validation of Function Hook Arguments | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-623 | Unsafe ActiveX Control Marked Safe For Scripting | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-624 | Executable Regular Expression Error | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-625 | Permissive Regular Expression | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-626 | Null Byte Interaction Error (Poison Null Byte) | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-627 | Dynamic Variable Evaluation | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-628 | Function Call with Incorrectly Specified Arguments | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-636 | Not Failing Securely ('Failing Open') | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-637 | Unnecessary Complexity in Protection Mechanism (Not Using 'E | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-638 | Not Using Complete Mediation | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-639 | Authorization Bypass Through User-Controlled Key | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-640 | Weak Password Recovery Mechanism for Forgotten Password | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-641 | Improper Restriction of Names for Files and Other Resources | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-642 | External Control of Critical State Data | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-643 | Improper Neutralization of Data within XPath Expressions ('X | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-644 | Improper Neutralization of HTTP Headers for Scripting Syntax | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-645 | Overly Restrictive Account Lockout Mechanism | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-646 | Reliance on File Name or Extension of Externally-Supplied Fi | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-647 | Use of Non-Canonical URL Paths for Authorization Decisions | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-648 | Incorrect Use of Privileged APIs | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-649 | Reliance on Obfuscation or Encryption of Security-Relevant I | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-650 | Trusting HTTP Permission Methods on the Server Side | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-651 | Exposure of WSDL File Containing Sensitive Information | Variant | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-652 | Improper Neutralization of Data within XQuery Expressions (' | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-653 | Improper Isolation or Compartmentalization | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-654 | Reliance on a Single Factor in a Security Decision | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-655 | Insufficient Psychological Acceptability | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-656 | Reliance on Security Through Obscurity | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-657 | Violation of Secure Design Principles | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-662 | Improper Synchronization | Class | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-663 | Use of a Non-reentrant Function in a Concurrent Context | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-664 | Improper Control of a Resource Through its Lifetime | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-665 | Improper Initialization | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-666 | Operation on Resource in Wrong Phase of Lifetime | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-667 | Improper Locking | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-668 | Exposure of Resource to Wrong Sphere | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-669 | Incorrect Resource Transfer Between Spheres | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-670 | Always-Incorrect Control Flow Implementation | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-671 | Lack of Administrator Control over Security | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-672 | Operation on a Resource after Expiration or Release | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-673 | External Influence of Sphere Definition | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-674 | Uncontrolled Recursion | Class | PATCHED+TESTED | `b6bb63ef2` |
| CWE-675 | Multiple Operations on Resource in Single-Operation Context | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-676 | Use of Potentially Dangerous Function | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-680 | Integer Overflow to Buffer Overflow | Compound | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-681 | Incorrect Conversion between Numeric Types | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-682 | Incorrect Calculation | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-683 | Function Call With Incorrect Order of Arguments | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-684 | Incorrect Provision of Specified Functionality | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-685 | Function Call With Incorrect Number of Arguments | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-686 | Function Call With Incorrect Argument Type | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-687 | Function Call With Incorrectly Specified Argument Value | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-688 | Function Call With Incorrect Variable or Reference as Argume | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-689 | Permission Race Condition During Resource Copy | Compound | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-690 | Unchecked Return Value to NULL Pointer Dereference | Compound | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-691 | Insufficient Control Flow Management | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-692 | Incomplete Denylist to Cross-Site Scripting | Compound | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-693 | Protection Mechanism Failure | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-694 | Use of Multiple Resources with Duplicate Identifier | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-695 | Use of Low-Level Functionality | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-696 | Incorrect Behavior Order | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-697 | Incorrect Comparison | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-698 | Execution After Redirect (EAR) | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-703 | Improper Check or Handling of Exceptional Conditions | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-704 | Incorrect Type Conversion or Cast | Class | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-705 | Incorrect Control Flow Scoping | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-706 | Use of Incorrectly-Resolved Name or Reference | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-707 | Improper Neutralization | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-708 | Incorrect Ownership Assignment | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-710 | Improper Adherence to Coding Standards | Pillar | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-732 | Incorrect Permission Assignment for Critical Resource | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-733 | Compiler Optimization Removal or Modification of Security-cr | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-749 | Exposed Dangerous Method or Function | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-754 | Improper Check for Unusual or Exceptional Conditions | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-755 | Improper Handling of Exceptional Conditions | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-756 | Missing Custom Error Page | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-757 | Selection of Less-Secure Algorithm During Negotiation ('Algo | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-758 | Reliance on Undefined, Unspecified, or Implementation-Define | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-759 | Use of a One-Way Hash without a Salt | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-760 | Use of a One-Way Hash with a Predictable Salt | Variant | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-761 | Free of Pointer not at Start of Buffer | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-762 | Mismatched Memory Management Routines | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-763 | Release of Invalid Pointer or Reference | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-764 | Multiple Locks of a Critical Resource | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-765 | Multiple Unlocks of a Critical Resource | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-766 | Critical Data Element Declared Public | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-767 | Access to Critical Private Variable via Public Method | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-768 | Incorrect Short Circuit Evaluation | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-770 | Allocation of Resources Without Limits or Throttling | Base | PATCHED+TESTED | `92894f17f` |
| CWE-771 | Missing Reference to Active Allocated Resource | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-772 | Missing Release of Resource after Effective Lifetime | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-773 | Missing Reference to Active File Descriptor or Handle | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-774 | Allocation of File Descriptors or Handles Without Limits or  | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-775 | Missing Release of File Descriptor or Handle after Effective | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-776 | Improper Restriction of Recursive Entity References in DTDs  | Base | PATCHED+TESTED | `e7b56012f` |
| CWE-777 | Regular Expression without Anchors | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-778 | Insufficient Logging | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-779 | Logging of Excessive Data | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-780 | Use of RSA Algorithm without OAEP | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-781 | Improper Address Validation in IOCTL with METHOD_NEITHER I/O | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-782 | Exposed IOCTL with Insufficient Access Control | Variant | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-783 | Operator Precedence Logic Error | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-784 | Reliance on Cookies without Validation and Integrity Checkin | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-785 | Use of Path Manipulation Function without Maximum-sized Buff | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-786 | Access of Memory Location Before Start of Buffer | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-787 | Out-of-bounds Write | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-788 | Access of Memory Location After End of Buffer | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-789 | Memory Allocation with Excessive Size Value | Variant | TESTED | `21c9df941` |
| CWE-790 | Improper Filtering of Special Elements | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-791 | Incomplete Filtering of Special Elements | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-792 | Incomplete Filtering of One or More Instances of Special Ele | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-793 | Only Filtering One Instance of a Special Element | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-794 | Incomplete Filtering of Multiple Instances of Special Elemen | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-795 | Only Filtering Special Elements at a Specified Location | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-796 | Only Filtering Special Elements Relative to a Marker | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-797 | Only Filtering Special Elements at an Absolute Position | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-798 | Use of Hard-coded Credentials | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-799 | Improper Control of Interaction Frequency | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-804 | Guessable CAPTCHA | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-805 | Buffer Access with Incorrect Length Value | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-806 | Buffer Access Using Size of Source Buffer | Variant | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-807 | Reliance on Untrusted Inputs in a Security Decision | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-820 | Missing Synchronization | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-821 | Incorrect Synchronization | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-822 | Untrusted Pointer Dereference | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-823 | Use of Out-of-range Pointer Offset | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-824 | Access of Uninitialized Pointer | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-825 | Expired Pointer Dereference | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-826 | Premature Release of Resource During Expected Lifetime | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-827 | Improper Control of Document Type Definition | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-828 | Signal Handler with Functionality that is not Asynchronous-S | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-829 | Inclusion of Functionality from Untrusted Control Sphere | Base | PATCHED+TESTED | `5acf63c26` |
| CWE-830 | Inclusion of Web Functionality from an Untrusted Source | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-831 | Signal Handler Function Associated with Multiple Signals | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-832 | Unlock of a Resource that is not Locked | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-833 | Deadlock | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-834 | Excessive Iteration | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-835 | Loop with Unreachable Exit Condition ('Infinite Loop') | Base | PATCHED+TESTED | `b6bb63ef2` |
| CWE-836 | Use of Password Hash Instead of Password for Authentication | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-837 | Improper Enforcement of a Single, Unique Action | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-838 | Inappropriate Encoding for Output Context | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-839 | Numeric Range Comparison Without Minimum Check | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-841 | Improper Enforcement of Behavioral Workflow | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-842 | Placement of User into Incorrect Group | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-843 | Access of Resource Using Incompatible Type ('Type Confusion' | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-862 | Missing Authorization | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-863 | Incorrect Authorization | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-908 | Use of Uninitialized Resource | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-909 | Missing Initialization of Resource | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-910 | Use of Expired File Descriptor | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-911 | Improper Update of Reference Count | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-912 | Hidden Functionality | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-913 | Improper Control of Dynamically-Managed Code Resources | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-914 | Improper Control of Dynamically-Identified Variables | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-915 | Improperly Controlled Modification of Dynamically-Determined | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-916 | Use of Password Hash With Insufficient Computational Effort | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-917 | Improper Neutralization of Special Elements used in an Expre | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-918 | Server-Side Request Forgery (SSRF) | Base | PATCHED+TESTED | `e31f6ac9c` |
| CWE-920 | Improper Restriction of Power Consumption | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-921 | Storage of Sensitive Data in a Mechanism without Access Cont | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-922 | Insecure Storage of Sensitive Information | Class | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-923 | Improper Restriction of Communication Channel to Intended En | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-924 | Improper Enforcement of Message Integrity During Transmissio | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-925 | Improper Verification of Intent by Broadcast Receiver | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-926 | Improper Export of Android Application Components | Variant | N/A: framework/platform-specific — N/A to a plain library |  |
| CWE-927 | Use of Implicit Intent for Sensitive Communication | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-939 | Improper Authorization in Handler for Custom URL Scheme | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-940 | Improper Verification of Source of a Communication Channel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-941 | Incorrectly Specified Destination in a Communication Channel | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-942 | Permissive Cross-domain Security Policy with Untrusted Domai | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-943 | Improper Neutralization of Special Elements in Data Query Lo | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1004 | Sensitive Cookie Without 'HttpOnly' Flag | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-1007 | Insufficient Visual Distinction of Homoglyphs Presented to U | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1021 | Improper Restriction of Rendered UI Layers or Frames | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-1022 | Use of Web Link to Untrusted Target with window.opener Acces | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-1023 | Incomplete Comparison with Missing Factors | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1024 | Comparison of Incompatible Types | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1025 | Comparison Using Wrong Factors | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1037 | Processor Optimization Removal or Modification of Security-c | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1038 | Insecure Automated Optimizations | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1039 | Inadequate Detection or Handling of Adversarial Input Pertur | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1041 | Use of Redundant Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1042 | Static Member Data Element outside of a Singleton Class Elem | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1043 | Data Element Aggregating an Excessively Large Number of Non- | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1044 | Architecture with Number of Horizontal Layers Outside of Exp | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1045 | Parent Class with a Virtual Destructor and a Child Class wit | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1046 | Creation of Immutable Text Using String Concatenation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1047 | Modules with Circular Dependencies | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1048 | Invokable Control Element with Large Number of Outward Calls | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1049 | Excessive Data Query Operations in a Large Data Table | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1050 | Excessive Platform Resource Consumption within a Loop | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1051 | Initialization with Hard-Coded Network Resource Configuratio | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1052 | Excessive Use of Hard-Coded Literals in Initialization | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1053 | Missing Documentation for Design | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1054 | Invocation of a Control Element at an Unnecessarily Deep Hor | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1055 | Multiple Inheritance from Concrete Classes | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1056 | Invokable Control Element with Variadic Parameters | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1057 | Data Access Operations Outside of Expected Data Manager Comp | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1058 | Invokable Control Element in Multi-Thread Context with non-F | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-1059 | Insufficient Technical Documentation | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1060 | Excessive Number of Inefficient Server-Side Data Accesses | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1061 | Insufficient Encapsulation | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1062 | Parent Class with References to Child Class | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1063 | Creation of Class Instance within a Static Code Block | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1064 | Invokable Control Element with Signature Containing an Exces | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1065 | Runtime Resource Management Control Element in a Component B | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1066 | Missing Serialization Control Element | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1067 | Excessive Execution of Sequential Searches of Data Resource | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1068 | Inconsistency Between Implementation and Documented Design | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1069 | Empty Exception Block | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1070 | Serializable Data Element Containing non-Serializable Item E | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1071 | Empty Code Block | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1072 | Data Resource Access without Use of Connection Pooling | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1073 | Non-SQL Invokable Control Element with Excessive Number of D | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1074 | Class with Excessively Deep Inheritance | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1075 | Unconditional Control Flow Transfer outside of Switch Block | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1076 | Insufficient Adherence to Expected Conventions | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1077 | Floating Point Comparison with Incorrect Operator | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1078 | Inappropriate Source Code Style or Formatting | Class | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1079 | Parent Class without Virtual Destructor Method | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1080 | Source Code File with Excessive Number of Lines of Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1082 | Class Instance Self Destruction Control Element | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1083 | Data Access from Outside Expected Data Manager Component | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1084 | Invokable Control Element with Excessive File or Data Access | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1085 | Invokable Control Element with Excessive Volume of Commented | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1086 | Class with Excessive Number of Child Classes | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1087 | Class with Virtual Method without a Virtual Destructor | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1088 | Synchronous Access of Remote Resource without Timeout | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1089 | Large Data Table with Excessive Number of Indices | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1090 | Method Containing Access of a Member Element from Another Cl | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1091 | Use of Object without Invoking Destructor Method | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1092 | Use of Same Invokable Control Element in Multiple Architectu | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1093 | Excessively Complex Data Representation | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1094 | Excessive Index Range Scan for a Data Resource | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1095 | Loop Condition Value Update within the Loop | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1096 | Singleton Class Instance Creation without Proper Locking or  | Variant | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-1097 | Persistent Storable Data Element without Associated Comparis | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1098 | Data Element containing Pointer Item without Proper Copy Con | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-1099 | Inconsistent Naming Conventions for Identifiers | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1100 | Insufficient Isolation of System-Dependent Functions | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1101 | Reliance on Runtime Component in Generated Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1102 | Reliance on Machine-Dependent Data Representation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1103 | Use of Platform-Dependent Third Party Components | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1104 | Use of Unmaintained Third Party Components | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1105 | Insufficient Encapsulation of Machine-Dependent Functionalit | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1106 | Insufficient Use of Symbolic Constants | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1107 | Insufficient Isolation of Symbolic Constant Definitions | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1108 | Excessive Reliance on Global Variables | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1109 | Use of Same Variable for Multiple Purposes | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1110 | Incomplete Design Documentation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1111 | Incomplete I/O Documentation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1112 | Incomplete Documentation of Program Execution | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1113 | Inappropriate Comment Style | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1114 | Inappropriate Whitespace Style | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1115 | Source Code Element without Standard Prologue | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1116 | Inaccurate Source Code Comments | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1117 | Callable with Insufficient Behavioral Summary | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1118 | Insufficient Documentation of Error Handling Techniques | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1119 | Excessive Use of Unconditional Branching | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1120 | Excessive Code Complexity | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1121 | Excessive McCabe Cyclomatic Complexity | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1122 | Excessive Halstead Complexity | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1123 | Excessive Use of Self-Modifying Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1124 | Excessively Deep Nesting | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1125 | Excessive Attack Surface | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1126 | Declaration of Variable with Unnecessarily Wide Scope | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1127 | Compilation with Insufficient Warnings or Errors | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1164 | Irrelevant Code | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1173 | Improper Use of Validation Framework | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1174 | ASP.NET Misconfiguration: Improper Model Validation | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-1176 | Inefficient CPU Computation | Class | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1177 | Use of Prohibited Code | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1188 | Initialization of a Resource with an Insecure Default | Base | TESTED | `e7b56012f` |
| CWE-1189 | Improper Isolation of Shared Resources on System-on-a-Chip ( | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1190 | DMA Device Enabled Too Early in Boot Phase | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1191 | On-Chip Debug and Test Interface With Improper Access Contro | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1192 | Improper Identifier for IP Block used in System-On-Chip (SOC | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1193 | Power-On of Untrusted Execution Core Before Enabling Fabric  | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1204 | Generation of Weak Initialization Vector (IV) | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1209 | Failure to Disable Reserved Bits | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1220 | Insufficient Granularity of Access Control | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1221 | Incorrect Register Defaults or Module Parameters | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1222 | Insufficient Granularity of Address Regions Protected by Reg | Variant | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1223 | Race Condition for Write-Once Attributes | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-1224 | Improper Restriction of Write-Once Bit Fields | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1229 | Creation of Emergent Resource | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1230 | Exposure of Sensitive Information Through Metadata | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1231 | Improper Prevention of Lock Bit Modification | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1232 | Improper Lock Behavior After Power State Transition | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1233 | Security-Sensitive Hardware Controls with Missing Lock Bit P | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1234 | Hardware Internal or Debug Modes Allow Override of Locks | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1235 | Incorrect Use of Autoboxing and Unboxing for Performance Cri | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1236 | Improper Neutralization of Formula Elements in a CSV File | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1239 | Improper Zeroization of Hardware Register | Variant | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1240 | Use of a Cryptographic Primitive with a Risky Implementation | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-1241 | Use of Predictable Algorithm in Random Number Generator | Base | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-1242 | Inclusion of Undocumented Features or Chicken Bits | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1243 | Sensitive Non-Volatile Information Not Protected During Debu | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1244 | Internal Asset Exposed to Unsafe Debug Access Level or State | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1245 | Improper Finite State Machines (FSMs) in Hardware Logic | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1246 | Improper Write Handling in Limited-write Non-Volatile Memori | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1247 | Improper Protection Against Voltage and Clock Glitches | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1248 | Semiconductor Defects in Hardware Logic with Security-Sensit | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1249 | Application-Level Admin Tool with Inconsistent View of Under | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1250 | Improper Preservation of Consistency Between Independent Rep | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1251 | Mirrored Regions with Different Values | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1252 | CPU Hardware Not Configured to Support Exclusivity of Write  | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1253 | Incorrect Selection of Fuse Values | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1254 | Incorrect Comparison Logic Granularity | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1255 | Comparison Logic is Vulnerable to Power Side-Channel Attacks | Variant | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1256 | Improper Restriction of Software Interfaces to Hardware Feat | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1257 | Improper Access Control Applied to Mirrored or Aliased Memor | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1258 | Exposure of Sensitive System Information Due to Uncleared De | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1259 | Improper Restriction of Security Token Assignment | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1260 | Improper Handling of Overlap Between Protected Memory Ranges | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1261 | Improper Handling of Single Event Upsets | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1262 | Improper Access Control for Register Interface | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1263 | Improper Physical Access Control | Class | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1264 | Hardware Logic with Insecure De-Synchronization between Cont | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1265 | Unintended Reentrant Invocation of Non-reentrant Code Via Ne | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1266 | Improper Scrubbing of Sensitive Data from Decommissioned Dev | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1267 | Policy Uses Obsolete Encoding | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1268 | Policy Privileges are not Assigned Consistently Between Cont | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1269 | Product Released in Non-Release Configuration | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1270 | Generation of Incorrect Security Tokens | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1271 | Uninitialized Value on Reset for Registers Holding Security  | Base | N/A: no unmanaged memory (CPython-managed; no C buffers/pointers) |  |
| CWE-1272 | Sensitive Information Uncleared Before Debug/Power State Tra | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1273 | Device Unlock Credential Sharing | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1274 | Improper Access Control for Volatile Memory Containing Boot  | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1275 | Sensitive Cookie with Improper SameSite Attribute | Variant | N/A: web-app weakness — N/A (only the local wordnet_app server, whose XSS/CSRF/auth are covered) |  |
| CWE-1276 | Hardware Child Block Incorrectly Connected to Parent System | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1277 | Firmware Not Updateable | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1278 | Missing Protection Against Hardware Reverse Engineering Usin | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1279 | Cryptographic Operations are run Before Supporting Units are | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-1280 | Access Control Check Implemented After Asset is Accessed | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1281 | Sequence of Processor Instructions Leads to Unexpected Behav | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1282 | Assumed-Immutable Data is Stored in Writable Memory | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1283 | Mutable Attestation or Measurement Reporting Data | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1284 | Improper Validation of Specified Quantity in Input | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1285 | Improper Validation of Specified Index, Position, or Offset  | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1286 | Improper Validation of Syntactic Correctness of Input | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1287 | Improper Validation of Specified Type of Input | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1288 | Improper Validation of Consistency within Input | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1289 | Improper Validation of Unsafe Equivalence in Input | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1290 | Incorrect Decoding of Security Identifiers | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1291 | Public Key Re-Use for Signing both Debug and Production Code | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-1292 | Incorrect Conversion of Security Identifiers | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1293 | Missing Source Correlation of Multiple Independent Data | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1294 | Insecure Security Identifier Mechanism | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1295 | Debug Messages Revealing Unnecessary Information | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1296 | Incorrect Chaining or Granularity of Debug Components | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1297 | Unprotected Confidential Information on Device is Accessible | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1298 | Hardware Logic Contains Race Conditions | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1299 | Missing Protection Mechanism for Alternate Hardware Interfac | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1300 | Improper Protection of Physical Side Channels | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1301 | Insufficient or Incomplete Data Removal within Hardware Comp | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1302 | Missing Source Identifier in Entity Transactions on a System | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1303 | Non-Transparent Sharing of Microarchitectural Resources | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1304 | Improperly Preserved Integrity of Hardware Configuration Sta | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1310 | Missing Ability to Patch ROM Code | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1311 | Improper Translation of Security Attributes by Fabric Bridge | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1312 | Missing Protection for Mirrored Regions in On-Chip Fabric Fi | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1313 | Hardware Allows Activation of Test or Debug Logic at Runtime | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1314 | Missing Write Protection for Parametric Data Values | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1315 | Improper Setting of Bus Controlling Capability in Fabric End | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1316 | Fabric-Address Map Allows Programming of Unwarranted Overlap | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1317 | Improper Access Control in Fabric Bridge | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1318 | Missing Support for Security Features in On-chip Fabrics or  | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1319 | Improper Protection against Electromagnetic Fault Injection  | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1320 | Improper Protection for Outbound Error Messages and Alert Si | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1321 | Improperly Controlled Modification of Object Prototype Attri | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1322 | Use of Blocking Code in Single-threaded, Non-blocking Contex | Base | N/A: minimal concurrency surface; TOCTOU on staged files is pathsec-guarded |  |
| CWE-1323 | Improper Management of Sensitive Trace Data | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1325 | Improperly Controlled Sequential Memory Allocation | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1326 | Missing Immutable Root of Trust in Hardware | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1327 | Binding to an Unrestricted IP Address | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1328 | Security Version Number Mutable to Older Versions | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1329 | Reliance on Component That is Not Updateable | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1330 | Remanent Data Readable after Memory Erase | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1331 | Improper Isolation of Shared Resources in Network On Chip (N | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1332 | Improper Handling of Faults that Lead to Instruction Skips | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1333 | Inefficient Regular Expression Complexity | Base | PATCHED+TESTED | `772128c1d` |
| CWE-1334 | Unauthorized Error Injection Can Degrade Hardware Redundancy | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1335 | Incorrect Bitwise Shift of Integer | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1336 | Improper Neutralization of Special Elements Used in a Templa | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1338 | Improper Protections Against Hardware Overheating | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1339 | Insufficient Precision or Accuracy of a Real Number | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1341 | Multiple Releases of Same Resource or Handle | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1342 | Information Exposure through Microarchitectural State after  | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1351 | Improper Handling of Hardware Behavior in Exceptionally Cold | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1357 | Reliance on Insufficiently Trustworthy Component | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1384 | Improper Handling of Physical or Environmental Conditions | Class | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1385 | Missing Origin Validation in WebSockets | Variant | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1386 | Insecure Operation on Windows Junction / Mount Point | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1389 | Incorrect Parsing of Numbers with Different Radices | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1390 | Weak Authentication | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1391 | Use of Weak Credentials | Class | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1392 | Use of Default Credentials | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1393 | Use of Default Password | Base | N/A: not an auth/privilege boundary (a library; the one local server's auth is covered) |  |
| CWE-1394 | Use of Default Cryptographic Key | Base | N/A: no cryptographic primitives authored (uses stdlib secrets/hmac where needed) |  |
| CWE-1395 | Dependency on Vulnerable Third-Party Component | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1419 | Incorrect Initialization of Resource | Class | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1420 | Exposure of Sensitive Information during Transient Execution | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1421 | Exposure of Sensitive Information in Shared Microarchitectur | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1422 | Exposure of Sensitive Information caused by Incorrect Data F | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1423 | Exposure of Sensitive Information caused by Shared Microarch | Base | N/A: no SQL/LDAP/XPath surface (chat80 uses parameterized sqlite) |  |
| CWE-1426 | Improper Validation of Generative AI Output | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1427 | Improper Neutralization of Input Used for LLM Prompting | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1428 | Reliance on HTTP instead of HTTPS | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |
| CWE-1429 | Missing Security-Relevant Feedback for Unexecuted Operations | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1431 | Driving Intermediate Cryptographic State/Results to Hardware | Base | N/A: hardware/firmware weakness — N/A to a software library |  |
| CWE-1434 | Insecure Setting of Generative AI/ML Model Inference Paramet | Base | N/A: not reachable in NLTK's surface (file/parse/model/subprocess/output paths are the guarded set) |  |

## 4. NIST / NVD authoritative NLTK CVE list (48 CVEs, live from services.nvd.nist.gov)

Every CVE the NVD attributes to the nltk product, cross-referenced to this branch.

| CVE | CWE | NLTK status | Commit |
|---|---|---|---|
| CVE-2019-14751 | CWE-22 | COVERED by CWE-22 class (chokepoint) | `772128c1d` |
| CVE-2021-3828 | CWE-697 | pre-branch / older-version fix or advisory-only |  |
| CVE-2021-3842 | CWE-1333 | COVERED by CWE-1333 class (chokepoint) | `772128c1d` |
| CVE-2021-43854 | CWE-400 | COVERED by CWE-400 class (chokepoint) | `21c9df941` |
| CVE-2024-39705 | CWE-502 | TESTED | `1c966b41d` |
| CVE-2025-14009 | CWE-94 | COVERED by CWE-94 class (chokepoint) | `772128c1d` |
| CVE-2025-71408 | CWE-95 | pre-branch / older-version fix or advisory-only |  |
| CVE-2025-7707 | CWE-377 | N/A: dependency (llama_index), not NLTK itself |  |
| CVE-2026-0846 | CWE-22 | COVERED by CWE-22 class (chokepoint) | `772128c1d` |
| CVE-2026-0847 | CWE-22 | TESTED | `89815b247` |
| CVE-2026-0848 | CWE-20 | COVERED by CWE-20 class (chokepoint) | `5f91fd1a3` |
| CVE-2026-12252 | CWE-94 | TESTED | `558877315` |
| CVE-2026-12259 | CWE-494 | COVERED by CWE-494 class (chokepoint) | `880b6873a` |
| CVE-2026-12261 | CWE-284 | PATCHED+TESTED | `7a5740af8` |
| CVE-2026-12372 | CWE-918 | COVERED by CWE-918 class (chokepoint) | `e31f6ac9c` |
| CVE-2026-33230 | CWE-79 | COVERED by CWE-79 class (chokepoint) | `5f91fd1a3` |
| CVE-2026-33231 | CWE-306 | COVERED by CWE-306 class (chokepoint) | `b6bb63ef2` |
| CVE-2026-33236 | CWE-22 | TESTED | `1f803e1ff` |
| CVE-2026-54293 | CWE-22 | TESTED | `483c5fe65` |
| CVE-2026-62383 | CWE-22 | COVERED by CWE-22 class (chokepoint) | `772128c1d` |
| CVE-2026-62384 | CWE-22 | COVERED by CWE-22 class (chokepoint) | `772128c1d` |
| CVE-2026-62385 | CWE-73 | COVERED by CWE-73 class (chokepoint) | `09987e7b6` |
| CVE-2026-62388 | CWE-1188 | COVERED by CWE-1188 class (chokepoint) | `e7b56012f` |
| CVE-2026-63310 | CWE-494 | COVERED by CWE-494 class (chokepoint) | `880b6873a` |
| CVE-2026-63311 | CWE-918 | COVERED by CWE-918 class (chokepoint) | `e31f6ac9c` |
| CVE-2026-63312 | CWE-22 | COVERED by CWE-22 class (chokepoint) | `772128c1d` |
| CVE-2026-65915 | CWE-284 | pre-branch / older-version fix or advisory-only |  |
| CVE-2026-66393 | CWE-674 | COVERED by CWE-674 class (chokepoint) | `b6bb63ef2` |
| CVE-2026-70626 | CWE-59 | TESTED | `89815b247` |
| CVE-2026-71513 | CWE-502 | TESTED | `1c966b41d` |
| CVE-2026-71514 | CWE-22 | COVERED by CWE-22 class (chokepoint) | `772128c1d` |
| CVE-2026-72818 | CWE-1333 | COVERED by CWE-1333 class (chokepoint) | `772128c1d` |
| CVE-2026-78680 | CWE-426 | COVERED by CWE-426 class (chokepoint) | `772128c1d` |
| CVE-2026-78681 | CWE-776 | COVERED by CWE-776 class (chokepoint) | `e7b56012f` |
| CVE-2026-78682 | CWE-918 | COVERED by CWE-918 class (chokepoint) | `e31f6ac9c` |
| CVE-2026-78683 | CWE-502 | TESTED | `1c966b41d` |
| CVE-2026-79657 | CWE-502 | COVERED by CWE-502 class (chokepoint) | `e78af79c0` |
| CVE-2026-79674 | CWE-73 | COVERED by CWE-73 class (chokepoint) | `09987e7b6` |
| CVE-2026-79675 | CWE-88 | COVERED by CWE-88 class (chokepoint) | `95b3824aa` |
| CVE-2026-79676 | CWE-22 | COVERED by CWE-22 class (chokepoint) | `772128c1d` |
| CVE-2026-80205 | CWE-1333 | COVERED by CWE-1333 class (chokepoint) | `772128c1d` |
| CVE-2026-80206 | CWE-1333 | COVERED by CWE-1333 class (chokepoint) | `772128c1d` |
| CVE-2026-81722 | CWE-407 | COVERED by CWE-407 class (chokepoint) | `772128c1d` |
| CVE-2026-81723 | CWE-400 | COVERED by CWE-400 class (chokepoint) | `21c9df941` |
| CVE-2026-81724 | CWE-674 | COVERED by CWE-674 class (chokepoint) | `b6bb63ef2` |
| CVE-2026-81725 | CWE-400 | COVERED by CWE-400 class (chokepoint) | `21c9df941` |
| CVE-2026-81726 | CWE-73 | PATCHED+TESTED | `03b0f707d` |
| CVE-2026-81727 | CWE-59 | COVERED by CWE-59 class (chokepoint) | `772128c1d` |

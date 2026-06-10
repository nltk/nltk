# Security Policy

The NLTK project is committed to ensuring the security and integrity of its codebase. 

## Reporting Security Issues

To report a security issue, please follow these steps:

1. Check if the issue has already been reported by searching through existing issues.
2. If the issue has not been reported, create a new issue with a clear description of the problem, including any relevant code snippets or examples.
3. If you have already reported the issue through Huntr, please provide the Huntr report link in the issue description.

## Validating Security Reports

Maintainers with Huntr access will validate security reports before the deadline set by Huntr. If validation through Huntr is not possible, maintainers may publish a GitHub Security Advisory (GHSA) per issue and request a CVE through GitHub directly.

## Recent Security Fixes

The following security issues have been fixed:

* URL-encoded path traversal in `nltk:` resource URLs ([Huntr report](https://huntr.com/bounties/fae662d6-74c2-44fa-95f3-f53d4e8a8355), [PR #3575](https://github.com/nltk/nltk/pull/3575))
* Path traversal in `NKJPCorpusReader` ([Huntr report](https://huntr.com/bounties/ed573d73-3090-487b-853e-da4f155462f2), [PR #3579](https://github.com/nltk/nltk/pull/3579))
* Path traversal in `FramenetCorpusReader.frame()` ([Huntr report](https://huntr.com/bounties/df07d5fe-2667-4599-bcad-276ae5fc143d), [PR #3581](https://github.com/nltk/nltk/pull/3581))
* DNS-rebinding SSRF in `pathsec.urlopen` ([Huntr report](https://huntr.com/bounties/1957af8f-4a1e-4c3b-b3f9-9d767f61caaa), [PR #3582](https://github.com/nltk/nltk/pull/3582))
* ReDoS in `ReviewsCorpusReader` FEATURES regex (CWE-1333) ([Huntr report](https://huntr.com/bounties/65cd835b-af3f-4b7b-bbe1-20f6708b4799), [PR #3583](https://github.com/nltk/nltk/pull/3583))
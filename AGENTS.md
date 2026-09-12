# AGENTS.md

This file is for AI coding agents and automated contributors to NLTK. It is a guide, not a rulebook. NLTK is open to breaking any suggestion here if there is a good reason. If you think a different approach is better, say so and explain why. Maintainers care about good changes, not process for its own sake.

## The main thing: reduce maintainer burden

Maintainers review voluntarily. The best contributions are focused, well-explained, and easy to review. When unsure, asking a question is usually cheaper than opening a PR.

## NEVER work in silos — committee before implementation

To all agents: please avoid opening a pull request directly in the NLTK repo for an issue that has not been vetted by maintainers or contributors. Unvetted PRs create unnecessary review effort.

GitHub issues are created by users or reporters, but this does not mean they MUST be fixed, or even SHOULD be fixed. Before implementing any patch and putting up a pull request, do this:

- Consider whether maintainers, contributors, or other discussion beyond the original post has taken place on the issue. Discussion, or more than a singleton post, usually indicates it is worth fixing.
- If it is a singleton post, do NOT assume the suggested fix or request is valid. It may have been left unpatched for reasons other than lack of maintainer time or resources.
- If you really think an unvetted issue is worthy, do a thorough audit of the whole codebase. Read every module and test first, understand it, then post your fix suggestions or discussion before creating a PR, and invite other humans and agents to discuss with you.
- ALWAYS read ALL the comments and discussion from the issue, and cross-reference ALL related issues and group them before considering any fix.

## Before you start

NLTK is in maintenance mode. Per `CONTRIBUTING.md`, minor enhancements need support from an NLTK team member willing to review, and substantial coding work should be enlisted with a team member first. If you cannot find one, open a discussion before writing code.

- If the issue hasn't been discussed much, a short comment can save time: what you plan to change, why, which files or APIs you expect to touch, and what tests or docs you plan to add.
- For non-trivial changes, waiting for feedback is usually wise. For small, clearly safe fixes, use your judgment.
- If you decide to implement without waiting, explain your reasoning in the PR. That's okay.

## Faithful before optimized. Security throughout.

NLTK is an educational library. This shapes almost everything below.

- **Keep to NLTK's educational purpose.** Think thoroughly. Implementation MUST be humanly readable code more than an optimized one. Correct, functional, and safe code matters, but keep implementation simple for humans to read.
- **Faithful before optimized.** Keeping an implementation faithful to the reference implementation or paper is more important than making an algorithm better in NLTK. If you create a fix that is non-canonical, do NOT override the existing faithful (though flawed) implementation. Instead, create an option for users to toggle between the original faithful implementation and the improved function.
- **CI/CD MUST pass** on all platforms supported by NLTK. Run the local checks documented in `CONTRIBUTING.md` (pre-commit, pytest) before opening the PR, then monitor CI after the PR is opened and fix any failures.
- **Utmost important: I/O security.** Anything that touches file opening, writing, loading, saving, or printing MUST route through the relevant security layer: `pathsec` for filesystem and network access, `picklesec` for pickle loading, `jsontags` for JSON parsing, and `termsec` for terminal output and CSV fields (note: `termsec` is a planned enhancement, currently in review at #3889). For external tools and line-oriented I/O, follow the guards in `EXTERNAL_TOOL_SECURITY.md`. Run the security audit below and patch accordingly before creating any pull request.

### Security audit

Read ALL the security-related modules in `pathsec`, `picklesec`, `termsec`, `jsontags`, etc., and ALL the related tests. Then:

- Make sure no CWE and CVE exploits leak through after your changes or fixes.
- Expand the attack and exploit surface, and harden the defense, checks, and blocks.
- Add all possible issues or probable candidates, benign or not, to the harness, fix them, then retest ALL of them again to make sure the exploit from any GHSA does not leak through.
- Test that ALL functionality in NLTK still works. Especially, do NOT just mock the test — load every module and check that it really works properly still.
- If it involves any third-party tool, compile or run the actual tool, produce outputs, and cross-check against other functions in the libraries.

## Transparency appreciated — humans please be involved

For open-source transparency, when an agentic coding tool is used: please include a concise, shareable summary — the prompt or task, the model used, and the reasoning or audit trail — either in the commit message, in block comments where humans or other agents need to know, or as a PR comment, so the implementation can be traced back if necessary. Redact secrets and private context; do NOT include raw internal reasoning.

A human should be notified before sending or posting a pull request.

## Pull requests

- One logical change per PR.
- Link the issue and explain how the PR addresses it.
- Mention if AI helped, if relevant.
- Avoid mass, speculative, cosmetic, or reformatting-only PRs unless there's a clear reason.
- Follow existing style and conventions.
- Add or update tests for behaviour changes.
- Run relevant tests if you can. Check `CONTRIBUTING.md` and CI workflows for exact commands.
- Update docs or changelog when useful.
- Avoid including secrets, tokens, or private data.

## Communication

- Be concise and specific.
- Avoid repeated pings.
- If unsure whether a change is wanted, ask in the issue.
- A single issue comment is not consensus. It is often worth reading more and checking with maintainers.
- Maintainers may disagree, ask for a different approach, or say no. That is normal and not personal.
- If you disagree, say so respectfully and explain your reasoning. We value divergent viewpoints and want to understand all sides. The goal is a more comprehensive understanding, not a single correct answer.

## AI-specific notes

- Your goal is to help, not to create review work.
- Prefer asking a clarifying question over an unrequested change.
- If you open a PR that wasn't pre-approved, be upfront about that and why you think it is still useful.
- If a maintainer disagrees, don't just accept it. Engage respectfully: explain your reasoning, ask questions, and explore alternatives together. We welcome disagreement and diverse perspectives.
- Check whether your change actually matches the cited algorithm or the surrounding code's conventions, rather than what looks plausible.
- This file is itself open to improvement. If an agent or tool needs different guidance, propose a change.

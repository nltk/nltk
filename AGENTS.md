# AGENTS.md

Hello! This file is for AI coding agents and automated contributors to NLTK. It is a guide, not a rulebook. NLTK is open to breaking any suggestion here if there is a good reason. If you think a different approach is better, say so and explain why. Maintainers care about good changes, not process for its own sake.

## The main thing: reduce maintainer burden

Maintainers review voluntarily. The best contributions are focused, well-explained, and easy to review. When unsure, asking a question is usually cheaper than opening a PR.

## Never work in silos — committee before implementation

GitHub issues are created by users or reporters. An open issue is not automatically required, or even recommended, to be fixed.

- Before implementing any patch, check whether maintainers, contributors, or other discussion has taken place beyond the original post.
- If it is a singleton post, do not assume the suggested fix is valid. It may have been left unpatched for reasons other than lack of resources.
- If you believe an unvetted issue is worth fixing, do a thorough audit of the whole codebase. Read every module and test first, understand it, then post your fix suggestions or discussion before creating a PR. Invite other humans and agents to discuss with you.
- ALWAYS read ALL comments and discussion from the issue, and cross-reference ALL related issues before considering any fix.

## Before you start

NLTK is in maintenance mode. Per `CONTRIBUTING.md`, minor enhancements need support from an NLTK team member willing to review, and substantial coding work should be enlisted with a team member first. If you cannot find one, open a discussion before writing code.

- Read the whole issue, including comments and linked discussions. Consensus may be in the comments, not the first post.
- If the issue hasn't been discussed much, a short comment can save time: what you plan to change, why, which files or APIs you expect to touch, and what tests or docs you plan to add.
- For non-trivial changes, waiting for feedback is usually wise. For small, clearly safe fixes, use your judgment.
- If you decide to implement without waiting, explain your reasoning in the PR. That's okay.

## Faithful before optimized. Security throughout.

NLTK is an educational library. This shapes almost everything below.

- **Keep to NLTK's educational purpose.** Implementation must be humanly readable code more than an optimized one. Correct, functional, and safe code matters, but keep implementation simple for humans to read.
- **Faithful before optimized.** Keeping an implementation faithful to the reference implementation or paper is more important than making an algorithm better. If you create a non-canonical fix, do not override the existing faithful (though flawed) implementation. Instead, create an option for users to toggle between the original faithful implementation and the improved function.
- **CI/CD must pass** on all platforms supported by NLTK. Run the local checks documented in `CONTRIBUTING.md` (pre-commit, pytest) before opening the PR, then monitor CI after the PR is opened and fix any failures.
- **I/O security is paramount.** Use the relevant security layer for the boundary you are touching: `pathsec` for filesystem and network access, `picklesec` for pickle loading, `jsontags` for JSON parsing, and `termsec` for terminal output and CSV fields (note: `termsec` is a planned enhancement, currently in review). For external tools and line-oriented I/O, follow the guards in `EXTERNAL_TOOL_SECURITY.md`.

### Security audit

Read the security-related modules and tests relevant to your change.

- Make sure no CWE and CVE exploits leak through after your changes/fixes.
- Expand the attack and exploit surface, harden the defense/checks/blocks.
- Add all possible issues or probable candidates, benign or not, to the harness, fix them, then retest all of them again to make sure exploits from any GHSA do not leak through.
- Test that ALL functionality in NLTK still works. Do not just mock the test. Load every module and check that it really works properly still.
- If it involves any third-party tool, compile or run the actual tool, produce outputs, and cross-check against other functions in the libraries.

## Transparency appreciated — humans please be involved

For open-source transparency, when an agentic coding tool is used:

- Include a concise, shareable summary in a commit message or PR comment: the task, the model or tool used, and a short rationale or verification summary. Do not include raw internal reasoning, prompts containing secrets, or private context — redact as needed.
- A human should be notified before sending or posting a pull request.

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

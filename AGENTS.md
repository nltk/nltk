# AGENTS.md

Hello! This file is for AI coding agents and automated contributors to NLTK. It is a guide, not a rulebook. NLTK is open to breaking any suggestion here if there is a good reason. If you think a different approach is better, say so and explain why. Maintainers care about good changes, not process for its own sake.

## The main thing: reduce maintainer burden

Maintainers review voluntarily. The best contributions are focused, well-explained, and easy to review. When unsure, asking a question is usually cheaper than opening a PR.

## Before you start

- Read the whole issue, including comments and linked discussions. Consensus may be in the comments, not the first post.
- If the issue hasn't been discussed much, a short comment can save time: what you plan to change, why, which files or APIs you expect to touch, and what tests or docs you plan to add.
- For non-trivial changes, waiting for feedback is usually wise. For small, clearly safe fixes, use your judgment.
- If you decide to implement without waiting, explain your reasoning in the PR. That's okay.

## Pull requests

- One logical change per PR.
- Link the issue and explain how the PR addresses it.
- Mention if AI helped, if relevant.
- Avoid mass, speculative, cosmetic, or reformatting-only PRs unless there's a clear reason.
- Follow existing style and conventions.
- Add or update tests for behavior changes.
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
- This file is itself open to improvement. If an agent or tool needs different guidance, propose a change.

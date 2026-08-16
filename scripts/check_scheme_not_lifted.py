"""Did this marking scheme get written against the candidate's answer?

There is no way to prove a scheme was authored blind. There IS a way to detect
the most common symptom of it not having been: an `acceptable_variant` that is
a verbatim phrase out of the answer script.

The failure this exists to catch is real and is in this repository.
`schemes/dl-2026-s1.json` carries:

    "encode and restructure the given data"     <- the candidate's own words
    "details are more preserved"                <- the candidate's own words

Those are not anticipated phrasings. They are transcriptions. A scheme built
that way scores well on the script it was built from and tells you nothing
about any other script, which is how the same file ended up crediting CNN,
LSTM and the forget gate for a question that asks about attention mechanisms.

WHAT THIS PROVES, AND WHAT IT DOES NOT
--------------------------------------
Zero lifts is WEAK evidence. An author who paraphrases while looking at the
answer defeats it completely, and so does one who simply happens to guess the
candidate's wording.

One or more lifts is evidence against, but READ THE LIFTS, do not read the
count. Measured on first use, 2026-08-16:

    dsa-2026-cse201.json  8 lifts
    dl-2026-s1.json       3 lifts

and the scheme with FEWER lifts is the one known to be contaminated. The
counts are backwards because the check cannot tell these two things apart:

    "details are more preserved"          idiosyncratic. No textbook says
                                          this. Could only have come from
                                          the script. A real tell.

    "push and pop" / "last in first out"  canonical. Every author of a stack
                                          question writes these, blind or
                                          not. Collision proves nothing.

Definition questions are almost all canonical phrasing, so this check is at
its weakest exactly where Section A lives. Distinguishing the two categories
needs a reference corpus of standard phrasings, which does not exist here.

So: the check can fail informatively only when a human reads the failures and
judges whether the phrase is one an independent author would have produced.
It cannot pass informatively at all. It is a smoke detector, not a verdict.

    python scripts/check_scheme_not_lifted.py schemes/X.json tmp/Y.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# A phrase this short can collide by chance ("faster search") without telling
# you anything about how it was authored.
MIN_CONTENT_WORDS = 3


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def content_words(text: str) -> int:
    return len([w for w in normalise(text).split() if len(w) > 1])


def strings_in_scheme(scheme: dict):
    """Every matchable string, with the value point it belongs to."""
    for q in scheme["questions"]:
        for vp in q["value_points"]:
            yield q["question_number"], vp["id"], "text", vp["text"]
            for variant in vp.get("acceptable_variants", []):
                yield q["question_number"], vp["id"], "variant", variant


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2

    scheme = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    transcription = json.loads(Path(argv[2]).read_text(encoding="utf-8"))

    answer = normalise(" ".join(l["text"] for l in transcription["lines"]))

    checked = 0
    skipped = 0
    lifts = []

    for q_num, vp_id, kind, string in strings_in_scheme(scheme):
        if content_words(string) < MIN_CONTENT_WORDS:
            skipped += 1
            continue
        checked += 1
        if normalise(string) in answer:
            lifts.append((q_num, vp_id, kind, string))

    print(f"scheme       : {argv[1]}")
    print(f"answer text  : {argv[2]}  ({len(answer):,} normalised chars)")
    print(f"strings checked: {checked}   (skipped {skipped} shorter than "
          f"{MIN_CONTENT_WORDS} content words, too short to be evidence)")
    print()

    if lifts:
        print(f"VERBATIM LIFTS FOUND: {len(lifts)}")
        for q_num, vp_id, kind, string in lifts:
            print(f"  Q{q_num} {vp_id} ({kind}): {string!r}")
        print()
        print("Each of these appears word-for-word in the candidate's answer.")
        print("That is the signature of a scheme authored against the script it")
        print("is being used to mark. Strong evidence AGAINST blind authoring.")
        return 1

    print("No verbatim lifts.")
    print()
    print("This is WEAK positive evidence only. It rules out the crude form of")
    print("answer-shaped authoring. It cannot rule out paraphrase-while-looking,")
    print("and it is not a substitute for authoring the scheme before the script")
    print("exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

import json, re, sys

doc = json.load(open('/root/marketplace/research/candidate-vocabulary.json'))
v = doc['vocabulary']
assert v['provenance'] == 'candidate-unreviewed', "provenance must stay candidate-unreviewed until Harry approves"
stages = v['stages']
sight = v['sight_words']
order = ["short-a-cvc", "short-a-plus-short-i-cvc", "short-a-i-o-cvc",
         "mixed-short-vowel-cvc", "mixed-cvc-plus-common-digraphs"]
assert list(stages.keys()) == order, f"stage order/keys mismatch: {list(stages.keys())}"
ok = True

def check(name, words):
    global ok
    for w in words:
        if not re.fullmatch(r"[a-z]+", w):
            print(f"FAIL {name}: bad token {w!r}"); ok = False
    dups = [w for w, c in __import__('collections').Counter(words).items() if c > 1]
    if dups:
        print(f"FAIL {name}: duplicates {dups}"); ok = False
    return len(words)

counts = {}
for i, s in enumerate(order):
    counts[s] = check(s, stages[s])
    if i > 0:
        missing = set(stages[order[i-1]]) - set(stages[s])
        if missing:
            print(f"FAIL {s}: not cumulative, missing from stage {i-1}: {sorted(missing)}"); ok = False
print("stage counts:", counts)
check("sight_words", sight)
print("sight count:", len(sight))
overlap = set(sight) & set(stages["mixed-cvc-plus-common-digraphs"])
print("sight/stage5 overlap (allowed):", len(overlap))

# vowel sanity per stage: every token must contain exactly one vowel from aeiou
for s in order:
    for w in stages[s]:
        vowels = [c for c in w if c in "aeiou"]
        if len(vowels) != 1:
            print(f"FAIL {s}: {w!r} has {len(vowels)} vowels"); ok = False
print("single-vowel check: PASS")
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)

# Feature Engineering & Requirements

The fastest reliable way to go from an idea to a feature list you can build and test.

## 1. Principles that matter most
1. **Problem before solution.** Write down the pain or job first. A feature is only a guess until it is tied to one.
2. **Past behaviour beats opinions.** Ask what users *did* last time, never "would you use X?" (Mom Test).
3. **Examples beat abstract rules.** Every rule needs at least one concrete example, and examples become tests.
4. **Fix the time, flex the scope.** Set an appetite (1 or 2 weeks), then cut scope to fit it (Shape Up).
5. **Slice by journey, not by component.** The first release is the thinnest end-to-end path a user can finish (walking skeleton).
6. **Write down what you won't build.** Otherwise small "while we're at it" extras keep sneaking in and the work keeps growing.
7. **Questions are output too. Don't guess. Write down what you don't know.** Turn each unknown into a question and name who will answer it.
8. **Just enough, just in time.** Only write full details for what you'll build next. Keep the rest to one line each, because plans change once real users try the product.

## 2. The fast pipeline (≈1–3 days for a small product)
| Step | Do | Output | Time-box |
|---|---|---|---|
| 1. Frame | Goal and success metric, personas, top problems, non-goals | `product.md` | 2 h |
| 2. Discover | 5–8 short interviews or prototype walkthroughs | Notes, job stories | 1 day |
| 3. Map | Story map: user activities left→right, tasks stacked under each | Journey map | 1–2 h |
| 4. Slice | Draw release lines; the top slice is the walking skeleton | Release 1 scope | 30 min |
| 5. Prioritise | MoSCoW for the release cut; RICE/ICE only for a big backlog | Priority per feature | 30 min |
| 6. List | One row per feature: ID, journey, priority, dependencies, status | `features.md` | 1–2 h |
| 7. Specify | Per feature: Example Mapping, then acceptance criteria | `spec.md` | ≤30 min each |

## 3. Technique cheat sheet (pick the lightest one that answers the question)
| Need | Technique | Why it's fast |
|---|---|---|
| Why build it at all? | Impact Mapping: Goal → Actors → Impacts → Deliverables | Drops features that have no goal |
| Which problems exist? | Opportunity Solution Tree (Torres) | Keeps problems apart from feature requests |
| What do users really do? | Mom Test interviews | Avoids false "validation" |
| Complex flow or domain | Event Storming: "something happened" events on a timeline | Surfaces conflicts and hidden steps in hours |
| Which features, in what order? | User Story Mapping (Patton) | Shows gaps and gives release slices |
| Align a team on an MVP | Lean Inception (Caroli): 1 week, ends in an MVP canvas | Replaces 2–4 week inceptions |
| Is this story ready to build? | Example Mapping (Wynne): story, rules, examples, questions | 25–30 min per story |
| UI or flow unclear | Clickable prototype | People react to screens better than to prose |

## 4. Gathering: interview rules (Mom Test)
- Talk about their life, not your idea. Don't pitch until the end.
- Ask about specific past events: "Tell me about the last time you…", "What did you do then?", "What did it cost you?"
- Ignore compliments and "I would…" answers. Trust commitments: time, money, intros, a pilot.
- Listen more than you talk. Capture exact quotes. Stop when the answers start repeating.

## 5. Analysis: shaping features
- **Job stories for discovery:** "When [situation], I want to [motivation], so I can [outcome]."
- **User stories for building:** "As a [persona], I want [action], so that [benefit]." Check INVEST: Independent, Negotiable, Valuable, Estimable, Small, Testable.
- **Split big stories with SPIDR:** Spike, Paths, Interfaces, Data, Rules. Example: card payments first, PayPal later; valid data first, edge cases later.
- **Prioritise.** Use Kano first if you're unsure what users expect vs what would delight them. Then:
  - **MoSCoW** (decide what's in this release): **Must** = release fails without it. **Should** = important, but users can work around it. **Could** = nice to have, dropped first. **Won't** = not this time. Keep Musts at or under ~60% of effort.
  - **RICE** (rank a big backlog): Reach (users/month) × Impact (0.25–3) × Confidence (50–100%) ÷ Effort (person-weeks). Highest score goes first. **ICE** is the quick version when you have no usage data: Impact × Confidence × Ease, each scored 1–10.
- **Dependencies:** record them in the feature list. Build the features with no open dependency first.

## 6. Writing requirements that tests and AI agents can use
- **EARS** for acceptance criteria:
  - Always: `The system shall <response>`
  - Event: `When <trigger>, the system shall <response>`
  - State: `While <state>, the system shall <response>`
  - Unwanted: `If <condition>, then the system shall <response>`
  - Optional: `Where <feature is included>, the system shall <response>`
- **Given / When / Then** for each example from Example Mapping. Each one becomes an automated test.
- One behaviour per criterion. Ban "and/or", "etc.", "fast", "user-friendly", "should handle". Use numbers.
- **NFR quick pass (ISO/IEC 25010):** pick only what matters for v1: security (auth, data access), reliability (uptime, backups), performance (e.g. p95 < 300 ms), usability. Each gets a number and a way to measure it.

## 7. Using AI to go faster (safely)
- Let an LLM **interview you**: one question at a time, challenge every assumption, end with a list of open questions.
- Use AI to draft stories, edge cases, EARS criteria and NFR lists. A human approves every requirement.
- 2025 studies: LLM-drafted requirements were rated as aligned and complete as experts' at a fraction of the time, and LLM interviewers matched human error rates. They **still missed requirements and sometimes contradicted themselves**, and the interview studies used simulated stakeholders. Use AI for breadth; use people for truth.
- Spec-driven tools (GitHub Spec Kit, Kiro) follow the same chain: requirements → design → tasks. Spec quality caps agent output quality.

## 8. Definition of Ready (per feature, before plan and tasks)
- [ ] Linked to a journey and a goal in `product.md`
- [ ] Priority and dependencies set in `features.md`
- [ ] Every rule has at least one concrete example; every criterion is testable
- [ ] Open questions answered, or parked with an owner
- [ ] Out-of-scope and no-gos written down
- [ ] Prototype screens referenced wherever there is UI
- [ ] Fits the appetite; if not, split it (SPIDR)

## 9. Anti-patterns that waste the most time
- Asking "would you use this?" and trusting the answer.
- Specifying the whole product upfront in full detail. Most of it will change.
- Rules without examples, which turn into abstract, untestable criteria.
- Slicing by layer (DB, API, UI) instead of by user-visible journey.
- Marking everything "Must", which makes MoSCoW meaningless.
- Leaving NFRs until launch, when security, data and performance surprise you late.
- Copying prototype code instead of extracting its decisions.
- Treating "a late fix costs 100× more" as law. Catching ambiguity early is still cheap, but the evidence for the multiplier is mixed (Menzies et al., 2017), so don't over-specify to avoid a myth.

## Sources
- Patton, *User Story Mapping* (2014); jpattonassociates.com
- Fitzpatrick, *The Mom Test*; Klement, Job Stories (Intercom, 2013)
- Wynne, "Introducing Example Mapping": cucumber.io/blog/bdd/example-mapping-introduction
- Singer, *Shape Up*: basecamp.com/shapeup
- Adzic, *Impact Mapping*; Torres, *Continuous Discovery Habits*; Brandolini, *Introducing EventStorming*
- Caroli, *Lean Inception*: martinfowler.com/articles/lean-inception
- Cohn, SPIDR: mountaingoatsoftware.com; DSDM MoSCoW guidance
- Mavin et al., EARS; ISO/IEC 25010:2023
- LLM elicitation: arxiv.org/abs/2507.02564 (LLMREI), arxiv.org/abs/2501.19297, arxiv.org/abs/2503.07800
- Menzies et al., "Are delayed issues harder to resolve?", Empirical Software Engineering (2017)

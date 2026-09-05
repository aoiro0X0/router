# ComfyUI Peace Elite Prototype Router

A deterministic routing package for ByteArtist's internal online ComfyUI
workflows. It evaluates the client category code and the original user input
before Ark Search. The specialized prototype path is enabled only when the
category code is `"3"` and at least one approved trigger term is present.

This repository is the complete public routing-node bundle used by the
current Game UGC workflows. One installation registers all of the following
deterministic capabilities:

- schema-v3 Planner validation, source-faithful gift naming, value/brand
  protection, and the lazy-search Boolean decision;
- deterministic TEXT image-prompt normalization that prepends the protected
  Planner `display_text` without requiring the LLM to copy a fixed template;
- schema-v2 generic subject-route protection for compatible workflows;
- Peace Elite prototype matching plus final policy arbitration;
- active prototype PE assembly and ordered reference-image selection.

The Web Search plugin and the Planner/Image/Motion LLM nodes remain separate
runtime dependencies. They are model/tool execution nodes rather than
deterministic routing nodes.

## Nodes

### Policy Router variants

`PeaceElitePrototypePolicyRouterCompact` and
`PeaceElitePrototypePolicyRouter` add a third `llm_decision` input while still
reading the original category and user text. The full-output policy router,
used by the current 1- and 99-diamond workflows, restores literal hard
recognition: category `"3"` plus any exact six-prototype allowlist hit enables
the prototype route even when the LLM says `0`. Deterministic high-value,
brand-asset, person, other-creature, vehicle, scene, building, and facility
guards still close the route. The compact policy router retains its older
semantic-suggestion behavior for compatibility but is not used by the current
1- or 99-diamond candidates.

### Game UGC Route Policy Guard

`GameUGCRoutePolicyGuard` validates the schema-v2 subject route after the
generic route LLM. It receives both the LLM output and original user text,
normalizes traditional characters, whitespace and the diamond emoji for
policy matching, and hard-locks high-value or brand-asset requests to TEXT.
It outputs the validated marker-plus-JSON string for module selection and the
same route as plain JSON for `production_brief` parsing. Invalid JSON and
unrelated generic fallbacks are replaced with a safe text route derived from
the user's own wording rather than a fixed phrase.

### Game UGC Planner Policy Guard

`GameUGCPlannerPolicyGuard` validates the schema-v3 `ProductionSpec` used by
the conditional-search workflow. `price_diamonds` selects the `WITHIN_1 /
OVER_1` or `WITHIN_99 / OVER_99` audit vocabulary. When the optional raw
`category_code` input is connected, category `"3"` plus a safe literal
prototype hit deterministically rewrites an LLM false TEXT or over-budget
result to an OBJECT prototype spec and disables search. The same node is used
before and after the lazy Web Search switch, so the hard decision reaches both
the search control and the downstream image/motion context.

The guard enforces representative resolution as a general stage order rather
than maintaining a term-to-object patch list. A `PRE_SEARCH` guard turns a
failed single biological or `IDENTITY_SUBJECT` representative attempt into a
lazy search request. Node-only fix **v3.35.16** repairs absent/null/empty
bookkeeping fields from explicit subject decisions before validation. An
equipment OBJECT or an explicitly selected REPRESENTATIVE is preserved when
schema, prototype, budget, or representative audit metadata is missing. The
guard never invents a carrier or picks arbitrarily among unresolved candidates.
If either Planner returns unrecoverable or internally inconsistent output,
the guard produces a deterministic runnable spec instead of raising an
exception. Recovery preserves identified policy constraints; an incomplete
single identity/biological audit still requests search at `PRE_SEARCH`.
At `FINAL`, unresolved results remain TEXT without starting another search.
An unparseable response or a response that never identified the subject as an
identity cannot be reliably classified by this repair. Safe literal
prototype hits still become OBJECT specs; other unrecoverable results preserve
the original input as TEXT. Brand assets remain prohibited, and composite
relations stay under semantic planning.

This update retains existing node ports and schema-v3 output fields. Existing
1- and 99-diamond workflow JSON files need no edits; update this node package
and restart/reload the BA runtime. It does not change the legacy 299-diamond
router. Local tests do not establish the cause of any previous BA output or
replace an end-to-end rerun.

Outputs:

- `validated_output`: the marker-plus-JSON `ProductionSpec` for downstream
  module selection.
- `spec_json`: the same protected spec as plain JSON.
- `need_search`: the Boolean control for a lazy Web Search switch.
- `prototype_decision`: the protected `3` or `0` decision; with raw category
  connected, a safe literal hit is already hard-corrected to `3`.

### Game UGC TEXT Image Prompt Guard

`GameUGCImagePromptTextGuard` sits between the extracted Image Director prompt
and the image generator. For `render_mode=TEXT`, it prepends the fixed main
image prefix and the exact protected Planner `display_text` automatically.
The Image Director does not need to copy a fixed sentence or calculate a
character count, and natural layout wording such as “the first two
characters” is accepted. A matching legacy lock at the beginning is removed
before the new instruction is prepended, preventing duplicate migration
text. Empty prompts, invalid Planner specs, and empty `display_text` values are
recovered into a minimal runnable prompt, using the optional original user input
as the final literal fallback. Non-empty non-TEXT prompts pass through
unchanged. The same normalized prompt should also feed the Motion Director
context so still-image generation and animation planning share one source.

### Peace Elite Prototype Router (Compact)

Inputs:

- `category_code`: the client category code. Peace Elite must send the string
  `"3"`.
- `user_input`: the unmodified user input. The client must not preprocess or
  rewrite it.

Outputs:

- `route_state`: internal routing state consumed by the other two nodes in
  this package.
- `prototype_enabled`: `true` when at least one prototype is matched. It can
  directly drive a Boolean switch between the generic and specialized paths.
- `user_input_json`: a minimal JSON object containing only the original user
  input, ready for the specialized production LLM.

The compact node deliberately exposes only these three runtime outputs. The
ordered match set, canonical names, and per-prototype flags already exist in
`route_state`, so duplicating them as visible sockets adds wiring clutter
without changing execution.

The original `PeaceElitePrototypeRouter` class remains registered as
`和平精英原型路由（兼容旧版）`. It preserves the former output indices for
workflows saved before the compact node was introduced. New workflows should
use `PeaceElitePrototypeRouterCompact`, displayed as
`和平精英原型路由（精简）`.

The prototype IDs and exact substring allowlist are fixed:

| ID | Prototype | Trigger terms |
|---:|---|---|
| 1 | Frying pan | `平底锅` |
| 2 | Screaming chicken | `尖叫鸡`, `鸡否` |
| 3 | Airdrop crate | `空投箱`, `空投` |
| 4 | Level 3 armor | `三级防弹衣`, `三级甲` |
| 5 | Level 3 backpack | `三级背包`, `三级包` |
| 6 | Level 3 helmet | `三级头盔`, `三级头` |

Matching is deterministic. The node does not tokenize, interpret negation,
correct typos, or perform fuzzy semantic matching. For example, `不要鸡否`
still matches the screaming chicken, while ambiguous short forms such as
`三甲`, `三包`, `三头`, and `锅` do not match.

### Peace Elite Prototype PE Assembler

This node receives one shared PE and six optional prototype modules. It
includes only the modules matched by the current request. References are
always ordered by prototype ID from `1` to `6`, and the assembler injects the
corresponding `Image 1`, `Image 2`, and subsequent bindings into the final PE.

When multiple prototypes are listed without an explicit relationship, the
shared composition rules instruct the production LLM to create the simplest
natural and readable event without inventing additional characters or core
props.

Production PE content is proprietary and is deliberately not distributed in
this GitHub plugin repository. Supply the shared PE and six modules through
ByteArtist-internal STRING nodes. The assembler removes each leading
`PE_VERSION` line before composing the runtime system prompt, so release
metadata is never injected into the production LLM. The externally supplied
shared PE must contain exactly one `<<<ACTIVE_PROTOTYPE_CONTEXT>>>` slot. The
assembler replaces that slot with the ordered reference manifest and active
modules, keeping the final output contract at the end of the system prompt.

### Peace Elite Ordered Reference List

This node receives six independent reference images, selects only the matched
ones, removes each input's singleton batch dimension, and returns one ordered
Python list whose items are individual `H x W x C` image tensors. It never
creates a pixel collage. Every selected input must contain exactly one image,
and all selected images must have identical height, width, and channel count.
Resize or pad inputs individually before this node when necessary. Preserve
each reference's aspect ratio; do not stretch the source or combine multiple
references into one canvas.

`OUTPUT_IS_LIST` deliberately remains false. ComfyUI therefore wraps the
Python list as one payload and calls the downstream generation node once. Do
not change it to an execution list: doing so would make ComfyUI call a normal
downstream node once per reference. This output is a deliberate adapter for a
list-aware image-upload input; do not route it through ordinary ComfyUI IMAGE
processing nodes that expect one standard BHWC tensor.

All six image sockets use ComfyUI lazy evaluation. A disabled route requests
none of the image inputs and returns a real empty image list; an enabled route
requests only the matched references. Therefore this node can connect directly
to the generation node and also owns the generic-path empty-reference result.
Do not keep a separate screaming-chicken image gate or use any prototype asset
as an empty-reference placeholder.

This adapter matches the observed downstream uploader contract: it iterates a
Python sequence and sends each item directly to `PIL.Image.fromarray`, which
requires an individual HWC image instead of a four-dimensional ComfyUI IMAGE
batch. The downstream source is not included in this repository, so still test
with at least two visually distinct references and confirm one generation task
receives every reference in manifest order before deployment.

## Recommended Wiring

```text
category_code + user_input
-> Peace Elite Prototype Router
   |-> prototype_enabled -> generic/specialized Boolean switch
   |-> user_input_json -> specialized production LLM user input
   `-> route_state
       |-> Peace Elite Prototype PE Assembler -> specialized system prompt
       `-> Peace Elite Ordered Reference List -> image generation node
```

When no prototype is matched, `prototype_enabled` is `false`, the PE assembler
returns an empty string, and the reference batch node returns an empty image
list. The workflow should continue through the generic Ark Search path.

## Installation

Clone or copy this entire repository into the ByteArtist ComfyUI custom node
directory. No second routing repository is required:

```text
ComfyUI/custom_nodes/comfyui_peace_elite_prototype_router
```

Restart ComfyUI and search for these nodes:

- `和平精英原型策略路由（精简）`
- `和平精英原型策略路由（兼容输出）`
- `游戏 UGC 路由策略护栏`
- `游戏 UGC Planner 策略护栏`
- `游戏 UGC TEXT 图像提示词护栏`
- `和平精英原型路由（精简）`
- `和平精英原型路由（兼容旧版）`
- `和平精英原型 PE 组装`
- `和平精英有序多参考图列表`

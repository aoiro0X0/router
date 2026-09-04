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
- deterministic TEXT image-prompt validation against the protected Planner
  `display_text` and its whitespace-free visible-character count;
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
reading the original category and user text. They treat the short LLM output
as a semantic suggestion, then deterministically override false negatives for
pure prototype combinations and reject high-value, brand-asset, and known
positive biological/vehicle/scene/facility mixed-subject requests. Negated
extras and explicit comparisons remain eligible for semantic handling.
The compact variant is used by the current 1-diamond workflow; the
output-stable variant is used by the current 99-diamond workflow.

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
the conditional-search workflow. It deterministically enforces the latest
value and brand locks, limits the public gift name to at most six visible
characters selected from ordered source spans in the original input, and
allows search only when a non-empty search query is present. The same node can
be used before and after the lazy Web Search switch: the first instance emits
`need_search`, while the second validates either the Planner result or the
search-enriched replacement without requiring another aggregation LLM.

Outputs:

- `validated_output`: the marker-plus-JSON `ProductionSpec` for downstream
  module selection.
- `spec_json`: the same protected spec as plain JSON.
- `need_search`: the Boolean control for a lazy Web Search switch.
- `prototype_decision`: the Planner's `3` or `0` suggestion for the
  deterministic Peace Elite policy router.

### Game UGC TEXT Image Prompt Guard

`GameUGCImagePromptTextGuard` sits between the extracted Image Director prompt
and the image generator. For `render_mode=TEXT`, it requires the prompt to
start with the fixed main image prefix followed immediately by the exact
Planner `display_text`, its whitespace-free visible-character count, and the
fixed no-rewrite instruction. Missing or rewritten text, a wrong count, or a
second count claim raises an error before image generation. Non-TEXT prompts
pass through unchanged. The same validated prompt should also feed the Motion
Director context so still-image generation and animation planning share one
source.

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

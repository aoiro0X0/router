# ComfyUI Peace Elite Prototype Router

A deterministic routing package for ByteArtist's internal online ComfyUI
workflows. It evaluates the client category code and the original user input
before Ark Search. The specialized prototype path is enabled only when the
category code is `"3"` and at least one approved trigger term is present.

## Nodes

### Peace Elite Prototype Router

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
- Six independent Boolean outputs for resource gating and debugging.
- `matched_names` and `matched_ids_json` for debugging.
- `user_input_json`: a minimal JSON object containing only the original user
  input, ready for the specialized production LLM.

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

### Peace Elite Multi-Reference Batch

This node receives six independent reference images, selects only the matched
ones, and combines them into an ordered ComfyUI IMAGE batch. It never creates
a pixel collage. Every selected input must contain exactly one image, and all
selected images must have identical height, width, and channel count. Resize
or pad inputs individually before this node when necessary. Preserve each
reference's aspect ratio; do not stretch the source or combine multiple
references into one canvas.

All six image sockets use ComfyUI lazy evaluation. A disabled route requests
none of the image inputs and returns a real empty image list; an enabled route
requests only the matched references. Therefore this node can connect directly
to the generation node and also owns the generic-path empty-reference result.
Do not keep a separate screaming-chicken image gate or use any prototype asset
as an empty-reference placeholder.

The downstream `BALLMImg` node must be verified to interpret an IMAGE batch as
multiple ordered references in one Seedream request, rather than using only
the first image or launching one generation per image. The `BALLMImg` source
is not included in this repository, so test this behavior in the ByteArtist
environment with at least two visually distinct references before deployment.

## Recommended Wiring

```text
category_code + user_input
-> Peace Elite Prototype Router
   |-> prototype_enabled -> generic/specialized Boolean switch
   |-> user_input_json -> specialized production LLM user input
   `-> route_state
       |-> Peace Elite Prototype PE Assembler -> specialized system prompt
       `-> Peace Elite Multi-Reference Batch -> image generation node
```

When no prototype is matched, `prototype_enabled` is `false`, the PE assembler
returns an empty string, and the reference batch node returns an empty image
list. The workflow should continue through the generic Ark Search path.

## Installation

Copy this directory to the ByteArtist ComfyUI custom node directory:

```text
ComfyUI/custom_nodes/comfyui_peace_elite_prototype_router
```

Restart ComfyUI and search for these nodes:

- `和平精英原型路由`
- `和平精英原型 PE 组装`
- `和平精英多参考图批次`

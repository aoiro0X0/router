# ComfyUI Peace Elite Prototype Router

A deterministic routing package for ByteArtist's internal online ComfyUI
workflows. It evaluates the client category code and the original user input
before Ark Search. The specialized prototype path is enabled only when the
category code is `"3"` and at least one approved trigger term is present.

## Nodes

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

### Workflow-Embedded Reference Image

This node keeps one static reference image inside the workflow JSON instead of
depending on a room-local ComfyUI input filename. It has three widget inputs:

- `image_name`: a stable label used only in validation errors.
- `expected_sha256`: an optional SHA-256 digest of the original PNG, JPEG, or
  WebP file bytes after Base64 decoding. A mismatch stops execution instead of
  silently loading damaged workflow data.
- `image_base64`: raw Base64 or a PNG, JPEG, or WebP Base64 data URI.

The node performs strict Base64 decoding entirely in memory, verifies the
optional digest, applies EXIF orientation, converts the image to RGB, and
returns one standard ComfyUI `[1, H, W, 3]` float32 `IMAGE` in the `[0, 1]`
range. It does not read a filesystem path, upload a file, or access the
network. Alpha is intentionally discarded, matching the RGB `IMAGE` output of
the classic static `LoadImage` path; this node does not emit a mask.

Only single-frame PNG, JPEG, and WebP files are accepted. One encoded file is
limited to 16 MiB, 16,777,216 decoded pixels, and 8,192 pixels on either edge.
Malformed inputs rejected by the decoder, animated files, oversized files,
unsupported formats, and hash mismatches fail explicitly. Production
workflows should always fill `expected_sha256`; with that digest present, any
byte-level truncation or modification is detected even if Pillow could still
decode the remaining bytes.

For the Peace Elite workflow, prepare every reference with its final Lanczos
resize and centered edge padding before embedding it. The six embedded nodes
can then connect directly to the ordered reference node, with no runtime
resize nodes and no room-local image assets. Lossless WebP keeps those final
pixels compact without changing them.

Base64 is persistence, not encryption. Anyone who can read the workflow JSON
can extract its images. Keep workflows containing proprietary references
private. This public plugin repository contains only the decoder code and
documentation; it must never contain workflow Base64, reference assets, or PE
content.

### Peace Elite Ordered Reference List

This node receives six independent reference images, selects only the matched
ones, removes each input's singleton batch dimension, and returns one ordered
Python list whose items are individual `H x W x C` image tensors. It never
creates a pixel collage. Every selected input must contain exactly one image,
and all selected images must have identical height, width, and channel count.
Resize or pad inputs individually before this node when necessary. Preserve
each reference's aspect ratio; do not stretch the source or combine multiple
references into one canvas. If the workflow embeds already-finalized,
same-sized references, connect them directly and omit the runtime resize
nodes.

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

Workflow-Embedded Reference Image x 6
-> Peace Elite Ordered Reference List
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

- `和平精英原型路由（精简）`
- `和平精英原型路由（兼容旧版）`
- `和平精英原型 PE 组装`
- `工作流内嵌参考图`
- `和平精英有序多参考图列表`

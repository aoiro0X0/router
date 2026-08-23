import base64
import binascii
import hashlib
from io import BytesIO
import json
import re
import warnings


PROTOTYPES = (
    {
        "id": 1,
        "key": "pan",
        "name": "平底锅",
        "terms": ("平底锅",),
        "image_input": "pan_image",
        "module_input": "pan_module",
    },
    {
        "id": 2,
        "key": "screaming_chicken",
        "name": "尖叫鸡",
        "terms": ("尖叫鸡", "鸡否"),
        "image_input": "screaming_chicken_image",
        "module_input": "screaming_chicken_module",
    },
    {
        "id": 3,
        "key": "airdrop_crate",
        "name": "空投箱",
        "terms": ("空投箱", "空投"),
        "image_input": "airdrop_crate_image",
        "module_input": "airdrop_crate_module",
    },
    {
        "id": 4,
        "key": "level3_armor",
        "name": "三级甲",
        "terms": ("三级防弹衣", "三级甲"),
        "image_input": "level3_armor_image",
        "module_input": "level3_armor_module",
    },
    {
        "id": 5,
        "key": "level3_backpack",
        "name": "三级包",
        "terms": ("三级背包", "三级包"),
        "image_input": "level3_backpack_image",
        "module_input": "level3_backpack_module",
    },
    {
        "id": 6,
        "key": "level3_helmet",
        "name": "三级头",
        "terms": ("三级头盔", "三级头"),
        "image_input": "level3_helmet_image",
        "module_input": "level3_helmet_module",
    },
)


PE_VERSION_LINE = re.compile(r"\APE_VERSION: v[0-9]+\.[0-9]+\.[0-9]+\s*(?:\r?\n)+")
ACTIVE_PROTOTYPE_CONTEXT_SLOT = "<<<ACTIVE_PROTOTYPE_CONTEXT>>>"
MAX_EMBEDDED_IMAGE_BYTES = 16 * 1024 * 1024
MAX_EMBEDDED_IMAGE_PIXELS = 16 * 1024 * 1024
MAX_EMBEDDED_IMAGE_DIMENSION = 8192
SHA256_HEX = re.compile(r"\A[0-9a-f]{64}\Z")
IMAGE_DATA_URI = re.compile(
    r"\Adata:image/(?:png|jpe?g|webp);base64,",
    flags=re.IGNORECASE,
)


def _as_text(value):
    if value is None:
        return ""
    return str(value)


def _strip_pe_version(value):
    """Keep source PE files versioned without injecting their metadata into the LLM."""
    return PE_VERSION_LINE.sub("", _as_text(value), count=1).strip()


def build_route_state(category_code, user_input):
    """Build a deterministic, JSON-serializable routing state."""
    category_text = _as_text(category_code).strip()
    original_text = _as_text(user_input)
    category_enabled = category_text == "3"
    matched = []

    if category_enabled:
        for prototype in PROTOTYPES:
            matched_term = next(
                (term for term in prototype["terms"] if term in original_text),
                None,
            )
            if matched_term is not None:
                matched.append(
                    {
                        "id": prototype["id"],
                        "key": prototype["key"],
                        "name": prototype["name"],
                        "matched_term": matched_term,
                        "image_index": len(matched) + 1,
                    }
                )

    return {
        "schema_version": 1,
        "category_code": category_text,
        "category_enabled": category_enabled,
        "enabled": bool(matched),
        "user_input": original_text,
        "matched": matched,
    }


def _router_input_types():
    return {
        "required": {
            "category_code": ("STRING", {"default": "", "forceInput": True}),
            "user_input": (
                "STRING",
                {"default": "", "multiline": True, "forceInput": True},
            ),
        }
    }


def _build_user_input_json(route_state):
    return json.dumps(
        {"用户原词": route_state["user_input"]},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _validate_route_state(route_state):
    if not isinstance(route_state, dict):
        raise TypeError("route_state 必须来自 Peace Elite Prototype Router 节点。")
    if route_state.get("schema_version") != 1:
        raise ValueError("不支持的和平精英原型路由状态版本。")
    return route_state


def decode_embedded_image_bytes(image_base64, expected_sha256="", image_name=""):
    """Decode one workflow-embedded image and optionally verify its source bytes."""
    label = _as_text(image_name).strip() or "内嵌图片"
    encoded = _as_text(image_base64)
    max_encoded_chars = 4 * ((MAX_EMBEDDED_IMAGE_BYTES + 2) // 3)
    max_source_chars = max_encoded_chars + max_encoded_chars // 32 + 256
    if len(encoded) > max_source_chars:
        raise ValueError(
            f"{label}超过 {MAX_EMBEDDED_IMAGE_BYTES // (1024 * 1024)} MiB 的内嵌上限。"
        )
    encoded = encoded.strip()
    if not encoded:
        raise ValueError(f"{label}的 Base64 数据为空。")

    if encoded.lower().startswith("data:"):
        match = IMAGE_DATA_URI.match(encoded)
        if match is None:
            raise ValueError(f"{label}使用了不支持的图片 Data URI。")
        encoded = encoded[match.end() :]

    # Workflow JSON normally stores one uninterrupted string. Ignoring whitespace
    # also keeps manually wrapped Base64 lossless while validate=True still rejects
    # every non-Base64 character.
    encoded = "".join(encoded.split())
    if len(encoded) > max_encoded_chars:
        raise ValueError(
            f"{label}超过 {MAX_EMBEDDED_IMAGE_BYTES // (1024 * 1024)} MiB 的内嵌上限。"
        )

    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{label}的 Base64 数据无效或已被截断。") from exc

    if not raw:
        raise ValueError(f"{label}解码后为空。")
    if len(raw) > MAX_EMBEDDED_IMAGE_BYTES:
        raise ValueError(
            f"{label}超过 {MAX_EMBEDDED_IMAGE_BYTES // (1024 * 1024)} MiB 的内嵌上限。"
        )

    expected = _as_text(expected_sha256).strip().lower()
    if expected:
        if SHA256_HEX.fullmatch(expected) is None:
            raise ValueError(f"{label}的 expected_sha256 必须是 64 位十六进制字符串。")
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError(
                f"{label}的 SHA-256 校验失败；工作流中的图片数据可能已损坏。"
            )

    return raw


def decode_embedded_image_array(image_base64, expected_sha256="", image_name=""):
    """Decode one static image to ComfyUI's classic float32 RGB HWC contract."""
    import numpy as np
    from PIL import Image, ImageOps, UnidentifiedImageError

    label = _as_text(image_name).strip() or "内嵌图片"
    raw = decode_embedded_image_bytes(image_base64, expected_sha256, label)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as opened:
                image_format = (opened.format or "").upper()
                if image_format not in {"PNG", "JPEG", "WEBP"}:
                    raise ValueError(
                        f"{label}必须是 PNG、JPEG 或 WebP 静态图片。"
                    )

                frame_count = int(getattr(opened, "n_frames", 1))
                if frame_count != 1:
                    raise ValueError(
                        f"{label}必须是单帧图片，当前包含 {frame_count} 帧。"
                    )

                width, height = opened.size
                if width <= 0 or height <= 0:
                    raise ValueError(f"{label}的图片尺寸无效。")
                if (
                    width > MAX_EMBEDDED_IMAGE_DIMENSION
                    or height > MAX_EMBEDDED_IMAGE_DIMENSION
                ):
                    raise ValueError(
                        f"{label}任一边不得超过 {MAX_EMBEDDED_IMAGE_DIMENSION} 像素。"
                    )
                if width * height > MAX_EMBEDDED_IMAGE_PIXELS:
                    raise ValueError(
                        f"{label}超过 {MAX_EMBEDDED_IMAGE_PIXELS:,} 像素的解码上限。"
                    )

                opened.load()
                image = ImageOps.exif_transpose(opened)
                if image.mode == "I":
                    image = image.point(lambda value: value * (1 / 255))
                image = image.convert("RGB")
                array = np.array(image).astype(np.float32) / 255.0
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError(f"{label}的图片尺寸触发 Pillow 安全限制。") from exc
    except UnidentifiedImageError as exc:
        raise ValueError(f"{label}不是 Pillow 可识别的图片。") from exc
    except OSError as exc:
        raise ValueError(f"{label}的图片文件不完整或无法解码。") from exc

    return np.ascontiguousarray(array)


def build_reference_manifest(route_state):
    state = _validate_route_state(route_state)
    if not state.get("enabled"):
        return ""

    lines = [
        "工作流按以下顺序传入彼此独立的参考图；图号与原型绑定关系不可交换："
    ]
    for item in state["matched"]:
        lines.append(
            f'图{item["image_index"]}是{item["name"]}的唯一视觉真源，只控制{item["name"]}。'
        )
    return "\n".join(lines)


def assemble_prototype_pe(route_state, common_pe, modules):
    state = _validate_route_state(route_state)
    if not state.get("enabled"):
        return "", ""

    common_text = _strip_pe_version(common_pe)
    if not common_text:
        raise ValueError("命中特调路线时，common_pe 不能为空。")
    if common_text.count(ACTIVE_PROTOTYPE_CONTEXT_SLOT) != 1:
        raise ValueError(
            "common_pe 必须且只能包含一个 <<<ACTIVE_PROTOTYPE_CONTEXT>>> 插槽。"
        )

    manifest = build_reference_manifest(state)
    active_sections = [manifest]

    prototype_by_key = {item["key"]: item for item in PROTOTYPES}
    for match in state["matched"]:
        prototype = prototype_by_key[match["key"]]
        module_text = _strip_pe_version(modules.get(prototype["module_input"]))
        if not module_text:
            raise ValueError(f'{prototype["name"]}已命中，但对应 PE 模块为空。')
        image_index = match["image_index"]
        active_sections.append(
            f'<<<PROTOTYPE_MODULE_BEGIN:{prototype["name"]}:图{image_index}>>>\n'
            f"{module_text}\n"
            f'<<<PROTOTYPE_MODULE_END:{prototype["name"]}:图{image_index}>>>'
        )

    active_context = "\n\n".join(active_sections)
    assembled = common_text.replace(ACTIVE_PROTOTYPE_CONTEXT_SLOT, active_context)
    return assembled, manifest


def _is_empty_image(value):
    return value is None or isinstance(value, (list, tuple)) and len(value) == 0


def collect_reference_batch(route_state, images):
    """Collect ordered HWC tensors as one list payload for the downstream image node."""
    state = _validate_route_state(route_state)
    if not state.get("enabled"):
        return [], "", 0

    prototype_by_key = {item["key"]: item for item in PROTOTYPES}
    selected = []
    for match in state["matched"]:
        prototype = prototype_by_key[match["key"]]
        image = images.get(prototype["image_input"])
        if _is_empty_image(image):
            raise ValueError(f'{prototype["name"]}已命中，但对应参考图没有连接。')
        if isinstance(image, (list, tuple)):
            if len(image) != 1:
                raise ValueError(
                    f'{prototype["name"]}的输入必须是一张参考图，不能预先传入图片列表。'
                )
            image = image[0]
        shape = getattr(image, "shape", None)
        if shape is None or len(shape) != 4:
            raise TypeError(f'{prototype["name"]}参考图不是标准 ComfyUI IMAGE 张量。')
        if int(shape[0]) != 1:
            raise ValueError(
                f'{prototype["name"]}参考图必须只含一张图片，当前 batch 数为 {shape[0]}。'
            )
        selected.append(image)

    first_shape = tuple(selected[0].shape[1:])
    for image in selected[1:]:
        if tuple(image.shape[1:]) != first_shape:
            raise ValueError(
                "多张参考图的高、宽和通道数必须一致；请在本节点前分别调整到相同尺寸。"
            )

    # BALLMImg's egress uploader iterates a Python sequence and gives every item
    # directly to PIL.Image.fromarray. A standard ComfyUI [N,H,W,C] IMAGE batch
    # is therefore treated as one four-dimensional image and fails in PIL.
    # Keep this list as one opaque Comfy payload (OUTPUT_IS_LIST=False), while
    # removing each input's singleton batch dimension so every item is HWC.
    individual_images = [image[0] for image in selected]
    return individual_images, build_reference_manifest(state), len(individual_images)


class PeaceElitePrototypeRouter:
    """Legacy output contract retained for workflows saved before v0.3.0."""

    @classmethod
    def INPUT_TYPES(cls):
        return _router_input_types()

    RETURN_TYPES = (
        "PEACE_ELITE_ROUTE",
        "BOOLEAN",
        "BOOLEAN",
        "BOOLEAN",
        "BOOLEAN",
        "BOOLEAN",
        "BOOLEAN",
        "BOOLEAN",
        "STRING",
        "STRING",
        "STRING",
    )
    RETURN_NAMES = (
        "route_state",
        "prototype_enabled",
        "pan",
        "screaming_chicken",
        "airdrop_crate",
        "level3_armor",
        "level3_backpack",
        "level3_helmet",
        "matched_names",
        "matched_ids_json",
        "user_input_json",
    )
    FUNCTION = "route"
    CATEGORY = "ByteArtist/logic"

    def route(self, category_code, user_input):
        state = build_route_state(category_code, user_input)
        matched_keys = {item["key"] for item in state["matched"]}
        matched_names = "、".join(item["name"] for item in state["matched"])
        matched_ids = [item["id"] for item in state["matched"]]
        user_input_json = _build_user_input_json(state)
        flags = [prototype["key"] in matched_keys for prototype in PROTOTYPES]

        return (
            state,
            state["enabled"],
            *flags,
            matched_names,
            json.dumps(matched_ids, separators=(",", ":")),
            user_input_json,
        )


class PeaceElitePrototypeRouterCompact:
    """Expose only the three outputs required by current workflows."""

    @classmethod
    def INPUT_TYPES(cls):
        return _router_input_types()

    RETURN_TYPES = (
        "PEACE_ELITE_ROUTE",
        "BOOLEAN",
        "STRING",
    )
    RETURN_NAMES = (
        "route_state",
        "prototype_enabled",
        "user_input_json",
    )
    FUNCTION = "route"
    CATEGORY = "ByteArtist/logic"

    def route(self, category_code, user_input):
        state = build_route_state(category_code, user_input)
        return state, state["enabled"], _build_user_input_json(state)


class PeaceElitePEAssembler:
    """Assemble the common PE, ordered reference bindings, and active prototype modules."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "route_state": ("PEACE_ELITE_ROUTE",),
                "common_pe": ("STRING", {"default": "", "multiline": True, "forceInput": True}),
            },
            "optional": {
                "pan_module": ("STRING", {"default": "", "multiline": True, "forceInput": True}),
                "screaming_chicken_module": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
                "airdrop_crate_module": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
                "level3_armor_module": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
                "level3_backpack_module": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
                "level3_helmet_module": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("assembled_pe", "reference_manifest")
    FUNCTION = "assemble"
    CATEGORY = "ByteArtist/text"

    def assemble(self, route_state, common_pe, **modules):
        return assemble_prototype_pe(route_state, common_pe, modules)


class PeaceEliteReferenceBatch:
    """Select matched references lazily as one ordered list of HWC image tensors."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "route_state": ("PEACE_ELITE_ROUTE",),
            },
            "optional": {
                "pan_image": ("IMAGE", {"lazy": True}),
                "screaming_chicken_image": ("IMAGE", {"lazy": True}),
                "airdrop_crate_image": ("IMAGE", {"lazy": True}),
                "level3_armor_image": ("IMAGE", {"lazy": True}),
                "level3_backpack_image": ("IMAGE", {"lazy": True}),
                "level3_helmet_image": ("IMAGE", {"lazy": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("reference_images", "reference_manifest", "reference_count")
    # False is intentional: Comfy wraps the Python list as one payload, so the
    # downstream generator executes once and receives every ordered reference.
    OUTPUT_IS_LIST = (False, False, False)
    FUNCTION = "collect"
    CATEGORY = "ByteArtist/image"

    def check_lazy_status(self, route_state, **images):
        state = _validate_route_state(route_state)
        if not state.get("enabled"):
            return []

        prototype_by_key = {item["key"]: item for item in PROTOTYPES}
        needed = []
        for match in state["matched"]:
            input_name = prototype_by_key[match["key"]]["image_input"]
            if input_name in images and images[input_name] is None:
                needed.append(input_name)
        return needed

    def collect(self, route_state, **images):
        return collect_reference_batch(route_state, images)


class PeaceEliteEmbeddedImage:
    """Decode one losslessly embedded source file into a standard ComfyUI IMAGE."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_name": ("STRING", {"default": "embedded.png"}),
                "expected_sha256": ("STRING", {"default": ""}),
                "image_base64": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "dynamicPrompts": False,
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "load"
    CATEGORY = "ByteArtist/image"

    def load(self, image_name, expected_sha256, image_base64):
        import torch

        image = decode_embedded_image_array(
            image_base64,
            expected_sha256=expected_sha256,
            image_name=image_name,
        )
        return (torch.from_numpy(image).unsqueeze(0),)


NODE_CLASS_MAPPINGS = {
    "PeaceElitePrototypeRouter": PeaceElitePrototypeRouter,
    "PeaceElitePrototypeRouterCompact": PeaceElitePrototypeRouterCompact,
    "PeaceElitePEAssembler": PeaceElitePEAssembler,
    "PeaceEliteReferenceBatch": PeaceEliteReferenceBatch,
    "PeaceEliteEmbeddedImage": PeaceEliteEmbeddedImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PeaceElitePrototypeRouter": "和平精英原型路由（兼容旧版）",
    "PeaceElitePrototypeRouterCompact": "和平精英原型路由（精简）",
    "PeaceElitePEAssembler": "和平精英原型 PE 组装",
    "PeaceEliteReferenceBatch": "和平精英有序多参考图列表",
    "PeaceEliteEmbeddedImage": "工作流内嵌参考图",
}

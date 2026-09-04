import json
import re
import unicodedata


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

ALLOWED_ROUTE_CONSTRAINTS = {
    "HIGH_VALUE",
    "BRAND_ASSET",
    "BIOLOGICAL",
    "VEHICLE",
    "SCENE",
    "FACILITY",
    "OVER_BUDGET",
}

_TRADITIONAL_POLICY_TRANSLATION = str.maketrans(
    {
        "黃": "黄",
        "鑽": "钻",
        "級": "级",
        "頭": "头",
        "盔": "盔",
        "純": "纯",
        "鍍": "镀",
        "寶": "宝",
        "滿": "满",
        "現": "现",
        "錶": "表",
    }
)

_SAFE_VALUE_CONTEXTS = (
    re.compile(r"金色(?:配色|涂装|喷漆)"),
    re.compile(r"金黄色"),
    re.compile(r"(?:黄金|钻石)(?:段位|排位|局)"),
)

_HIGH_VALUE_TERMS = (
    "钻戒",
    "黄金",
    "纯金",
    "足金",
    "24k",
    "镀金",
    "鎏金",
    "钻石",
    "镶钻",
    "满钻",
    "碎钻",
    "宝石",
    "珠宝",
    "金条",
    "现金堆",
    "大额现金",
    "奢华限量",
    "奢侈限量",
    "收藏级",
)

_BRAND_ASSET_PATTERNS = (
    re.compile(r"logo", re.IGNORECASE),
    re.compile(r"商标(?:图形)?"),
    re.compile(r"品牌(?:图标|标志|logo)", re.IGNORECASE),
    re.compile(r"官方标准字"),
    re.compile(r"商业字标"),
    re.compile(r"品牌吉祥物"),
)

_GENERIC_FALLBACK_TEXTS = {"心意收到", "心意", "收到", "自定义礼物", "礼物"}

# High-confidence extra subjects that must not be silently dropped merely
# because the same input also names one of the six fixed prototypes. This is
# deliberately a narrow bypass guard, not a replacement for the generic LLM
# subject router.
_PROTOTYPE_FORBIDDEN_REMAINDER_TERMS = (
    "企鹅",
    "金毛犬",
    "小狗",
    "狗狗",
    "猫咪",
    "兔兔",
    "大象",
    "老虎",
    "狮子",
    "狼王",
    "风暴龙王",
    "人物",
    "角色",
    "皮肤",
    "幼崽",
    "跑车",
    "汽车",
    "赛车",
    "摩托车",
    "自行车",
    "游轮",
    "邮轮",
    "轮船",
    "飞船",
    "飞机",
    "直升机",
    "坦克",
    "载具",
    "交通工具",
    "镜面空间",
    "无限空间",
    "场景",
    "环境",
    "建筑",
    "城堡",
    "宫殿",
    "城市",
    "森林",
    "海洋",
    "天空",
    "宇宙",
    "摩天轮",
    "过山车",
    "游乐园",
    "体育馆",
    "大型装置",
    "大型设施",
)

# Ordinary low-value support props that may remain subordinate to a bound
# prototype in the 99-diamond workflow. They do not receive a reference image;
# high-value, brand, biological, vehicle, scene and facility guards still win.
_99_ALLOWED_SUPPORT_OBJECT_TERMS = (
    "akm",
    "m416",
    "枪械",
    "步枪",
    "冲锋枪",
    "狙击枪",
    "手枪",
    "枪",
    "刀",
    "弓弩",
    "手雷",
    "地雷",
    "手机",
    "电子产品",
    "吉他",
    "乐器",
    "魔法杖",
    "宝箱",
    "无人机",
    "瞄准镜",
)

_99_PROTOTYPE_ACTION_TERMS = (
    "落地",
    "奔跑",
    "冲刺",
    "起跳",
    "跳跃",
    "跳舞",
    "弯腰",
    "鞠躬",
    "摔倒",
    "跌倒",
    "欢呼",
    "尖叫",
    "杂耍",
    "躲闪",
    "探头",
    "追赶",
    "逃跑",
    "挥舞",
    "摇摆",
    "翻滚",
    "站立",
    "坐下",
    "趴下",
    "躺下",
    "奔入",
    "冲入",
    "飞入",
    "滑入",
    "跌入",
    "跳入",
    "画外",
    "画内",
    "快速",
    "缓慢",
    "突然",
    "原地",
    "向前",
    "向后",
    "向左",
    "向右",
    "随后",
    "然后",
    "再",
    "后",
)


def normalize_policy_text(value):
    """Normalize only for policy matching; never use this as displayed user text."""
    text = unicodedata.normalize("NFKC", _as_text(value)).translate(
        _TRADITIONAL_POLICY_TRANSLATION
    )
    text = text.replace("💎", "钻石")
    return re.sub(r"\s+", "", text).lower()


def detect_policy_constraints(user_input):
    """Return deterministic high-confidence constraints without rewriting the input."""
    normalized = normalize_policy_text(user_input)
    value_scan = normalized
    for pattern in _SAFE_VALUE_CONTEXTS:
        value_scan = pattern.sub("", value_scan)

    constraints = []
    if any(term in value_scan for term in _HIGH_VALUE_TERMS):
        constraints.append("HIGH_VALUE")
    if any(pattern.search(normalized) for pattern in _BRAND_ASSET_PATTERNS):
        constraints.append("BRAND_ASSET")
    return constraints


def _matched_prototype_terms(user_input):
    text = _as_text(user_input)
    matches = []
    for prototype in PROTOTYPES:
        matched = next((term for term in prototype["terms"] if term in text), None)
        if matched:
            matches.append(matched)
    return matches


def _is_prototype_only_request(user_input, matched_terms, extra_phrases=()):
    """Recognize stable prototype-only wording that the short LLM may not veto."""
    remainder = normalize_policy_text(user_input)
    for term in sorted(matched_terms, key=len, reverse=True):
        remainder = remainder.replace(normalize_policy_text(term), "")

    removable_phrases = (
        "和平精英",
        "金色配色",
        "金色涂装",
        "金色喷漆",
        "金黄色",
        "黄金段位",
        "钻石段位",
        "黄金排位",
        "钻石排位",
        "黄金局",
        "钻石局",
        "不要",
        "只要",
        "以及",
        "还有",
        "拿着",
        "持握",
        "戴着",
        "佩戴",
        "穿着",
        "背着",
        "抱着",
        "举着",
        "扛着",
        "顶着",
        "叼着",
        "挂着",
        "踩着",
        "坐在",
        "靠着",
        "放在",
        "装进",
        "跳进去",
        "跳出来",
        "撞向",
        "砸向",
        "抛出",
        "接住",
        "旁边",
        "里面",
        "外面",
        "一起",
        "同时",
        "装备",
        "换上",
        "脱下",
        "打开",
        "破损",
        "损坏",
        "全新",
        "旋转",
        "翻转",
        "碰撞",
        "格挡",
        "和",
        "与",
        "及",
        "加",
        "拿",
        "戴",
        "穿",
        "背",
        "装",
        "开",
        "掉落",
        "落下",
        "砸",
        "挡",
        "从",
        "在",
        "里",
        "有",
        "的",
    )
    for phrase in (*extra_phrases, *removable_phrases):
        remainder = remainder.replace(phrase, "")
    remainder = re.sub(r"[，。！？、,.;:：；!?()（）\[\]【】<>《》\-—_]+", "", remainder)
    return not remainder


def _has_forbidden_prototype_remainder(user_input, matched_terms):
    """Catch stable positive mixed subjects while preserving negation/comparisons."""
    remainder = normalize_policy_text(user_input)
    # “不要企鹅，只要三级头” keeps the prototype and must not be treated as a
    # positive penguin request. Conversely “不要三级头，只要跑车” leaves the
    # vehicle in the remainder and therefore closes the prototype path.
    remainder = re.sub(r"不要.*?(?=只要)", "", remainder)
    # “三级头像跑车一样快” is a comparison, not a request to draw the car.
    remainder = re.sub(r"像[^，。；,.;]{1,24}(?:一样|似的)", "", remainder)
    for term in sorted(matched_terms, key=len, reverse=True):
        remainder = remainder.replace(normalize_policy_text(term), "")
    return any(term in remainder for term in _PROTOTYPE_FORBIDDEN_REMAINDER_TERMS)


def guard_prototype_category(category_code, user_input, llm_decision):
    """Combine deterministic prototype facts with the semantic LLM's narrow decision."""
    if _as_text(category_code).strip() != "3":
        return "0"
    matched_terms = _matched_prototype_terms(user_input)
    if not matched_terms:
        return "0"
    if detect_policy_constraints(user_input):
        return "0"
    if _has_forbidden_prototype_remainder(user_input, matched_terms):
        return "0"
    if _is_prototype_only_request(user_input, matched_terms):
        return "3"
    return "3" if _as_text(llm_decision).strip() == "3" else "0"


def guard_prototype_category_strict(category_code, user_input, llm_decision):
    """99-diamond guard: keep prototype actions and affordable support props."""
    if _as_text(category_code).strip() != "3":
        return "0"
    matched_terms = _matched_prototype_terms(user_input)
    if not matched_terms:
        return "0"
    if detect_policy_constraints(user_input):
        return "0"
    if _has_forbidden_prototype_remainder(user_input, matched_terms):
        return "0"
    if _is_prototype_only_request(
        user_input,
        matched_terms,
        (*_99_ALLOWED_SUPPORT_OBJECT_TERMS, *_99_PROTOTYPE_ACTION_TERMS),
    ):
        return "3"
    return guard_prototype_category(category_code, user_input, llm_decision)


def _extract_json_object(value):
    text = _as_text(value)
    start = text.find("{")
    if start < 0:
        return None
    try:
        result, _ = json.JSONDecoder().raw_decode(text[start:])
    except (json.JSONDecodeError, TypeError):
        return None
    return result if isinstance(result, dict) else None


def _visible_length(value):
    return len(re.sub(r"\s+", "", _as_text(value)))


IMAGE_PROMPT_MAIN_PREFIX = (
    "3D render, premium stylized 3D animated, high-end animation-film "
    "rendering, live gift icon quality."
)


def _text_display_lock(display_text):
    return (
        f"画面唯一可见文字必须逐字为「{display_text}」，"
        f"共{_visible_length(display_text)}个可见字符，"
        "不得增删、替换、翻译或生成其他文字。"
    )


def guard_image_prompt_text(image_prompt, spec_json):
    """Require the Planner's exact TEXT payload before image generation."""
    prompt = _as_text(image_prompt).strip()
    if not prompt:
        raise ValueError("IMAGE_PROMPT is empty")

    spec = _extract_json_object(spec_json)
    if not isinstance(spec, dict) or spec.get("schema_version") != 3:
        raise ValueError("PlannerSpec is invalid for IMAGE_PROMPT validation")
    if spec.get("render_mode") != "TEXT":
        return prompt

    display_text = _as_text(spec.get("display_text")).strip()
    if not display_text:
        raise ValueError("TEXT PlannerSpec display_text is empty")

    required_start = f"{IMAGE_PROMPT_MAIN_PREFIX} {_text_display_lock(display_text)}"
    if not prompt.startswith(required_start):
        raise ValueError(
            "TEXT IMAGE_PROMPT must start with the exact display_text and visible-character lock"
        )

    remainder = prompt[len(required_start) :].replace(display_text, "")
    conflicting_count = re.search(
        r"(?:\d+|[零〇一二两三四五六七八九十百]+)"
        r"(?:个(?:可见)?字符|个字|字)",
        remainder,
    )
    if conflicting_count:
        raise ValueError("TEXT IMAGE_PROMPT contains a conflicting character-count claim")
    return prompt


def _compact_user_anchor(user_input):
    original = _as_text(user_input).strip()
    compact = re.sub(r"\s+", "", original)
    if 1 <= len(compact) <= 8:
        return compact

    quoted = re.search(r"[“\"']([^”\"']{2,8})[”\"']", original)
    if quoted:
        return re.sub(r"\s+", "", quoted.group(1))

    if "只要" in compact:
        tail = compact.rsplit("只要", 1)[1]
        tail = re.split(r"[，。；,.;]", tail, maxsplit=1)[0]
        if 1 <= len(tail) <= 8:
            return tail

    requested = re.search(
        r"(?:生成|画出|制作|做成|变成)(?:一个|一件|一枚|一只|完整)?([^，。；,.;]{2,8})",
        compact,
    )
    if requested:
        return requested.group(1)

    reduced = compact
    for phrase in ("旁边有", "旁边", "以及", "还有", "和", "与", "加"):
        reduced = reduced.replace(phrase, "")
    reduced = re.sub(r"[^\u3400-\u9fffA-Za-z0-9💎]+", "", reduced)
    return (reduced or "输入内容")[:6]


def _safe_display_text(user_input, route):
    original = re.sub(r"\s+", "", _as_text(user_input).strip())
    if 1 <= len(original) <= 8:
        return original, "EXACT_INPUT"

    candidate = _as_text(route.get("display_text") if route else "").strip()
    if (
        1 <= _visible_length(candidate) <= 12
        and candidate not in _GENERIC_FALLBACK_TEXTS
    ):
        source = _as_text(route.get("text_source")).strip()
        if source not in {
            "EXACT_INPUT",
            "EXPLICIT_TEXT",
            "EXACT_EXTRACT",
            "SEMANTIC_SUMMARY",
        }:
            source = "SEMANTIC_SUMMARY"
        return candidate, source
    return _compact_user_anchor(user_input), "SEMANTIC_SUMMARY"


def _build_text_route(user_input, route, constraints):
    display_text, text_source = _safe_display_text(user_input, route or {})
    input_kind = _as_text((route or {}).get("input_kind")).strip()
    if input_kind not in {"TERM", "REQUEST", "DESIGN_BRIEF"}:
        input_kind = "TERM" if _visible_length(user_input) <= 8 else "REQUEST"
    constraint_text = "、".join(constraints) if constraints else "OVER_BUDGET"
    brief = (
        f"主体为TEXT；展示文字为“{display_text}”，逐字准确；"
        f"硬约束为{constraint_text}；只把受限对象保留为可见字符语义，"
        "使用价值中性的主题化字骨、组字和非物象整合装饰，不生成对应物象、局部、材质、包装、标识、场景或特效。"
    )
    return {
        "schema_version": 2,
        "type": "TEXT",
        "mode": "TEXT",
        "input_kind": input_kind,
        "focus": display_text,
        "constraints": constraints or ["OVER_BUDGET"],
        "display_text": display_text,
        "text_source": text_source,
        "production_brief": brief,
    }


def guard_route_output(llm_output, user_input):
    """Validate the semantic compiler and hard-lock deterministic policy outcomes."""
    route = _extract_json_object(llm_output)
    detected = detect_policy_constraints(user_input)
    existing = route.get("constraints", []) if isinstance(route, dict) else []
    constraints = []
    for item in [*existing, *detected]:
        if item in ALLOWED_ROUTE_CONSTRAINTS and item not in constraints:
            constraints.append(item)

    valid = (
        isinstance(route, dict)
        and route.get("schema_version") == 2
        and route.get("type") in {"OBJECT", "DIORAMA", "TEXT"}
        and route.get("mode") in {"NATIVE", "REPRESENTATIVE", "TEXT"}
        and isinstance(route.get("production_brief"), str)
        and bool(route.get("production_brief", "").strip())
    )
    hard_text = any(item in constraints for item in ("HIGH_VALUE", "BRAND_ASSET"))
    unrelated_fallback = (
        valid
        and route.get("type") == "TEXT"
        and _as_text(route.get("display_text")).strip() in _GENERIC_FALLBACK_TEXTS
        and _as_text(route.get("display_text")).strip() not in _as_text(user_input)
    )

    if not valid or hard_text or unrelated_fallback:
        route = _build_text_route(user_input, route if isinstance(route, dict) else {}, constraints)
    else:
        route["constraints"] = constraints

    marker = f'<<<SUBJECT_{route["type"]}>>>'
    route_json = json.dumps(route, ensure_ascii=False, separators=(",", ":"))
    return f"{marker}\n{route_json}", route_json


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


def _policy_router_input_types():
    return {
        "required": {
            "category_code": ("STRING", {"default": "", "forceInput": True}),
            "user_input": (
                "STRING",
                {"default": "", "multiline": True, "forceInput": True},
            ),
            "llm_decision": ("STRING", {"default": "", "forceInput": True}),
        }
    }


class PeaceElitePrototypePolicyRouter(PeaceElitePrototypeRouter):
    """99-diamond router with a strict six-prototype-only policy backstop."""

    @classmethod
    def INPUT_TYPES(cls):
        return _policy_router_input_types()

    def route(self, category_code, user_input, llm_decision):
        guarded = guard_prototype_category_strict(
            category_code, user_input, llm_decision
        )
        return super().route(guarded, user_input)


class PeaceElitePrototypePolicyRouterCompact(PeaceElitePrototypeRouterCompact):
    """Compact-output router with deterministic prototype and value-policy enforcement."""

    @classmethod
    def INPUT_TYPES(cls):
        return _policy_router_input_types()

    def route(self, category_code, user_input, llm_decision):
        guarded = guard_prototype_category(category_code, user_input, llm_decision)
        return super().route(guarded, user_input)


class GameUGCRoutePolicyGuard:
    """Validate route JSON and force deterministic brand/value outcomes to TEXT."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "llm_output": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
                "user_input": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("validated_output", "route_json")
    FUNCTION = "guard"
    CATEGORY = "ByteArtist/logic"

    def guard(self, llm_output, user_input):
        return guard_route_output(llm_output, user_input)


def _normalize_name_piece(value):
    return re.sub(r"\s+", "", _as_text(value).strip())


def _planner_name(user_input, route):
    """Return a <=6-character gift name built only from source spans."""
    compact = _normalize_name_piece(user_input)
    if 1 <= len(compact) <= 6:
        return compact, [compact], "EXACT_INPUT"

    raw_sources = route.get("name_source", []) if isinstance(route, dict) else []
    if isinstance(raw_sources, str):
        raw_sources = [raw_sources]
    sources = []
    cursor = 0
    for raw_piece in raw_sources[:3] if isinstance(raw_sources, list) else []:
        piece = _normalize_name_piece(raw_piece)
        if not piece:
            continue
        index = compact.find(piece, cursor)
        if index < 0:
            sources = []
            break
        sources.append(piece)
        cursor = index + len(piece)

    joined = "".join(sources)
    proposed = _normalize_name_piece(route.get("gift_name", "")) if isinstance(route, dict) else ""
    if sources and joined == proposed and 1 <= len(joined) <= 6:
        return joined, sources, "EXACT_EXTRACT"

    for key in ("display_text", "visual_subject"):
        candidate = _normalize_name_piece(route.get(key, "")) if isinstance(route, dict) else ""
        if 1 <= len(candidate) <= 6 and candidate in compact:
            return candidate, [candidate], "EXACT_EXTRACT"

    for prototype in PROTOTYPES:
        for term in prototype["terms"]:
            if term in compact and len(term) <= 6:
                return term, [term], "EXACT_EXTRACT"

    anchor = _normalize_name_piece(_compact_user_anchor(user_input))[:6] or "礼物"
    source = anchor if anchor in compact else compact[:6]
    source = source or "礼物"
    return source[:6], [source[:6]], "SAFE_FALLBACK"


def _planner_text_spec(user_input, route, constraints):
    display_text, _ = _safe_display_text(user_input, route or {})
    display_text = _normalize_name_piece(display_text)[:12] or "礼物"
    base = dict(route) if isinstance(route, dict) else {}
    base.update(
        {
            "schema_version": 3,
            "user_input": _as_text(user_input),
            "need_search": False,
            "search_query": "",
            "search_reason": "",
            "prototype_decision": "0",
            "render_mode": "TEXT",
            "subject_mode": "TEXT",
            "visual_subject": display_text,
            "entities": [display_text],
            "relation": "",
            "action_intent": _as_text(base.get("action_intent")).strip()[:120],
            "constraints": constraints or ["OVER_BUDGET"],
            "display_text": display_text,
            "evidence": [],
        }
    )
    return base


def guard_planner_output(llm_output, user_input):
    """Validate the v3 planner contract and keep search/name decisions compact."""
    route = _extract_json_object(llm_output)
    detected = detect_policy_constraints(user_input)
    existing = route.get("constraints", []) if isinstance(route, dict) else []
    constraints = []
    if not isinstance(existing, list):
        existing = []
    for item in [*existing, *detected]:
        if item in ALLOWED_ROUTE_CONSTRAINTS and item not in constraints:
            constraints.append(item)

    valid = (
        isinstance(route, dict)
        and route.get("schema_version") == 3
        and route.get("render_mode") in {"OBJECT", "TEXT"}
        and route.get("subject_mode")
        in {"DIRECT", "REPRESENTATIVE", "RELATION", "TEXT"}
        and _as_text(route.get("prototype_decision")).strip() in {"3", "0"}
    )
    hard_text = any(item in constraints for item in ("HIGH_VALUE", "BRAND_ASSET"))
    if not valid or hard_text:
        route = _planner_text_spec(
            user_input,
            route if isinstance(route, dict) else {},
            constraints,
        )
    else:
        route = dict(route)
        route["schema_version"] = 3
        route["user_input"] = _as_text(user_input)
        route["constraints"] = constraints
        if route["render_mode"] == "TEXT":
            route["subject_mode"] = "TEXT"
            display_text, _ = _safe_display_text(user_input, route)
            route["display_text"] = _normalize_name_piece(display_text)[:12] or "礼物"
            route["visual_subject"] = route["display_text"]
            route["entities"] = [route["display_text"]]
        else:
            route.pop("display_text", None)
            entities = route.get("entities", [])
            if not isinstance(entities, list):
                entities = []
            route["entities"] = [
                _as_text(item).strip()[:80]
                for item in entities[:4]
                if _as_text(item).strip()
            ]
            route["visual_subject"] = _as_text(route.get("visual_subject")).strip()[:120]

        route["relation"] = _as_text(route.get("relation")).strip()[:160]
        route["action_intent"] = _as_text(route.get("action_intent")).strip()[:160]
        evidence = route.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []
        route["evidence"] = [
            _as_text(item).strip()[:160]
            for item in evidence[:3]
            if _as_text(item).strip()
        ]

        prototype_decision = _as_text(route.get("prototype_decision")).strip()
        route["prototype_decision"] = prototype_decision
        need_search = bool(route.get("need_search")) and prototype_decision == "0"
        search_query = _as_text(route.get("search_query")).strip()[:160]
        route["need_search"] = bool(need_search and search_query)
        route["search_query"] = search_query if route["need_search"] else ""
        route["search_reason"] = (
            _as_text(route.get("search_reason")).strip()[:120]
            if route["need_search"]
            else ""
        )

    gift_name, sources, name_mode = _planner_name(user_input, route)
    route["gift_name"] = gift_name
    route["name_source"] = sources
    route["name_mode"] = name_mode

    ordered_keys = (
        "schema_version",
        "user_input",
        "gift_name",
        "name_source",
        "name_mode",
        "need_search",
        "search_query",
        "search_reason",
        "prototype_decision",
        "render_mode",
        "subject_mode",
        "visual_subject",
        "entities",
        "relation",
        "action_intent",
        "constraints",
        "display_text",
        "evidence",
    )
    route = {key: route[key] for key in ordered_keys if key in route}
    marker = f'<<<SUBJECT_{route["render_mode"]}>>>'
    spec_json = json.dumps(route, ensure_ascii=False, separators=(",", ":"))
    return (
        f"{marker}\n{spec_json}",
        spec_json,
        route["need_search"],
        route["prototype_decision"],
    )


class GameUGCPlannerPolicyGuard:
    """Validate v3 PlannerSpec, exact-source gift names, and conditional search."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "llm_output": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
                "user_input": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = (
        "validated_output",
        "spec_json",
        "need_search",
        "prototype_decision",
    )
    FUNCTION = "guard"
    CATEGORY = "ByteArtist/logic"

    def guard(self, llm_output, user_input):
        return guard_planner_output(llm_output, user_input)


class GameUGCImagePromptTextGuard:
    """Block TEXT image generation unless the exact Planner text is locked."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_prompt": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
                "spec_json": (
                    "STRING",
                    {"default": "", "multiline": True, "forceInput": True},
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("validated_prompt",)
    FUNCTION = "guard"
    CATEGORY = "ByteArtist/logic"

    def guard(self, image_prompt, spec_json):
        return (guard_image_prompt_text(image_prompt, spec_json),)


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


NODE_CLASS_MAPPINGS = {
    "PeaceElitePrototypeRouter": PeaceElitePrototypeRouter,
    "PeaceElitePrototypeRouterCompact": PeaceElitePrototypeRouterCompact,
    "PeaceElitePrototypePolicyRouter": PeaceElitePrototypePolicyRouter,
    "PeaceElitePrototypePolicyRouterCompact": PeaceElitePrototypePolicyRouterCompact,
    "PeaceElitePEAssembler": PeaceElitePEAssembler,
    "PeaceEliteReferenceBatch": PeaceEliteReferenceBatch,
    "GameUGCRoutePolicyGuard": GameUGCRoutePolicyGuard,
    "GameUGCPlannerPolicyGuard": GameUGCPlannerPolicyGuard,
    "GameUGCImagePromptTextGuard": GameUGCImagePromptTextGuard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PeaceElitePrototypeRouter": "和平精英原型路由（兼容旧版）",
    "PeaceElitePrototypeRouterCompact": "和平精英原型路由（精简）",
    "PeaceElitePrototypePolicyRouter": "和平精英原型策略路由（兼容旧版）",
    "PeaceElitePrototypePolicyRouterCompact": "和平精英原型策略路由（精简）",
    "PeaceElitePEAssembler": "和平精英原型 PE 组装",
    "PeaceEliteReferenceBatch": "和平精英有序多参考图列表",
    "GameUGCRoutePolicyGuard": "游戏 UGC 主体路由策略护栏",
    "GameUGCPlannerPolicyGuard": "游戏 UGC Planner 策略护栏",
    "GameUGCImagePromptTextGuard": "游戏 UGC TEXT 图像提示词护栏",
}

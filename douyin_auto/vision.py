import os
import hashlib
import time
import numpy as np


try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = (
        r"D:\Program Files\Tesseract-OCR\tesseract.exe"
    )
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    from rapidocr import RapidOCR

    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False

try:
    from cnocr import CnOcr

    CNOCR_AVAILABLE = True
except ImportError:
    CNOCR_AVAILABLE = False

OCR_AVAILABLE = PYTESSERACT_AVAILABLE or RAPIDOCR_AVAILABLE or CNOCR_AVAILABLE

_pytesseract_initialized = False
_rapidocr_instance = None
_cnocr_instance = None


def _get_rapidocr():
    """获取 RapidOCR 实例"""
    global _rapidocr_instance
    if _rapidocr_instance is None and RAPIDOCR_AVAILABLE:
        try:
            from rapidocr import RapidOCR

            _rapidocr_instance = RapidOCR()
        except Exception as e:
            print("RapidOCR 初始化失败：%s" % e)
    return _rapidocr_instance


def _get_cnocr():
    """获取 cnocr 实例"""
    global _cnocr_instance
    if _cnocr_instance is None and CNOCR_AVAILABLE:
        try:
            from cnocr import CnOcr

            _cnocr_instance = CnOcr()
        except Exception as e:
            print("cnocr 初始化失败：%s" % e)
    return _cnocr_instance


def _init_pytesseract():
    """初始化 pytesseract"""
    global _pytesseract_initialized
    if not _pytesseract_initialized and PYTESSERACT_AVAILABLE:
        try:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = (
                r"D:\Program Files\Tesseract-OCR\tesseract.exe"
            )
            _pytesseract_initialized = True
        except Exception as e:
            print("初始化 pytesseract 失败：%s" % e)


def recognize_text(image, lang="cn"):
    """
    识别图像中的文字（使用 pytesseract，轻量级 OCR）

    Args:
        image: BGR 格式图像
        lang: 语言类型 'cn' 中文，'en' 英文

    Returns:
        results: list - 识别结果列表 [{"text": "文字", "bbox": (x1,y1,x2,y2)}, ...]
    """
    if image is None:
        return []

    if not PYTESSERACT_AVAILABLE:
        return []

    try:
        _init_pytesseract()
        if not _pytesseract_initialized:
            return []

        import pytesseract

        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        from PIL import Image

        pil_img = Image.fromarray(img_rgb)

        try:
            data = pytesseract.image_to_data(
                pil_img, lang="eng", output_type=pytesseract.Output.DICT
            )
        except Exception:
            text = pytesseract.image_to_string(pil_img, lang="eng")
            if text.strip():
                h, w = image.shape[:2]
                return [{"text": text.strip(), "bbox": [[0, 0, w, h]]}]
            return []

        results = []
        n_boxes = len(data.get("text", []))
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if text:
                try:
                    x = int(float(data["left"][i]))
                    y = int(float(data["top"][i]))
                    w = int(float(data["width"][i]))
                    h = int(float(data["height"][i]))
                    bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                    results.append({"text": text, "bbox": bbox})
                except (ValueError, TypeError, KeyError):
                    continue
        return results
    except Exception as e:
        print("pytesseract 识别错误：%s" % e)
        return []
        boxes = np.array(boxes)
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 0] + boxes[:, 2]
        y2 = boxes[:, 1] + boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        idxs = np.argsort(y2)
        pick = []
        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            overlap = (w * h) / areas[idxs[:last]]
            idxs = np.delete(
                idxs, np.concatenate(([last], np.where(overlap > overlap_thresh)[0]))
            )
            pick.append(i)
        return boxes[pick].tolist()

    matches = nms(matches, overlap_thresh=0.3)
    matches = [tuple(m) for m in matches]

    found = len(matches) > 0

    debug_image = None
    if debug and found:
        debug_image = image.copy()
        for x, y, w, h in matches:
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return found, len(matches), matches, debug_image


def detect_red_badge(image, min_area=50, debug=False):
    """
    检测图像中的红色标记（未读消息红点）

    Args:
        image: BGR 格式图像
        min_area: 最小红色区域面积阈值
        debug: 是否返回调试图像

    Returns:
        has_badge: bool
        count: int - 红色像素数量
        debug_image: 如果 debug=True，返回带标记的调试图像
    """
    if image is None or not CV2_AVAILABLE:
        return False, 0, None

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)

    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)

    mask = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    red_pixel_count = cv2.countNonZero(mask)

    has_badge = red_pixel_count >= min_area

    debug_image = None
    if debug:
        debug_image = image.copy()
        if has_badge:
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for cnt in contours:
                if cv2.contourArea(cnt) >= min_area:
                    x, y, w, h = cv2.boundingRect(cnt)
                    cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return has_badge, red_pixel_count, debug_image


def find_default_kuang_template():
    """Return path to default kuang.jpg template if present."""
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    template_path = os.path.join(templates_dir, "kuang.jpg")

    if os.path.exists(template_path):
        return template_path
    return None


def detect_message_box_by_template(
    image, template_path=None, threshold=0.7, debug=False, scales=None
):
    """
    使用模板图片定位消息框位置（全局盒子，返回相对坐标）。

    Args:
        image: 待检测图像，BGR 格式
        template_path: 消息框模板图片路径
        threshold: 匹配阈值
        debug: 是否返回调试图像
        scales: 尺度集合，支持多尺度匹配，默认自动给出一组合理的缩放

    Returns:
        dict: {
            "box": (left_rel, top_rel, right_rel, bottom_rel),  # 相对坐标 0-1
            "left": left_rel, "right": right_rel, "top": top_rel, "bottom": bottom_rel,
            "debug_image": img or None
        }
    """
    # 如果未提供模板路径，尝试使用默认的 kuang.jpg 模板
    if template_path is None:
        template_path = find_default_kuang_template()
    if not CV2_AVAILABLE or image is None:
        return {
            "box": (0, 0, 1, 1),
            "left": 0,
            "right": 1,
            "top": 0,
            "bottom": 1,
            "debug_image": None,
        }
    import math

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE) if template_path else None
    if tpl is None:
        return {
            "box": (0, 0, 1, 1),
            "left": 0,
            "right": 1,
            "top": 0,
            "bottom": 1,
            "debug_image": None,
        }

    h_img, w_img = gray.shape[:2]
    best_score = -1.0
    best_loc = None
    best_size = tpl.shape[1], tpl.shape[0]

    # 默认尺度集合
    if scales is None:
        scales = [0.8, 1.0, 1.2]

    for s in scales:
        w_t, h_t = int(tpl.shape[1] * s), int(tpl.shape[0] * s)
        if w_t <= 0 or h_t <= 0:
            continue
        if w_t > w_img or h_t > h_img:
            continue
        resized = cv2.resize(tpl, (w_t, h_t))
        res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val > best_score:
            best_score = max_val
            best_loc = max_loc
            best_size = (w_t, h_t)

    if best_loc is None or best_score < threshold:
        return {
            "box": (0.50, 0.06, 0.97, 0.75),
            "left": 0.50,
            "right": 0.97,
            "top": 0.06,
            "bottom": 0.75,
            "debug_image": None,
        }

    x, y = best_loc
    w_box, h_box = best_size
    left_rel = x / w_img
    top_rel = y / h_img
    right_rel = (x + w_box) / w_img
    bottom_rel = (y + h_box) / h_img

    debug_image = None
    if debug:
        debug_image = image.copy()
        cv2.rectangle(debug_image, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)

    return {
        "box": (left_rel, top_rel, right_rel, bottom_rel),
        "left": left_rel,
        "right": right_rel,
        "top": top_rel,
        "bottom": bottom_rel,
        "debug_image": debug_image,
    }


def check_window_state_by_height(hwnd, open_top_y, closed_top_y, tolerance=0.02):
    """
    通过窗口高度判断私信窗口是否打开

    Args:
        hwnd: 窗口句柄
        open_top_y: 打开状态时的顶部相对坐标Y
        closed_top_y: 关闭状态时的顶部相对坐标Y
        tolerance: 容差

    Returns:
        is_open: bool - True表示窗口已打开
    """
    import win32gui

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    window_height = bottom - top

    current_top_y = (top - top) / window_height if window_height > 0 else 0

    is_open = abs(current_top_y - open_top_y) < tolerance

    return is_open


def compute_relative_position(abs_x, abs_y, hwnd):
    """
    将屏幕绝对坐标转换为相对坐标

    Args:
        abs_x, abs_y: 屏幕绝对坐标
        hwnd: 窗口句柄

    Returns:
        rel_x, rel_y: 相对坐标 (0-1)
    """
    import win32gui

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    if width <= 0 or height <= 0:
        return 0, 0

    rel_x = (abs_x - left) / width
    rel_y = (abs_y - top) / height

    return rel_x, rel_y


def get_absolute_position(rel_x, rel_y, hwnd):
    """
    将相对坐标转换为屏幕绝对坐标

    Args:
        rel_x, rel_y: 相对坐标 (0-1)
        hwnd: 窗口句柄

    Returns:
        abs_x, abs_y: 屏幕绝对坐标
    """
    import win32gui

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    abs_x = int(left + rel_x * width)
    abs_y = int(top + rel_y * height)

    return abs_x, abs_y


# ==================== 强化功能：模板匹配定位 ====================


def find_element_by_template(
    image, template, threshold=0.7, multi_scale=True, scales=None
):
    """
    使用模板匹配查找元素位置（支持多尺度）

    Args:
        image: 待检测图像 (BGR格式)
        template: 模板图像 (BGR格式) 或 模板图片路径
        threshold: 匹配阈值 (0.7 = 70% 相似度)
        multi_scale: 是否进行多尺度匹配
        scales: 自定义尺度列表，默认 [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]

    Returns:
        found: bool - 是否找到匹配
        center_x, center_y: 匹配中心点坐标（相对坐标 0-1）
        match_info: dict - 包含匹配详情
    """
    if not CV2_AVAILABLE:
        return False, 0, 0, {}

    if isinstance(template, str):
        template = cv2.imread(template)
        if template is None:
            return False, 0, 0, {"error": "Cannot load template: {}".format(template)}

    if image is None or template is None:
        return False, 0, 0, {"error": "Invalid image or template"}

    h_img, w_img = image.shape[:2]
    h_tpl, w_tpl = template.shape[:2]

    if h_tpl > h_img or w_tpl > w_img:
        return False, 0, 0, {"error": "Template larger than image"}

    if scales is None:
        scales = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]

    best_match = None
    best_score = threshold
    best_scale = 1.0
    best_loc = (0, 0)

    for scale in scales:
        if not multi_scale:
            scale = 1.0

        new_h = int(h_tpl * scale)
        new_w = int(w_tpl * scale)

        if new_h > h_img or new_w > w_img:
            continue

        resized = cv2.resize(template, (new_w, new_h))

        result = cv2.matchTemplate(image, resized, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = max_val
            best_scale = scale
            best_loc = max_loc
            best_match = resized

        if not multi_scale:
            break

    if best_match is None:
        return False, 0, 0, {"score": best_score, "scale": 1.0}

    center_x = (best_loc[0] + (w_tpl * best_scale) / 2) / w_img
    center_y = (best_loc[1] + (h_tpl * best_scale) / 2) / h_img

    match_info = {
        "score": best_score,
        "scale": best_scale,
        "location": best_loc,
        "width": int(w_tpl * best_scale),
        "height": int(h_tpl * best_scale),
    }

    return True, center_x, center_y, match_info


def find_button_candidates(image, debug=False):
    """
    查找图像中可能的按钮候选区域（基于颜色和形状特征）

    Args:
        image: BGR格式图像
        debug: 是否返回调试图像

    Returns:
        candidates: list - 候选区域列表 [(x, y, w, h), ...]
        debug_image: 调试图像
    """
    if not CV2_AVAILABLE or image is None:
        return [], None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 100:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = float(w) / h if h > 0 else 0

        if 0.3 < aspect_ratio < 3.0:
            candidates.append((x, y, w, h))

    debug_image = None
    if debug:
        debug_image = image.copy()
        for x, y, w, h in candidates:
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return candidates, debug_image


# ==================== 强化功能：OCR文字识别 ====================


def recognize_text(image, lang="cn"):
    """
    识别图像中的文字（优先使用 RapidOCR > cnocr > pytesseract）

    Args:
        image: BGR 格式图像
        lang: 语言类型 'cn' 中文，'en' 英文

    Returns:
        results: list - 识别结果列表 [{"text": "文字", "bbox": (x1,y1,x2,y2)}, ...]
    """
    if image is None:
        return []

    h, w = image.shape[:2]

    if RAPIDOCR_AVAILABLE:
        try:
            ocr = _get_rapidocr()
            if ocr is not None:
                img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                from PIL import Image

                pil_img = Image.fromarray(img_rgb)
                output = ocr(pil_img)
                boxes = output.boxes
                txts = output.txts
                if boxes is not None and txts is not None and len(boxes) > 0:
                    results = []
                    for bbox, text in zip(boxes, txts):
                        text = str(text).strip()
                        if text and bbox is not None:
                            x1, y1 = bbox[0]
                            x2, y2 = bbox[2]
                            results.append(
                                {
                                    "text": text,
                                    "bbox": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                                }
                            )
                    if results:
                        return results
        except Exception as e:
            print("RapidOCR 识别失败：%s" % e)

    if CNOCR_AVAILABLE:
        try:
            ocr = _get_cnocr()
            if ocr is not None:
                img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                from PIL import Image

                pil_img = Image.fromarray(img_rgb)
                results_cn = ocr(pil_img)
                if results_cn and len(results_cn) > 0:
                    results = []
                    for line in results_cn:
                        text = line["text"].strip()
                        if text:
                            bbox = line.get("bbox", [])
                            if bbox:
                                x1, y1 = bbox[0]
                                x2, y2 = bbox[2]
                                results.append(
                                    {
                                        "text": text,
                                        "bbox": [
                                            [x1, y1],
                                            [x2, y1],
                                            [x2, y2],
                                            [x1, y2],
                                        ],
                                    }
                                )
                    if results:
                        return results
        except Exception as e:
            print("cnocr 识别失败：%s" % e)

    if not PYTESSERACT_AVAILABLE:
        return []

    try:
        _init_pytesseract()
        import pytesseract as pt

        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        from PIL import Image

        pil_img = Image.fromarray(img_rgb)

        lang_code = "chi_sim" if lang == "cn" else "eng"
        try:
            data = pt.image_to_data(pil_img, lang=lang_code, output_type=pt.Output.DICT)
        except Exception:
            text = pt.image_to_string(pil_img, lang=lang_code)
            if text.strip():
                return [{"text": text.strip(), "bbox": [[0, 0, w, h]]}]
            return []

        results = []
        n_boxes = len(data.get("text", []))
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if text:
                try:
                    x = int(float(data["left"][i]))
                    y = int(float(data["top"][i]))
                    w_box = int(float(data["width"][i]))
                    h_box = int(float(data["height"][i]))
                    bbox = [
                        [x, y],
                        [x + w_box, y],
                        [x + w_box, y + h_box],
                        [x, y + h_box],
                    ]
                    results.append({"text": text, "bbox": bbox})
                except (ValueError, TypeError, KeyError):
                    continue
        return results
    except Exception as e:
        print("pytesseract 识别错误：%s" % e)
        return []


def find_text_position(image, target_text, lang="cn", debug=False):
    """
    查找文字在图像中的位置

    Args:
        image: BGR格式图像
        target_text: 目标文字
        lang: 语言类型
        debug: 是否返回调试图像

    Returns:
        found: bool
        center_x, center_y: 文字中心位置（相对坐标）
        debug_image: 调试图像
    """
    results = recognize_text(image, lang)

    for item in results:
        if target_text in item["text"]:
            bbox = item["bbox"]
            center_x = (bbox[0] + bbox[2]) / 2 / image.shape[1]
            center_y = (bbox[1] + bbox[3]) / 2 / image.shape[0]

            debug_image = None
            if debug:
                debug_image = image.copy()
                cv2.rectangle(
                    debug_image,
                    (int(bbox[0]), int(bbox[1])),
                    (int(bbox[2]), int(bbox[3])),
                    (0, 255, 0),
                    2,
                )

            return True, center_x, center_y, debug_image

    return False, 0, 0, None


# ==================== 强化功能：消息检测 ====================


def compute_image_hash(image):
    """
    计算图像的感知哈希（用于消息变化检测）

    Args:
        image: BGR格式图像

    Returns:
        hash_str: str - 图像哈希值
    """
    if image is None or not hasattr(image, "shape") or image.size == 0:
        return ""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (8, 8))
    avg = resized.mean()
    binary = (resized > avg).astype(np.uint8)
    hash_str = "".join(str(b) for b in binary.flatten())
    return hashlib.md5(hash_str.encode()).hexdigest()


def compare_images(image1, image2, threshold=0.1):
    """
    比较两张图像的差异

    Args:
        image1: 第一张图像
        image2: 第二张图像
        threshold: 差异阈值 (0.1 = 10% 差异)

    Returns:
        is_different: bool - 是否有差异
        diff_ratio: float - 差异比例
        diff_image: 差异图像
    """
    if image1 is None or image2 is None:
        return False, 0.0, None

    if image1.shape != image2.shape:
        image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))

    gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray1, gray2)
    _, binary = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

    diff_ratio = np.count_nonzero(binary) / binary.size

    is_different = diff_ratio > threshold
    diff_color = cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR)

    return is_different, diff_ratio, diff_color


def detect_message_area(image, region="left"):
    """
    检测消息区域（通常是评论区或消息列表）

    Args:
        image: BGR格式图像
        region: 区域类型 "left"(评论区), "right"(按钮区), "bottom"(输入框)

    Returns:
        cropped: 裁剪后的图像区域
    """
    if image is None or not hasattr(image, "shape") or image.size == 0:
        return None

    h, w = image.shape[:2]

    # 确保坐标不超出边界
    if region == "left":
        x1 = max(0, int(w * 0.05))
        x2 = min(w, int(w * 0.4))
        y1 = max(0, int(h * 0.1))
        y2 = min(h, int(h * 0.9))
        return image[y1:y2, x1:x2]
    elif region == "right":
        x1 = max(0, int(w * 0.85))
        x2 = min(w, int(w * 0.98))
        y1 = max(0, int(h * 0.1))
        y2 = min(h, int(h * 0.9))
        return image[y1:y2, x1:x2]
    elif region == "bottom":
        x1 = max(0, int(w * 0.1))
        x2 = min(w, int(w * 0.9))
        y1 = max(0, int(h * 0.8))
        y2 = min(h, int(h * 0.98))
        return image[y1:y2, x1:x2]
    else:
        return image


# ==================== 强化功能：智能点击定位 ====================


class SmartLocator:
    """
    智能定位器 - 组合多种定位方法
    """

    def __init__(self, hwnd, template_dir=None):
        self.hwnd = hwnd
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), "templates"
        )
        self._load_templates()

    def _load_templates(self):
        """加载模板目录下的所有模板"""
        self.templates = {}
        if not os.path.exists(self.template_dir):
            return

        for filename in os.listdir(self.template_dir):
            if filename.endswith((".png", ".jpg", ".jpeg")):
                name = os.path.splitext(filename)[0]
                template_path = os.path.join(self.template_dir, filename)
                self.templates[name] = template_path

    def locate(
        self,
        element_name,
        image=None,
        use_template=True,
        use_color=True,
        use_fallback=True,
        fallback_pos=None,
    ):
        """
        智能定位元素

        Args:
            element_name: 元素名称（如 "like_button", "comment_button"）
            image: 截图（如果为None会自动截取）
            use_template: 是否使用模板匹配
            use_color: 是否使用颜色检测
            use_fallback: 是否使用相对坐标回退
            fallback_pos: 回退的相对坐标 (rel_x, rel_y)

        Returns:
            success: bool
            rel_x, rel_y: 相对坐标
            method: str - 使用的定位方法
        """
        import win32gui

        if image is None:
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top
            from PIL import Image, ImageGrab

            img = ImageGrab.grab((left, top, right, bottom))
            img_np = np.array(img)
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = img_np[:, :, :3]
            if CV2_AVAILABLE:
                image = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            else:
                image = img_np

        if use_template and element_name in self.templates:
            found, rx, ry, info = find_element_by_template(
                image, self.templates[element_name], threshold=0.6
            )
            if found:
                return True, rx, ry, "template"

        if use_color and element_name in [
            "like_button",
            "comment_button",
            "share_button",
        ]:
            found, rx, ry, _ = self._locate_by_color(image, element_name)
            if found:
                return True, rx, ry, "color"

        if use_fallback and fallback_pos:
            return True, fallback_pos[0], fallback_pos[1], "fallback"

        return False, 0, 0, None

    def _locate_by_color(self, image, element_name):
        """
        通过颜色特征定位元素

        Args:
            image: BGR图像
            element_name: 元素名称

        Returns:
            found, rel_x, rel_y, info
        """
        h, w = image.shape[:2]

        color_ranges = {
            "like_button": [
                (np.array([0, 200, 200]), np.array([10, 255, 255]))
            ],  # 红色
            "comment_button": [
                (np.array([80, 100, 100]), np.array([100, 255, 255]))
            ],  # 蓝色
            "share_button": [
                (np.array([0, 150, 150]), np.array([20, 255, 255]))
            ],  # 橙红色
        }

        if element_name not in color_ranges:
            return False, 0, 0, {}

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

        for lower, upper in color_ranges[element_name]:
            mask |= cv2.inRange(hsv, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, cw, ch = cv2.boundingRect(largest)
            if cw * ch > 100:
                center_x = (x + cw / 2) / w
                center_y = (y + ch / 2) / h
                return True, center_x, center_y, {"area": cw * ch}

        return False, 0, 0, {}

    def locate_click(self, element_name, retry=2):
        """
        定位并点击元素

        Args:
            element_name: 元素名称
            retry: 重试次数

        Returns:
            success: bool
        """
        import win32gui

        for i in range(retry):
            success, rx, ry, method = self.locate(element_name)
            if success:
                left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                width = right - left
                height = bottom - top
                abs_x = int(left + rx * width)
                abs_y = int(top + ry * height)

                from .utils import Click

                Click(abs_x, abs_y)
                time.sleep(0.2)
                return True

            time.sleep(0.3)

        return False


# ==================== 私信消息处理 ====================


def detect_background_region(image):
    """
    检测消息内容区域（所有消息气泡的包围盒）

    原理：基于特定颜色检测
    - 背景色：RGB(38, 38, 50) -> BGR(50, 38, 38)
    - 对方消息框：RGB(66, 66, 76) -> BGR(76, 66, 66)
    - 我的消息框：RGB(41, 141, 255) -> BGR(255, 141, 41)

    检测整个区域中的消息气泡（适用于私信聊天框主区域截图）

    Args:
        image: BGR 格式图像

    Returns:
        None: 未检测到有效区域
        (left, top, right, bottom): 相对坐标框 (0-1)
    """
    if image is None or not CV2_AVAILABLE:
        return None

    h, w = image.shape[:2]
    if h <= 0 or w <= 0:
        return None

    opponent_color_bgr = np.array([76, 66, 66], dtype=np.uint8)
    my_color_bgr = np.array([255, 141, 41], dtype=np.uint8)
    tolerance = 20

    opponent_lower = np.array(
        [max(0, c - tolerance) for c in opponent_color_bgr], dtype=np.uint8
    )
    opponent_upper = np.array(
        [min(255, c + tolerance) for c in opponent_color_bgr], dtype=np.uint8
    )
    opponent_mask = cv2.inRange(image, opponent_lower, opponent_upper)

    my_lower = np.array([max(0, c - tolerance) for c in my_color_bgr], dtype=np.uint8)
    my_upper = np.array([min(255, c + tolerance) for c in my_color_bgr], dtype=np.uint8)
    my_mask = cv2.inRange(image, my_lower, my_upper)

    message_mask = cv2.bitwise_or(opponent_mask, my_mask)

    kernel = np.ones((3, 3), np.uint8)
    message_mask = cv2.morphologyEx(message_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        message_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    bubble_rects = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch

        if cw < w * 0.1 or ch < h * 0.05:
            continue
        aspect_ratio = cw / ch if ch > 0 else 0
        if 0.3 < aspect_ratio < 10.0:
            bubble_rects.append((x, y, cw, ch, area))

    if not bubble_rects:
        return None

    min_x = min(r[0] for r in bubble_rects)
    min_y = min(r[1] for r in bubble_rects)
    max_x = max(r[0] + r[2] for r in bubble_rects)
    max_y = max(r[1] + r[3] for r in bubble_rects)

    if (max_x - min_x) > w * 0.2 and (max_y - min_y) > h * 0.15:
        left = max(0, min_x) / w
        top = max(0, min_y) / h
        right = min(w, max_x) / w
        bottom = min(h, max_y) / h
        return (left, top, right, bottom)

    return None


def detect_message_box(image, debug=False):
    """
    通过颜色检测定位所有消息气泡框

    原理:
    - 对方消息框：RGB(66, 66, 76) -> BGR(76, 66, 66), 用绿色框标记
    - 我的消息框：RGB(41, 141, 255) -> BGR(255, 141, 41), 用红色框标记

    Args:
        image: BGR 格式图像
        debug: 是否返回调试图像

    Returns:
        dict: {
            "box": (x1, y1, x2, y2),
            "left": float, "right": float, "top": float, "bottom": float,
            "bubbles": list of bubble dicts,
            "debug_image": img or None
        }
    """
    if not CV2_AVAILABLE or image is None:
        return {
            "box": (0, 0, 1, 1),
            "left": 0,
            "right": 1,
            "top": 0,
            "bottom": 1,
            "bubbles": [],
            "debug_image": None,
        }

    h, w = image.shape[:2]

    opponent_color_bgr = np.array([76, 66, 66], dtype=np.uint8)
    my_color_bgr = np.array([255, 141, 41], dtype=np.uint8)
    tolerance = 20

    opponent_lower = np.array(
        [max(0, c - tolerance) for c in opponent_color_bgr], dtype=np.uint8
    )
    opponent_upper = np.array(
        [min(255, c + tolerance) for c in opponent_color_bgr], dtype=np.uint8
    )
    opponent_mask = cv2.inRange(image, opponent_lower, opponent_upper)

    my_lower = np.array([max(0, c - tolerance) for c in my_color_bgr], dtype=np.uint8)
    my_upper = np.array([min(255, c + tolerance) for c in my_color_bgr], dtype=np.uint8)
    my_mask = cv2.inRange(image, my_lower, my_upper)

    kernel = np.ones((3, 3), np.uint8)
    opponent_mask = cv2.morphologyEx(opponent_mask, cv2.MORPH_CLOSE, kernel)
    my_mask = cv2.morphologyEx(my_mask, cv2.MORPH_CLOSE, kernel)

    opponent_contours, _ = cv2.findContours(
        opponent_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    my_contours, _ = cv2.findContours(
        my_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    bubbles = []

    for cnt in opponent_contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw < w * 0.1 or ch < h * 0.05:
            continue
        aspect_ratio = cw / ch if ch > 0 else 0
        if 0.3 < aspect_ratio < 10.0:
            bubbles.append(
                {
                    "box": (x / w, y / h, (x + cw) / w, (y + ch) / h),
                    "is_self": False,
                    "pixel_box": (x, y, x + cw, y + ch),
                }
            )

    for cnt in my_contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw < w * 0.1 or ch < h * 0.05:
            continue
        aspect_ratio = cw / ch if ch > 0 else 0
        if 0.3 < aspect_ratio < 10.0:
            bubbles.append(
                {
                    "box": (x / w, y / h, (x + cw) / w, (y + ch) / h),
                    "is_self": True,
                    "pixel_box": (x, y, x + cw, y + ch),
                }
            )

    all_boxes = [b["box"] for b in bubbles]
    if all_boxes:
        left = min(b[0] for b in all_boxes)
        top = min(b[1] for b in all_boxes)
        right = max(b[2] for b in all_boxes)
        bottom = max(b[3] for b in all_boxes)
    else:
        left, top, right, bottom = 0, 0, 1, 1

    debug_image = None
    if debug:
        debug_image = image.copy()
        for bubble in bubbles:
            x1, y1, x2, y2 = bubble["pixel_box"]
            color = (0, 255, 0) if not bubble["is_self"] else (0, 0, 255)
            cv2.rectangle(debug_image, (x1, y1), (x2, y2), color, 2)

    return {
        "box": (left, top, right, bottom),
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "bubbles": bubbles,
        "debug_image": debug_image,
    }


def extract_messages_from_box(
    image, box, bubbles=None, debug=False, screenshots_dir=None
):
    """
    从消息框内提取消息 (使用 OCR)

    原理:
    1. 裁剪消息框区域
    2. OCR 识别所有文字
    3. 根据文字 x 位置区分发送者:
       - 左侧 ≈ 对方消息
       - 右侧 ≈ 自己消息
    4. 按 y 位置排序返回

    Args:
        image: BGR 格式图像
        box: 消息框位置 (x1, y1, x2, y2) 相对坐标
        debug: 是否返回调试图像
        screenshots_dir: 气泡框截图保存目录

    Returns:
        list: [{"text": "文字", "is_self": False, "y": 0.5, "sender": "对方"}, ...]
    """
    if image is None:
        return []

    h, w = image.shape[:2]
    x1, y1, x2, y2 = box
    x1, y1, x2, y2 = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)

    if x1 >= x2 or y1 >= y2:
        return []

    msg_roi = image[y1:y2, x1:x2]
    roi_h, roi_w = msg_roi.shape[:2]

    if roi_h <= 0 or roi_w <= 0:
        return []

    # 如果有 bubbles 参数，对每个气泡框单独处理
    if bubbles and len(bubbles) > 0:
        return _process_bubbles_separately(image, box, bubbles, screenshots_dir)

    messages = []
    ocr_results = recognize_text(msg_roi, lang="cn")

    if OCR_AVAILABLE and ocr_results is not None:
        roi_center_x = roi_w / 2

        for item in ocr_results:
            if not isinstance(item, dict):
                continue

            text = item.get("text", "").strip()
            bbox = item.get("bbox", [])

            if not text:
                continue

            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                if isinstance(bbox[0], (list, tuple)):
                    x_min = min(p[0] for p in bbox)
                    x_max = max(p[0] for p in bbox)
                    y_min = min(p[1] for p in bbox)
                    y_max = max(p[1] for p in bbox)
                else:
                    x_min, y_min, x_max, y_max = bbox[0], bbox[1], bbox[2], bbox[3]

                x_center_roi = (x_min + x_max) / 2
                y_center_roi = (y_min + y_max) / 2
            else:
                continue

            abs_x = x1 + x_center_roi
            abs_y = y1 + y_center_roi

            rel_y = abs_y / h

            is_self = x_center_roi > roi_center_x
            sender = "我" if is_self else "对方"

            messages.append(
                {
                    "text": text,
                    "is_self": is_self,
                    "y": rel_y,
                    "sender": sender,
                    "bbox": [
                        [x1 + x_min, y1 + y_min],
                        [x1 + x_max, y1 + y_min],
                        [x1 + x_max, y1 + y_max],
                        [x1 + x_min, y1 + y_max],
                    ],
                }
            )

        messages.sort(key=lambda x: x["y"])

    debug_image = None
    if debug and messages:
        debug_image = image.copy()
        for i, msg in enumerate(messages):
            x_pos = (
                int(x1 + (x2 - x1) * 0.8)
                if msg["is_self"]
                else int(x1 + (x2 - x1) * 0.2)
            )
            y_pos = int(msg["y"] * h)
            color = (0, 255, 0) if msg["is_self"] else (0, 0, 255)
            cv2.putText(
                debug_image,
                "%d" % (i + 1),
                (x_pos, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2,
            )

    return messages


def _process_bubbles_separately(image, box, bubbles, screenshots_dir):
    """
    对每个气泡框单独截取并扩展到 400x400
    """
    h, w = image.shape[:2]
    messages = []

    print("    检测到 %d 个气泡框，分别进行 OCR 识别..." % len(bubbles))

    for idx, bubble in enumerate(bubbles):
        bubble_box = bubble.get("pixel_box")
        is_self = bubble.get("is_self", False)

        if not bubble_box:
            continue

        bx1, by1, bx2, by2 = bubble_box

        # 1. 先从原图截取气泡框内容
        bubble_crop = image[by1:by2, bx1:bx2]

        if bubble_crop.size == 0:
            continue

        crop_h, crop_w = bubble_crop.shape[:2]

        # 2. 将截取的图片统一扩展到 400x400
        target_size = 400
        bubble_roi = np.zeros((target_size, target_size, 3), dtype=np.uint8)

        # 计算居中位置
        start_x = (target_size - crop_w) // 2
        start_y = (target_size - crop_h) // 2

        # 将截取的气泡框放到 400x400 黑色背景中央
        bubble_roi[start_y : start_y + crop_h, start_x : start_x + crop_w] = bubble_crop

        # 保存统一尺寸的气泡框图片
        if screenshots_dir:
            try:
                bubble_image_path = os.path.join(
                    screenshots_dir,
                    "bubble_%d_%s_%s.png"
                    % (
                        idx,
                        "self" if is_self else "opp",
                        time.strftime("%Y%m%d_%H%M%S"),
                    ),
                )
                cv2.imwrite(bubble_image_path, bubble_roi)
                print(
                    "    气泡框 %d 已保存：%s (统一尺寸：400x400，原始尺寸：%dx%d)"
                    % (idx + 1, bubble_image_path, crop_w, crop_h)
                )
            except Exception as e:
                print("    保存气泡框 %d 图片失败：%s" % (idx + 1, e))

        # OCR 识别
        text = ""
        try:
            ocr_results = recognize_text(bubble_roi, lang="cn")
            if ocr_results and len(ocr_results) > 0:
                texts = [
                    r.get("text", "").strip() for r in ocr_results if r.get("text")
                ]
                text = " ".join(texts)
                print("    气泡框 %d 识别结果：%s" % (idx + 1, text))
        except Exception as e:
            print("    气泡框 %d OCR 识别失败：%s" % (idx + 1, e))

        by_center = (by1 + by2) / 2

        messages.append(
            {
                "text": text if text else "(未识别到文字)",
                "is_self": is_self,
                "y": by_center / h,
                "sender": "我" if is_self else "对方",
                "bubble_box": (bx1, by1, bx2, by2),
                "bubble_index": idx,
            }
        )

    messages.sort(key=lambda x: x["y"])

    if screenshots_dir:
        print("    共保存 %d 个气泡框图片到 screenshots 目录" % len(bubbles))

    return messages

    """
    根据已知位置获取消息框坐标（使用positions.txt的配置）

    Returns:
        tuple: (x1, y1, x2, y2) 相对坐标
    """
    try:
        from .positions import POSITIONS
    except ImportError:
        POSITIONS = {}

    if (
        "打开好友的私信窗口左上角" in POSITIONS
        and "打开好友的私信窗口右下角" in POSITIONS
    ):
        x1, y1 = POSITIONS["打开好友的私信窗口左上角"]
        x2, y2 = POSITIONS["打开好友的私信窗口右下角"]
        return (x1, y1, x2, y2)

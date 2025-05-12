import os
import io
from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# --- 常量设置 ---
# 在 Serverless 环境中，文件路径需要相对于当前脚本或使用绝对路径
# 假设 base.png 和 STXINWEI.TTF 在项目的根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # api 目录的上一级就是项目根目录

BASE_IMAGE_PATH = os.path.join(PROJECT_ROOT, "base.png")
FONT_PATH = os.path.join(PROJECT_ROOT, "STXINWEI.TTF")
FONT_COLOR = "#4B71A7"
TEXT_RECT = (235, 1004, 981, 1245)  # 文本区域 (x1, y1, x2, y2)

# --- Helper Functions (从原脚本复制并稍作修改) ---


def get_adaptive_font(
    text, font_path, rect_coords, max_font_size=200, min_font_size=50
):
    """根据文本和矩形区域动态计算合适的字体大小"""
    x1, y1, x2, y2 = rect_coords
    width = x2 - x1
    height = y2 - y1
    font_size = max_font_size
    font = None

    # 尝试找到适合的最大字体大小
    while font_size >= min_font_size:
        try:
            font = ImageFont.truetype(font_path, font_size)
            # 使用 getbbox 获取更准确的边界框
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]  # 高度是 bbox[3] - bbox[1]
            tolerance = 5  # 允许一些像素容差
            if text_width <= (width - tolerance) and text_height <= (
                height - tolerance
            ):
                return font  # 找到合适的字体
        except IOError:
            print(f"警告：无法加载字体 {font_path}。")
            # 如果字体文件加载失败，尝试使用默认字体，并立即返回
            try:
                return ImageFont.load_default()
            except IOError:  # 连默认字体都加载失败的情况（不太可能）
                raise RuntimeError("无法加载字体文件，也无法加载默认字体。")
        except Exception as e:
            print(f"计算字体大小时出错: {e}")
            # 如果计算出错，可以认为当前size不合适，继续尝试更小的
        font_size -= 1

    # 如果循环结束仍未找到合适的字体（即文本在最小字号下也放不下）
    # 或者在循环中字体加载成功但在min_font_size时才满足条件
    # 返回最小允许字号的字体对象
    try:
        print(
            f"警告：文本 '{text}' 在指定区域内可能无法完全容纳，使用最小字号 {min_font_size}。"
        )
        return ImageFont.truetype(font_path, min_font_size)
    except IOError:
        print(f"警告：无法加载字体 {font_path}（使用最小尺寸）。将使用默认字体。")
        try:
            return ImageFont.load_default()
        except IOError:
            raise RuntimeError("无法加载字体文件，也无法加载默认字体。")


def generate_single_image(name, base_image_path, font_path, color, text_rect_coords):
    """为单个名字生成图片，并返回图片对象"""
    try:
        img = Image.open(base_image_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        font = get_adaptive_font(name, font_path, text_rect_coords)

        # 使用 getbbox 获取文本边界框以精确计算位置
        bbox = font.getbbox(name)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]  # 实际渲染高度

        x1, y1, x2, y2 = text_rect_coords
        rect_width = x2 - x1
        rect_height = y2 - y1

        # 计算居中对齐的坐标
        x = x1 + (rect_width - text_width) / 2
        # Pillow的 draw.text 的 y 坐标是文本基线(baseline)的位置。
        # bbox[1] 是从字体顶部到基线的距离（对于大部分字体是负数或0）。
        # 为了视觉上垂直居中，我们需要考虑文本的实际高度和基线位置。
        # (rect_height - text_height) / 2 是文本框顶部的偏移量。
        # y = y1 + (rect_height - text_height) / 2 - bbox[1]
        # 更简单的方式是使用 textbbox 获取绘制后的实际边界框来居中
        # 但 getbbox 已经提供了足够的信息
        # 调整 y 坐标使其在垂直方向居中
        y = y1 + (rect_height - text_height) / 2 - bbox[1]

        draw.text((x, y), name, font=font, fill=color)
        return img

    except FileNotFoundError:
        raise FileNotFoundError(
            f"错误：找不到必要的文件。请确保 '{base_image_path}' 和 '{font_path}' 存在。"
        )
    except Exception as e:
        raise RuntimeError(f"生成图片时出错: {e}")


# --- Flask API Route ---
@app.route("/api/generate", methods=["POST"])
def handle_generate():
    """处理生成图片的请求"""
    if not request.is_json:
        return jsonify({"error": "请求必须是 JSON"}), 400

    data = request.get_json()
    name = data.get("name")

    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "缺少 'name' 参数或参数无效"}), 400

    name = name.strip()

    try:
        # 生成图片
        img = generate_single_image(
            name, BASE_IMAGE_PATH, FONT_PATH, FONT_COLOR, TEXT_RECT
        )

        # 将图片保存到内存中的字节流
        img_io = io.BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)  # 重置流的位置到开头

        # 返回图片文件
        return send_file(
            img_io,
            mimetype="image/png",
            as_attachment=False,  # 在浏览器中直接显示，而不是作为附件下载
            download_name=f"{name}.png",  # 浏览器保存时建议的文件名
        )

    except FileNotFoundError as e:
        print(f"文件未找到错误: {e}")
        return jsonify({"error": str(e)}), 500
    except RuntimeError as e:
        print(f"运行时错误: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"未知错误: {e}")
        return jsonify({"error": "生成图片时发生内部错误"}), 500


# Vercel 会自动处理运行 Flask app，不需要 app.run()
# 如果在本地测试，可以取消下面这行的注释：
# if __name__ == "__main__":
#     app.run(debug=True)

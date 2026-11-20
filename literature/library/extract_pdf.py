"""
PDF 内容提取工具
================
提取 PDF 中的文字、图片、结构信息（标题/段落/表格/公式区域），
并将结果保存为结构化的文本文件和图片文件夹，方便后续阅读分析。

依赖: pip install PyMuPDF Pillow
用法: python extract_pdf.py <pdf_path> [--output_dir <output_dir>]
"""

import fitz  # PyMuPDF
import os
import re
import json
import argparse
from collections import OrderedDict


def extract_pdf(pdf_path: str, output_dir: str = None) -> dict:
    """
    从 PDF 文件中提取全部内容，包括：
    - 逐页文本（保留结构）
    - 逐页图片（保存为文件）
    - 文档元信息（标题、作者、页数等）
    - 结构信息（字体大小分析 -> 推断标题/正文层级）
    - 表格区域检测（基于线条分析）
    
    参数:
        pdf_path: PDF 文件路径
        output_dir: 输出目录，默认为 PDF 同目录下的 <pdf名>_extracted/
    
    返回:
        包含所有提取内容的字典
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    doc = fitz.open(pdf_path)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(pdf_path), f"{pdf_name}_extracted")
    
    os.makedirs(output_dir, exist_ok=True)
    img_dir = os.path.join(output_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    result = {
        "meta": _extract_metadata(doc, pdf_path),
        "pages": [],
        "images": [],
        "structure": {},
    }

    all_font_sizes = []
    
    # ========== 逐页提取 ==========
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_data = _extract_page(doc, page, page_idx, img_dir, all_font_sizes)
        result["pages"].append(page_data)
        result["images"].extend(page_data.get("images", []))
    
    # ========== 分析全局结构 ==========
    result["structure"] = _analyze_structure(all_font_sizes, result["pages"])
    
    # ========== 保存结果 ==========
    _save_full_text(result, output_dir, pdf_name)
    _save_structured_text(result, output_dir, pdf_name)
    _save_summary(result, output_dir, pdf_name)
    report_path = _save_report(result, output_dir, pdf_name)
    
    doc.close()
    
    print(f"\n{'='*60}")
    print(f"提取完成！")
    print(f"  PDF:      {pdf_path}")
    print(f"  总页数:   {result['meta']['page_count']}")
    print(f"  提取图片: {len(result['images'])} 张")
    print(f"  输出目录: {output_dir}")
    print(f"{'='*60}")
    print(f"输出文件:")
    print(f"  {pdf_name}_report.md         - ★ 综合报告（一体化，推荐阅读）")
    print(f"  {pdf_name}_fulltext.txt      - 纯文本（带页码标记）")
    print(f"  {pdf_name}_structured.txt    - 结构化文本（含标题层级、图片位置标注）")
    print(f"  {pdf_name}_summary.json      - 元信息和结构摘要（JSON）")
    print(f"  images/                      - 提取的图片")
    print(f"{'='*60}")
    print(f"\n★ 综合报告路径: {report_path}")
    
    return result


def _extract_metadata(doc, pdf_path: str) -> dict:
    """提取 PDF 元信息"""
    meta = doc.metadata or {}
    return {
        "file": os.path.basename(pdf_path),
        "page_count": len(doc),
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "subject": meta.get("subject", ""),
        "creator": meta.get("creator", ""),
        "producer": meta.get("producer", ""),
        "creation_date": meta.get("creationDate", ""),
        "mod_date": meta.get("modDate", ""),
    }


def _extract_page(doc, page, page_idx: int, img_dir: str, all_font_sizes: list) -> dict:
    """提取单页内容：文本块、图片、表格线条"""
    page_data = {
        "page_num": page_idx + 1,
        "width": page.rect.width,
        "height": page.rect.height,
        "text": "",
        "text_blocks": [],
        "images": [],
        "drawings": [],
    }

    # ----- 1. 提取文本（按块，保留位置和字体信息）-----
    text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    page_text_lines = []
    
    for block in text_dict.get("blocks", []):
        if block["type"] == 0:  # 文本块
            block_info = {
                "type": "text",
                "bbox": list(block["bbox"]),
                "lines": [],
            }
            for line in block.get("lines", []):
                line_text = ""
                line_fonts = []
                for span in line.get("spans", []):
                    line_text += span["text"]
                    font_info = {
                        "text": span["text"],
                        "font": span["font"],
                        "size": round(span["size"], 1),
                        "color": span["color"],
                        "bold": "Bold" in span["font"] or "bold" in span["font"].lower(),
                        "italic": "Italic" in span["font"] or "italic" in span["font"].lower(),
                    }
                    line_fonts.append(font_info)
                    if span["text"].strip():
                        all_font_sizes.append(round(span["size"], 1))
                
                block_info["lines"].append({
                    "text": line_text,
                    "bbox": list(line["bbox"]),
                    "spans": line_fonts,
                })
                page_text_lines.append(line_text)
            
            page_data["text_blocks"].append(block_info)
        
        elif block["type"] == 1:  # 图片块
            page_data["text_blocks"].append({
                "type": "image_placeholder",
                "bbox": list(block["bbox"]),
            })
    
    page_data["text"] = "\n".join(page_text_lines)
    
    # ----- 2. 提取图片 -----
    page_data["images"] = _extract_images(doc, page, page_idx, img_dir)
    
    # ----- 3. 提取矢量图形/线条（用于表格检测）-----
    page_data["drawings"] = _extract_drawings(page)
    
    return page_data


def _extract_images(doc, page, page_idx: int, img_dir: str) -> list:
    """提取页面中的所有图片并保存"""
    images = []
    img_list = page.get_images(full=True)
    
    for img_idx, img_info in enumerate(img_list):
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            if base_image:
                img_ext = base_image.get("ext", "png")
                img_bytes = base_image["image"]
                img_width = base_image.get("width", 0)
                img_height = base_image.get("height", 0)
                
                # 跳过太小的图片（可能是装饰元素）
                if img_width < 20 or img_height < 20:
                    continue
                
                img_filename = f"page{page_idx + 1}_img{img_idx + 1}.{img_ext}"
                img_path = os.path.join(img_dir, img_filename)
                
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                
                # 尝试获取图片在页面上的位置
                img_rects = page.get_image_rects(xref)
                bbox = None
                if img_rects:
                    r = img_rects[0]
                    bbox = [r.x0, r.y0, r.x1, r.y1]
                
                images.append({
                    "page": page_idx + 1,
                    "index": img_idx + 1,
                    "filename": img_filename,
                    "path": img_path,
                    "width": img_width,
                    "height": img_height,
                    "format": img_ext,
                    "size_bytes": len(img_bytes),
                    "bbox": bbox,
                })
        except Exception as e:
            print(f"  [警告] 提取图片失败 (page {page_idx+1}, img {img_idx+1}): {e}")
    
    return images


def _extract_drawings(page) -> list:
    """提取页面中的矢量绘图（线条、矩形等），用于辅助检测表格"""
    drawings = []
    try:
        paths = page.get_drawings()
        lines = []
        rects = []
        for path in paths:
            for item in path.get("items", []):
                if item[0] == "l":  # 线段
                    lines.append({
                        "type": "line",
                        "start": [item[1].x, item[1].y],
                        "end": [item[2].x, item[2].y],
                    })
                elif item[0] == "re":  # 矩形
                    rects.append({
                        "type": "rect",
                        "bbox": [item[1].x0, item[1].y0, item[1].x1, item[1].y1],
                    })
        
        if lines or rects:
            drawings.append({
                "line_count": len(lines),
                "rect_count": len(rects),
                "has_table_like_structure": len(lines) > 4 or len(rects) > 2,
            })
    except Exception:
        pass
    
    return drawings


def _analyze_structure(all_font_sizes: list, pages: list) -> dict:
    """根据字体大小频率分析文档结构层级"""
    if not all_font_sizes:
        return {"body_size": 0, "heading_sizes": [], "levels": {}}
    
    # 统计字体大小频率
    size_freq = {}
    for s in all_font_sizes:
        size_freq[s] = size_freq.get(s, 0) + 1
    
    # 正文字体 = 出现频率最高的字体大小
    body_size = max(size_freq, key=size_freq.get)
    
    # 比正文大的字体视为标题
    heading_sizes = sorted([s for s in size_freq if s > body_size], reverse=True)
    
    # 构建层级映射
    levels = {}
    for i, size in enumerate(heading_sizes):
        levels[size] = {
            "level": i + 1,
            "count": size_freq[size],
            "role": f"heading_level_{i+1}",
        }
    levels[body_size] = {
        "level": len(heading_sizes) + 1,
        "count": size_freq[body_size],
        "role": "body_text",
    }
    
    # 提取标题列表
    headings = []
    for page_data in pages:
        for block in page_data.get("text_blocks", []):
            if block.get("type") != "text":
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span["size"] > body_size and span["text"].strip():
                        headings.append({
                            "page": page_data["page_num"],
                            "text": span["text"].strip(),
                            "size": span["size"],
                            "level": next(
                                (levels[s]["level"] for s in levels if s == span["size"]),
                                99
                            ),
                            "bold": span["bold"],
                        })
    
    return {
        "body_font_size": body_size,
        "heading_font_sizes": heading_sizes,
        "font_size_distribution": dict(sorted(size_freq.items(), reverse=True)),
        "levels": {str(k): v for k, v in levels.items()},
        "headings": headings,
    }


def _save_full_text(result: dict, output_dir: str, pdf_name: str):
    """保存纯文本版本（带页码标记）"""
    filepath = os.path.join(output_dir, f"{pdf_name}_fulltext.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        for page_data in result["pages"]:
            f.write(f"\n{'='*60}\n")
            f.write(f"=== PAGE {page_data['page_num']} ===\n")
            f.write(f"{'='*60}\n\n")
            f.write(page_data["text"])
            f.write("\n")
    print(f"  已保存: {filepath}")


def _save_structured_text(result: dict, output_dir: str, pdf_name: str):
    """保存结构化文本（含标题层级标注、图片位置标注）"""
    filepath = os.path.join(output_dir, f"{pdf_name}_structured.txt")
    body_size = result["structure"].get("body_font_size", 0)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"文档: {result['meta']['file']}\n")
        f.write(f"页数: {result['meta']['page_count']}\n")
        f.write(f"图片: {len(result['images'])} 张\n")
        f.write(f"正文字体大小: {body_size}\n")
        f.write(f"\n{'='*60}\n")
        f.write(f"目录结构（根据字体大小推断）:\n")
        f.write(f"{'='*60}\n\n")
        
        for h in result["structure"].get("headings", []):
            indent = "  " * (h["level"] - 1)
            f.write(f"{indent}[L{h['level']}] (p.{h['page']}) {h['text']}\n")
        
        f.write(f"\n{'='*60}\n")
        f.write(f"正文（含结构标注）:\n")
        f.write(f"{'='*60}\n\n")
        
        for page_data in result["pages"]:
            f.write(f"\n--- PAGE {page_data['page_num']} ---\n\n")
            
            # 收集本页图片位置信息
            page_images = [img for img in result["images"] if img["page"] == page_data["page_num"]]
            
            for block in page_data.get("text_blocks", []):
                if block.get("type") == "image_placeholder":
                    bbox = block.get("bbox", [])
                    # 找到对应图片
                    matched = _find_image_at(page_images, bbox)
                    if matched:
                        f.write(f"\n  [图片: {matched['filename']} ({matched['width']}x{matched['height']})]\n\n")
                    else:
                        f.write(f"\n  [图片区域: bbox={bbox}]\n\n")
                    continue
                
                if block.get("type") != "text":
                    continue
                    
                for line in block.get("lines", []):
                    text = line["text"].strip()
                    if not text:
                        continue
                    
                    # 判断是否为标题
                    max_size = max((s["size"] for s in line.get("spans", []) if s["text"].strip()), default=0)
                    if max_size > body_size:
                        level = _get_heading_level(max_size, result["structure"])
                        prefix = "#" * level
                        f.write(f"\n{prefix} {text}\n\n")
                    else:
                        f.write(f"{text}\n")
            
            # 在页末列出本页所有图片
            if page_images:
                f.write(f"\n  [本页图片: {', '.join(img['filename'] for img in page_images)}]\n")
    
    print(f"  已保存: {filepath}")


def _save_summary(result: dict, output_dir: str, pdf_name: str):
    """保存元信息和结构摘要为 JSON"""
    filepath = os.path.join(output_dir, f"{pdf_name}_summary.json")
    
    summary = {
        "meta": result["meta"],
        "structure": {
            "body_font_size": result["structure"].get("body_font_size"),
            "heading_font_sizes": result["structure"].get("heading_font_sizes"),
            "font_size_distribution": result["structure"].get("font_size_distribution"),
            "headings": result["structure"].get("headings", []),
        },
        "images": [
            {
                "page": img["page"],
                "filename": img["filename"],
                "width": img["width"],
                "height": img["height"],
                "format": img["format"],
                "size_bytes": img["size_bytes"],
            }
            for img in result["images"]
        ],
        "page_stats": [
            {
                "page": p["page_num"],
                "text_length": len(p["text"]),
                "block_count": len(p["text_blocks"]),
                "image_count": len(p["images"]),
                "has_drawings": len(p["drawings"]) > 0,
            }
            for p in result["pages"]
        ],
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"  已保存: {filepath}")


def _find_image_at(page_images: list, bbox: list) -> dict:
    """根据 bbox 位置匹配图片"""
    if not bbox or not page_images:
        return None
    for img in page_images:
        if img.get("bbox"):
            # 粗略匹配：中心点在 bbox 内
            img_cx = (img["bbox"][0] + img["bbox"][2]) / 2
            img_cy = (img["bbox"][1] + img["bbox"][3]) / 2
            if bbox[0] <= img_cx <= bbox[2] and bbox[1] <= img_cy <= bbox[3]:
                return img
    return page_images[0] if page_images else None


def _get_heading_level(font_size: float, structure: dict) -> int:
    """根据字体大小获取标题层级"""
    levels = structure.get("levels", {})
    info = levels.get(str(font_size))
    if info:
        return info["level"]
    # 找最接近的
    heading_sizes = structure.get("heading_font_sizes", [])
    for i, s in enumerate(heading_sizes):
        if font_size >= s:
            return i + 1
    return len(heading_sizes) + 1


def _save_report(result: dict, output_dir: str, pdf_name: str) -> str:
    """
    生成一体化综合报告（Markdown 格式），包含：
    - 文档元信息
    - 目录结构
    - 全文内容（带标题层级、图片标注、页码标记）
    - 图片汇总
    - 统计信息
    返回报告文件的完整路径。
    """
    filepath = os.path.join(output_dir, f"{pdf_name}_report.md")
    body_size = result["structure"].get("body_font_size", 0)
    
    with open(filepath, "w", encoding="utf-8") as f:
        # ===== 1. 文档元信息 =====
        f.write(f"# 论文综合提取报告: {result['meta']['file']}\n\n")
        f.write(f"---\n\n")
        f.write(f"## 📋 文档元信息\n\n")
        f.write(f"| 属性 | 值 |\n|------|----|\n")
        f.write(f"| 文件名 | {result['meta']['file']} |\n")
        f.write(f"| 总页数 | {result['meta']['page_count']} |\n")
        if result['meta'].get('title'):
            f.write(f"| 标题 | {result['meta']['title']} |\n")
        if result['meta'].get('author'):
            f.write(f"| 作者 | {result['meta']['author']} |\n")
        if result['meta'].get('subject'):
            f.write(f"| 主题 | {result['meta']['subject']} |\n")
        f.write(f"| 创建工具 | {result['meta'].get('creator', 'N/A')} |\n")
        f.write(f"| 图片数量 | {len(result['images'])} |\n")
        f.write(f"| 正文字体大小 | {body_size} |\n")
        f.write(f"\n")
        
        # ===== 2. 目录结构 =====
        headings = result["structure"].get("headings", [])
        if headings:
            f.write(f"## 📑 目录结构\n\n")
            for h in headings:
                indent = "  " * (h["level"] - 1)
                bold = "**" if h.get("bold") else ""
                f.write(f"{indent}- {bold}[L{h['level']}] (p.{h['page']}) {h['text']}{bold}\n")
            f.write(f"\n")
        
        # ===== 3. 图片汇总 =====
        if result["images"]:
            f.write(f"## 🖼️ 图片汇总\n\n")
            f.write(f"| # | 页码 | 文件名 | 尺寸 | 格式 | 大小 |\n")
            f.write(f"|---|------|--------|------|------|------|\n")
            for i, img in enumerate(result["images"], 1):
                size_kb = img['size_bytes'] / 1024
                f.write(f"| {i} | p.{img['page']} | {img['filename']} | {img['width']}x{img['height']} | {img['format']} | {size_kb:.1f}KB |\n")
            f.write(f"\n")
        
        # ===== 4. 各页统计 =====
        f.write(f"## 📊 各页概况\n\n")
        f.write(f"| 页码 | 文本长度 | 文本块数 | 图片数 | 含矢量图 |\n")
        f.write(f"|------|----------|----------|--------|----------|\n")
        for p in result["pages"]:
            has_draw = "✓" if p.get("drawings") else ""
            f.write(f"| {p['page_num']} | {len(p['text'])} | {len(p['text_blocks'])} | {len(p['images'])} | {has_draw} |\n")
        f.write(f"\n")
        
        # ===== 5. 全文内容（核心部分） =====
        f.write(f"---\n\n")
        f.write(f"## 📖 全文内容\n\n")
        
        for page_data in result["pages"]:
            f.write(f"\n---\n### 【第 {page_data['page_num']} 页】\n\n")
            
            page_images = [img for img in result["images"] if img["page"] == page_data["page_num"]]
            used_images = set()
            
            for block in page_data.get("text_blocks", []):
                if block.get("type") == "image_placeholder":
                    bbox = block.get("bbox", [])
                    matched = _find_image_at(page_images, bbox)
                    if matched:
                        used_images.add(matched["filename"])
                        f.write(f"\n> 📷 **[图片: {matched['filename']}]** ({matched['width']}x{matched['height']}, {matched['format']})\n\n")
                    else:
                        f.write(f"\n> 📷 **[图片区域]** (bbox: {bbox})\n\n")
                    continue
                
                if block.get("type") != "text":
                    continue
                
                for line in block.get("lines", []):
                    text = line["text"].strip()
                    if not text:
                        continue
                    
                    # 判断是否为标题
                    max_size = max(
                        (s["size"] for s in line.get("spans", []) if s["text"].strip()),
                        default=0
                    )
                    is_bold = any(s.get("bold") for s in line.get("spans", []) if s["text"].strip())
                    
                    if max_size > body_size:
                        level = _get_heading_level(max_size, result["structure"])
                        # 在报告中使用 h4-h6 避免和报告自身结构冲突
                        md_level = "#" * min(level + 3, 6)
                        f.write(f"\n{md_level} {text}\n\n")
                    elif is_bold and len(text) < 100:
                        # 粗体短文本可能是小标题
                        f.write(f"\n**{text}**\n\n")
                    else:
                        f.write(f"{text}\n")
            
            # 列出本页未在正文中出现的图片
            remaining = [img for img in page_images if img["filename"] not in used_images]
            if remaining:
                f.write(f"\n> 📎 本页附加图片: {', '.join(img['filename'] for img in remaining)}\n\n")
        
        # ===== 6. 字体分析 =====
        f.write(f"\n---\n\n")
        f.write(f"## 🔤 字体大小分布\n\n")
        dist = result["structure"].get("font_size_distribution", {})
        if dist:
            f.write(f"| 字体大小 | 出现次数 | 角色 |\n")
            f.write(f"|----------|----------|------|\n")
            levels = result["structure"].get("levels", {})
            for size, count in sorted(dist.items(), key=lambda x: -float(x[0])):
                role = levels.get(str(size), {}).get("role", "minor")
                f.write(f"| {size} | {count} | {role} |\n")
        
        f.write(f"\n---\n*报告生成完毕*\n")
    
    print(f"  已保存: {filepath}")
    return filepath


# ========== CLI 入口 ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF 内容提取工具")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("--output_dir", "-o", default=None, help="输出目录（默认: <PDF名>_extracted/）")
    args = parser.parse_args()
    
    extract_pdf(args.pdf_path, args.output_dir)

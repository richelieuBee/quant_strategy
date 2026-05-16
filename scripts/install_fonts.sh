#!/bin/bash
# 阿里云ECS中文字体安装脚本

echo "=== 开始安装中文字体 ==="

FONT_DIR="/usr/share/fonts/chinese"
mkdir -p $FONT_DIR

# 字体下载地址（使用多个备用源）
FONT_URLS=(
    "https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansSC.zip"
    "https://noto-website.storage.googleapis.com/files/NotoSansCJKsc-20170602.zip"
)

echo "下载中文字体..."

# 尝试下载
DOWNLOADED=false
for URL in "${FONT_URLS[@]}"; do
    echo "尝试: $URL"
    cd /tmp
    if curl -sL "$URL" -o chinese-font.zip 2>/dev/null; then
        if unzip -q chinese-font.zip -d chinese-font-extract 2>/dev/null; then
            # 查找OTF文件
            OTF_FILE=$(find chinese-font-extract -name "*.otf" 2>/dev/null | head -1)
            if [ -n "$OTF_FILE" ]; then
                cp "$OTF_FILE" "$FONT_DIR/NotoSansCJKsc.otf"
                DOWNLOADED=true
                echo "✓ 字体下载成功: $OTF_FILE"
                break
            fi
        fi
    fi
done

if [ "$DOWNLOADED" = false ]; then
    echo "下载失败，尝试备用方案..."
    # 备用：使用 pip 安装字体
    pip install --target=/tmp/font_temp noto-fonts-ttf 2>/dev/null || true
    find /tmp/font_temp -name "*CJK*.ttf" -o -name "*CJK*.otf" 2>/dev/null | head -1 | xargs -I {} cp {} "$FONT_DIR/NotoSansCJKsc.otf" 2>/dev/null || true
fi

# 检查是否安装成功
if [ -f "$FONT_DIR/NotoSansCJKsc.otf" ]; then
    echo "✓ 字体文件已就绪: $FONT_DIR/NotoSansCJKsc.otf"
    ls -lh "$FONT_DIR/"
else
    echo "✗ 字体安装失败"
    exit 1
fi

# 刷新字体缓存
echo "刷新字体缓存..."
fc-cache -fv $FONT_DIR

# 清除matplotlib缓存
echo "清除matplotlib缓存..."
rm -rf ~/.cache/matplotlib/*

echo ""
echo "=== 安装完成 ==="
echo "请重启服务:"
echo "  scripts/stop_service.sh"
echo "  scripts/start_service.sh"
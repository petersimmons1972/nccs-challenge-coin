#!/bin/bash
# Build NCCS Challenge Coin STL files
# Renders each color layer separately for multi-color printing
# Combined double-sided coin (obverse top, reverse bottom)

set -e
cd "$(dirname "$0")"

BUILD_DIR="build"
SRC_DIR="src"
mkdir -p "$BUILD_DIR"

echo "=== NCCS Challenge Coin Build ==="
echo ""

# Render combined coin - 4 color layers
echo "--- Combined Double-Sided Coin ---"
for color in 1 2 3 4; do
    case $color in
        1) name="navy" ;;
        2) name="gray" ;;
        3) name="carolina" ;;
        4) name="white" ;;
    esac
    echo "  Rendering coin_${name}.stl (color $color)..."
    openscad -o "$BUILD_DIR/coin_${name}.stl" \
        -D "COLOR=$color" \
        "$SRC_DIR/coin.scad" 2>/dev/null
done

# Render preview (all colors)
echo "  Rendering coin_preview.stl..."
openscad -o "$BUILD_DIR/coin_preview.stl" \
    -D "COLOR=0" \
    "$SRC_DIR/coin.scad" 2>/dev/null

# Render preview images
echo ""
echo "--- Preview Images ---"
echo "  Top view..."
openscad -o "$BUILD_DIR/coin_top.png" \
    --camera=0,0,0,0,0,0,120 --projection=ortho \
    --imgsize=800,800 \
    -D "COLOR=0" \
    "$SRC_DIR/coin.scad" 2>/dev/null

echo "  Bottom view (coin-turn flip)..."
openscad -o "$BUILD_DIR/coin_bottom.png" \
    --camera=0,0,0,0,180,0,120 --projection=ortho \
    --imgsize=800,800 \
    -D "COLOR=0" \
    "$SRC_DIR/coin.scad" 2>/dev/null

echo ""
echo "=== Build Complete ==="
echo ""
echo "Output files in $BUILD_DIR/:"
ls -la "$BUILD_DIR/"*.stl "$BUILD_DIR/"*.png 2>/dev/null
echo ""
echo "Next: Run 'python3 create_3mf.py' to package for Bambu Studio"

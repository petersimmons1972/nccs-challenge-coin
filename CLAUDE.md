# NCCS Challenge Coin — Claude Instructions

## Stack
- **CAD**: OpenSCAD (`src/coin.scad`) with `COLOR` parameter (0=preview, 1–4=per color)
- **Slicer**: Bambu Studio 02.05.00.66 on Bambu P1S + AMS Pro 2
- **Build**: `./build.sh` → STLs; `python3 create_3mf.py` → 3MF
- **Tests**: `python3 -m pytest test_3mf.py -v` (18 tests, always green before commit)

## AMS Slot Color Convention
| Slot | Color | Hex | Notes |
|---|---|---|---|
| 1 | Navy Blue | #1B3B60 | Rim, diamond, swimmer |
| 2 | Dark Gray | #999DA2 | Accent ring — swap gold anytime |
| 3 | Carolina Blue | #8BD1EE | Inner field |
| 4 | White | #FFFFFF | Letters + arc text |

## Key Rules
- **Zero mesh overlap** — each color layer is geometrically exclusive
- **Carolina/base uses `difference()`** to subtract all other color shapes
- **Bottom face wrapped in `mirror([1,0,0])`** — reads correctly when flipped
- **TDD first** — write failing test before changing `create_3mf.py` format
- See `~/projects/3dprint/lessons/` for full Bambu 3MF spec and patterns

## Workflow
1. Edit `src/coin.scad`
2. `./build.sh` to export STLs + preview PNGs
3. `python3 create_3mf.py` to package 3MF
4. `python3 -m pytest test_3mf.py -v` to verify
5. Open `build/NCCS_Challenge_Coin.3mf` in Bambu Studio to confirm

## Version History
- v1–v2: Two separate prints (obverse + reverse) glued together
- v3: Single double-sided print; 4-color native Bambu 3MF; swimmer in navy

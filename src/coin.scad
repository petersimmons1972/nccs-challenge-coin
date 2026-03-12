// NCCS Swim Team Challenge Coin - DOUBLE-SIDED
// Single print, no glue. Bambu P1S + AMS Pro 2 (4 colors)
//
// Top = Obverse (NCC shield logo)
// Bottom = Reverse (swimmer + arc text)
//
// IMPORTANT: Each color part has NO overlap with any other.
// Carolina blue base has all other colors subtracted from it.
//
// COLOR selects which filament layer to render:
//   0 = All (preview)
//   1 = Navy Blue (#1B3B60)
//   2 = Dark Gray (#999DA2) - accent ring only
//   3 = Carolina Blue (#8BD1EE)
//   4 = White (#FFFFFF)

COLOR = 0;

// === DIMENSIONS ===
coin_d = 50;
total_h = 5.0;       // Total coin thickness
rim_w = 2.5;
accent_w = 0.6;
relief = 0.6;        // Height of raised/recessed details

// Derived
inner_r = coin_d/2 - rim_w;
field_r = inner_r - accent_w;
text_r = field_r - 2;

// Logo scale (accounts for OpenSCAD 96 DPI SVG import)
logo_scale = 1.18;

// === COLORS ===
navy = [0.106, 0.231, 0.376];
gray = [0.6, 0.616, 0.635];
carolina = [0.545, 0.820, 0.933];
white_c = [1.0, 1.0, 1.0];

// === TEXT MODULES ===
module arc_text(str, radius, size, start_angle, char_angle) {
    for (i = [0:len(str)-1]) {
        angle = start_angle - i * char_angle;
        rotate([0, 0, angle])
            translate([0, radius, 0])
                text(str[i], size=size, font="Arial:style=Bold",
                     halign="center", valign="center");
    }
}

// Bottom arc text — characters at bottom half of circle, readable face-on.
module bottom_arc_text(str, radius, size, start_angle, char_angle) {
    for (i = [0:len(str)-1]) {
        angle = start_angle + i * char_angle;
        translate([radius * sin(angle), -radius * cos(angle), 0])
            rotate([0, 0, angle])
                text(str[i], size=size, font="Arial:style=Bold",
                     halign="center", valign="center");
    }
}


// =================================================================
// OBVERSE DESIGN (top face) - 2D shapes
// =================================================================

module obverse_navy_2d() {
    scale([logo_scale, logo_scale])
        import("logo_diamond.svg", center=true);
}

module obverse_carolina_2d() {
    scale([logo_scale, logo_scale])
        import("logo_border.svg", center=true);
}

module obverse_white_2d() {
    scale([logo_scale, logo_scale])
        import("logo_letters.svg", center=true);
}

// =================================================================
// REVERSE DESIGN (bottom face) - 2D shapes
// =================================================================

// Navy swimmer silhouette (bottom face)
module reverse_navy_2d() {
    mirror([1, 0, 0])
        translate([0, 1]) scale([0.65, 0.65])
            import("ref_swimmer.svg", center=true);
}

// White arc text only (bottom face)
module reverse_white_2d() {
    mirror([1, 0, 0]) {
        // Top arc: "NORTH COBB CHRISTIAN SCHOOL"
        arc_text("NORTH COBB CHRISTIAN SCHOOL",
                 radius=text_r, size=2.6,
                 start_angle=81, char_angle=6.8);

        // Bottom arc: "2026 SWIM TEAM"
        bottom_arc_text("2026 SWIM TEAM",
                        radius=text_r, size=2.6,
                        start_angle=-42, char_angle=7.2);
    }
}

// =================================================================
// 3D SHAPES for each color detail (used for both rendering AND subtraction)
// =================================================================

// Navy obverse diamond (top face)
module navy_diamond_3d() {
    translate([0, 0, total_h - relief])
        linear_extrude(height=relief)
            obverse_navy_2d();
}

// Navy swimmer (bottom face)
module navy_swimmer_3d() {
    linear_extrude(height=relief)
        reverse_navy_2d();
}

// Carolina obverse borders (top face)
module carolina_borders_3d() {
    translate([0, 0, total_h - relief + 0.01])
        linear_extrude(height=relief * 0.7)
            obverse_carolina_2d();
}

// White obverse letters (top face)
module white_obverse_3d() {
    translate([0, 0, total_h - relief])
        linear_extrude(height=relief)
            obverse_white_2d();
}

// White reverse text (bottom face)
module white_reverse_3d() {
    linear_extrude(height=relief)
        reverse_white_2d();
}

// =================================================================
// COLOR LAYER GEOMETRY - NO OVERLAP between parts
// =================================================================

// 1. NAVY: rim ring + obverse diamond + reverse swimmer
module navy_parts() {
    color(navy) {
        // Outer rim ring
        difference() {
            cylinder(h=total_h, d=coin_d, $fn=128);
            translate([0, 0, -0.01])
                cylinder(h=total_h+0.02, r=inner_r, $fn=128);
        }
        // Obverse diamond on top
        navy_diamond_3d();
        // Swimmer on bottom
        navy_swimmer_3d();
    }
}

// 2. GRAY: accent ring only
module gray_parts() {
    color(gray) {
        difference() {
            cylinder(h=total_h, r=inner_r, $fn=128);
            translate([0, 0, -0.01])
                cylinder(h=total_h+0.02, r=field_r, $fn=128);
        }
    }
}

// 3. CAROLINA: inner field with ALL other detail parts subtracted out
module carolina_parts() {
    color(carolina) {
        difference() {
            union() {
                // Base inner field cylinder
                cylinder(h=total_h, r=field_r, $fn=128);
                // Carolina borders on top
                carolina_borders_3d();
            }
            // Subtract navy diamond from top
            navy_diamond_3d();
            // Subtract navy swimmer from bottom
            navy_swimmer_3d();
            // Subtract white letters from top
            white_obverse_3d();
            // Subtract white text from bottom
            white_reverse_3d();
        }
    }
}

// 4. WHITE: obverse letters + reverse arc text
module white_parts() {
    color(white_c) {
        white_obverse_3d();
        white_reverse_3d();
    }
}

// === RENDER ===
if (COLOR == 0) {
    navy_parts();
    gray_parts();
    carolina_parts();
    white_parts();
} else if (COLOR == 1) {
    navy_parts();
} else if (COLOR == 2) {
    gray_parts();
} else if (COLOR == 3) {
    carolina_parts();
} else if (COLOR == 4) {
    white_parts();
}

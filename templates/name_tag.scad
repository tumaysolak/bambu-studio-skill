// Two-color name tag / keychain. Export both parts, slice with --assemble.
// openscad -D 'part="base"' -D 'name="MERHABA"' -o base.stl name_tag.scad
// openscad -D 'part="text"' -D 'name="MERHABA"' -o text.stl name_tag.scad
name = "MERHABA";
font = "Liberation Sans:style=Bold";
text_size = 10;     // cap height-ish, mm (keep >= 5 for 0.4 nozzle)
base_h = 3;         // plate thickness
text_h = 1.2;       // raised text height (6 layers @0.2)
margin = 4;
ring = true;        // keychain hole
ring_d = 5;
part = "all";       // "base" | "text" | "all"
$fn = 64;
len_est = len(name) * text_size * 0.92 + 2 * margin;
w = len_est + (ring ? ring_d + 4 : 0);
h = text_size + 2 * margin;
module base() {
  difference() {
    translate([0, 0, 0]) linear_extrude(base_h) offset(r = 3) offset(delta = -3) square([w, h]);
    if (ring) translate([ring_d / 2 + 3, h / 2, -1]) cylinder(d = ring_d, h = base_h + 2);
  }
}
module label() {
  translate([(ring ? ring_d + 4 : 0) + len_est / 2, h / 2, base_h - 0.01])
    linear_extrude(text_h + 0.01) text(name, size = text_size, font = font, halign = "center", valign = "center");
}
if (part == "base" || part == "all") color("white") base();
if (part == "text" || part == "all") color("red") label();

// Phone stand. Side profile is extruded along X, so it prints flat with no supports.
width = 70;          // stand width
angle = 65;          // back-rest angle from horizontal
phone_t = 12;        // phone + case thickness
lip_h = 12;          // front lip height above base
base_l = 90; t = 5;  // base length, general thickness
back_l = 95;         // back-rest length
cable_slot = 14;     // width of charging-cable slot in the lip/base, 0 = none
$fn = 48;
p0 = [t + phone_t, 0];                                   // back-rest pivot
pb = p0 + back_l * 0.62 * [cos(angle), sin(angle)];       // strut top
module bar(a, b, w) { hull() { translate(a) circle(d = w); translate(b) circle(d = w); } }
module profile() {
  square([base_l, t]);                                    // base
  square([t, lip_h + t]);                                 // front lip
  translate(p0) rotate(angle) square([back_l, t]);        // back-rest
  bar(pb + [t * 0.5, -t * 0.2], [base_l - t / 2, t / 2], t); // strut
}
difference() {
  rotate([90, 0, 90]) linear_extrude(width) profile();
  if (cable_slot > 0) translate([width / 2 - cable_slot / 2, -1, -1]) cube([cable_slot, t + phone_t + 2, lip_h + t + 2]);
}

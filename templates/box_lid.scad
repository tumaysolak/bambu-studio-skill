// Box with slip-fit lid. part = "box" | "lid" | "all" (lid printed upside down, next to box)
inner = [60, 40, 30];   // usable inside size X,Y,Z
wall = 1.6;             // 4 perimeters @0.4
floor = 1.2;
r = 3;                  // corner radius
lid_h = 8; lid_lip = 4; clearance = 0.2;  // 0.2 = snug slip fit on A1 mini
part = "all";
$fn = 48;
module rbox(s, rr) { linear_extrude(s[2]) offset(r = rr) offset(delta = -rr) square([s[0], s[1]]); }
outer = [inner[0] + 2 * wall, inner[1] + 2 * wall, inner[2] + floor];
module box() { difference() { rbox(outer, r); translate([wall, wall, floor]) rbox([inner[0], inner[1], inner[2] + 1], max(r - wall, 0.5)); } }
module lid() {
  rbox([outer[0], outer[1], floor], r);
  translate([wall + clearance, wall + clearance, 0]) difference() {
    rbox([inner[0] - 2 * clearance, inner[1] - 2 * clearance, floor + lid_lip], max(r - wall, 0.5));
    translate([wall, wall, floor]) rbox([inner[0] - 2 * clearance - 2 * wall, inner[1] - 2 * clearance - 2 * wall, lid_lip + 1], 0.5);
  }
}
if (part == "box" || part == "all") box();
if (part == "lid" || part == "all") translate([outer[0] + 8, 0, 0]) lid();

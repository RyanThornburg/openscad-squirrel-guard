/*
 * Squirrel Guard - Rectangular Parametric Flower Box Cover 
 * ==============================================================
 * Rounded-slot drainage panel with two independent rows of
 * plant holes (front and back), each with configurable count,
 * radius, Y-offset, and spike rings.
 * Border spikes on all four edges.
 *
 */

// preview[view:top, tilt:top]

/* [Panel Dimensions] */

// Width of the panel — match the inside of your flower box (mm)
panel_width = 350; // [20:1:1500]

// Length of the panel — match the inside of your flower box (mm)
panel_length = 100; // [20:1:1500]

// Thickness of the panel (mm)
panel_thickness = 3; // [2:0.5:10]

// Solid border around all edges — no slots within this zone (mm)
border = 2; // [0:1:30]

/* [Slot Holes] */

// Slot width — keep under 18 mm to block a squirrel paw (mm)
slot_width = 6; // [2:1:25]

// Slot length (mm)
slot_length = 12; // [2:2:80]

// Gap between slots (mm)
slot_gap = 2.5; // [2:0.5:10]

// Slot orientation
slot_axis = 1; // [0:Along length (Y), 1:Across width (X)]

/* [Front Row Holes] */

// Enable the front row of plant holes
front_row_enabled = true; // [true:Yes, false:No]

// Number of holes in the front row
front_hole_count = 5; // [1:1:20]

// Radius of each front hole (mm)
front_hole_radius = 20; // [5:1:150]

// Slot-free margin around each front hole (mm)
front_hole_clearance = 2; // [0:1:20]

// Y offset of front row from panel centre — negative = toward front (mm)
// 0 = centred, negative = toward front edge, positive = toward back edge
front_row_offset = -45; // [-750:1:750]

/* [Back Row Holes] */

// Enable the back row of plant holes
back_row_enabled = true; // [true:Yes, false:No]

// Number of holes in the back row
back_hole_count = 1; // [1:1:12]

// Radius of each back hole (mm)
back_hole_radius = 40; // [5:1:150]

// Slot-free margin around each back hole (mm)
back_hole_clearance = 2; // [0:1:20]

// Y offset of back row from panel centre — positive = toward back (mm)
back_row_offset = 20; // [-750:1:750]

/* [Front Row Spikes] */

// Enable spikes around front row holes
front_spikes_enabled = true; // [true:Yes, false:No]

// Front spike shape
front_spike_shape = 0; // [0:Pyramid, 1:Cone, 2:Blunt nub]

// Front spike height (mm)
front_spike_height = 12; // [3:1:40]

// Front spike base width (mm)
front_spike_base = 5; // [2:0.5:14]

// Number of spikes around each front hole
front_spike_count = 8; // [1:1:36]

// Gap between front hole edge and spike base (mm)
front_spike_clearance = 3; // [0:0.5:15]

/* [Back Row Spikes] */

// Enable spikes around back row holes
back_spikes_enabled = true; // [true:Yes, false:No]

// Back spike shape
back_spike_shape = 0; // [0:Pyramid, 1:Cone, 2:Blunt nub]

// Back spike height (mm)
back_spike_height = 12; // [3:1:40]

// Back spike base width (mm)
back_spike_base = 5; // [2:0.5:14]

// Number of spikes around each back hole
back_spike_count = 8; // [1:1:36]

// Gap between back hole edge and spike base (mm)
back_spike_clearance = 3; // [0:0.5:15]

/* [Border Spikes] */

// Enable spikes along the panel border
border_spikes_enabled = true; // [true:Yes, false:No]

// Border spike shape
border_spike_shape = 0; // [0:Pyramid, 1:Cone, 2:Blunt nub]

// Border spike height (mm)
border_spike_height = 15; // [3:1:40]

// Border spike base width (mm)
border_spike_base = 6; // [2:0.5:14]

// Number of spikes along each length edge (front and back long sides)
border_spikes_on_length_edges = 12; // [1:1:60]

// Number of spikes along each width edge (left and right short sides)
border_spikes_on_width_edges = 6; // [1:1:40]

// Margin inward from panel edge where border spikes sit (mm)
border_spike_margin = 8; // [4:1:25]

/* [Spike Priority] */

// When a spike and slot overlap, which wins?
spike_priority = true; // [true:Spike wins (skip the slot), false:Slot wins (skip the spike)]

/* [Segments] */

// Number of columns (splits along width)
segments_x = 1; // [1:1:6]

// Number of rows (splits along length)
segments_y = 1; // [1:1:8]

// Which segment to render — 0 = full preview, 1+ = individual piece
segment_to_print = 0; // [0:Full preview, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

/* [Hidden] */
$fn = 32;
eps = 0.01;
gtol = 0.01;

// ─── Derived values 

sw = (slot_axis == 0) ? slot_width : slot_length;
sl = (slot_axis == 0) ? slot_length : slot_width;
pitch_x = sw + slot_gap;
pitch_y = sl + slot_gap;

// Row Y positions (panel Y centre + offset)
panel_cy = panel_length / 2;
front_row_y = panel_cy + front_row_offset;
back_row_y = panel_cy + back_row_offset;

// Hole X positions — holes evenly spaced so the gap between hole edges
// is equal on all sides (left margin = middle gaps = right margin).
// Formula: equal_gap = (panel_width - 2*n*r) / (n+1)
//          centre_x  = r + equal_gap*(idx+1) + 2*r*idx
// When r=0 this reduces to the old panel_width/(count+1)*(idx+1)
function hole_x(idx, count, r) =
  let (gap = (panel_width - 2 * count * r) / (count + 1)) r + gap * (idx + 1) + 2 * r * idx;

// Convenience wrappers — use these everywhere instead of bare hole_x
function front_hole_x(idx) = hole_x(idx, front_hole_count, front_hole_radius);
function back_hole_x(idx) = hole_x(idx, back_hole_count, back_hole_radius);

// Effective slot clearances — large enough to protect spike rings
_eff_front_clear =
  front_row_enabled ? max(front_hole_clearance, front_spikes_enabled ? front_spike_clearance + front_spike_base : front_hole_clearance)
  : 0;
_eff_back_clear =
  back_row_enabled ? max(back_hole_clearance, back_spikes_enabled ? back_spike_clearance + back_spike_base : back_hole_clearance)
  : 0;

// Slot grid globals
_interior_w = panel_width - 2 * border;
_interior_l = panel_length - 2 * border;
// Guard against panels too narrow/short to fit even one slot
_cols = max(0, floor((_interior_w - sw) / pitch_x) + 1);
_rows = max(0, floor((_interior_l - sl) / pitch_y) + 1);
_grid_w = (_cols > 0) ? (_cols - 1) * pitch_x : 0;
_grid_l = (_rows > 0) ? (_rows - 1) * pitch_y : 0;
SLOT_X0 = border + (_interior_w - _grid_w) / 2;
SLOT_Y0 = border + (_interior_l - _grid_l) / 2;
SLOT_COLS = _cols;
SLOT_ROWS = _rows;

function dist2sq(ax, ay, bx, by) =
  let (dx = ax - bx, dy = ay - by) dx * dx + dy * dy;

// Does a slot at (sx,sy) overlap any hole?
function slot_overlaps_front(sx, sy) =
  !front_row_enabled ? false
  : let (thresh2 = let (t = front_hole_radius + _eff_front_clear + max(sw, sl) / 2) t * t) len(
    [
      for (i = [0:front_hole_count - 1]) if (dist2sq(sx, sy, front_hole_x(i), front_row_y) < thresh2) 1,
    ]
  ) > 0;

function slot_overlaps_back(sx, sy) =
  !back_row_enabled ? false
  : let (thresh2 = let (t = back_hole_radius + _eff_back_clear + max(sw, sl) / 2) t * t) len(
    [
      for (i = [0:back_hole_count - 1]) if (dist2sq(sx, sy, back_hole_x(i), back_row_y) < thresh2) 1,
    ]
  ) > 0;

function slot_overlaps_any_hole(sx, sy) =
  slot_overlaps_front(sx, sy) || slot_overlaps_back(sx, sy);

function slot_fits_panel(sx, sy) =
  (sx - sw / 2 >= border) && (sx + sw / 2 <= panel_width - border) && (sy - sl / 2 >= border) && (sy + sl / 2 <= panel_length - border);

// ─── Spike helpers 

function spike_in_rect(sx, sy, b) =
  (sx - b / 2 >= 0) && (sx + b / 2 <= panel_width) && (sy - b / 2 >= 0) && (sy + b / 2 <= panel_length);

// Spike must not have its centre inside any plant hole
function spike_hits_front_hole(sx, sy, b) =
  !front_row_enabled ? false
  : let (thresh2 = (front_hole_radius + b / 2) * (front_hole_radius + b / 2)) len(
    [
      for (i = [0:front_hole_count - 1]) if (dist2sq(sx, sy, front_hole_x(i), front_row_y) < thresh2) 1,
    ]
  ) > 0;

function spike_hits_back_hole(sx, sy, b) =
  !back_row_enabled ? false
  : let (thresh2 = (back_hole_radius + b / 2) * (back_hole_radius + b / 2)) len(
    [
      for (i = [0:back_hole_count - 1]) if (dist2sq(sx, sy, back_hole_x(i), back_row_y) < thresh2) 1,
    ]
  ) > 0;

function spike_hits_any_hole(sx, sy, b) =
  spike_hits_front_hole(sx, sy, b) || spike_hits_back_hole(sx, sy, b);

// Does a spike at (sx,sy) with base b overlap any slot?
function dist_to_rrect(px, py, rcx, rcy, hx, hy, r) =
  let (
    dx = max(abs(px - rcx) - (hx - r), 0),
    dy = max(abs(py - rcy) - (hy - r), 0)
  ) sqrt(dx * dx + dy * dy) - r;

function spike_over_slot(spx, spy, b) =
  !spike_priority ? false
  : let (
    _shx = sw / 2,
    _shy = sl / 2,
    _sr = min(sw, sl) / 2,
    max_reach = b / 2 + max(_shx, _shy),
    bc = floor((spx - SLOT_X0) / pitch_x),
    br = floor((spy - SLOT_Y0) / pitch_y),
    sc = ceil(max_reach / pitch_x),
    sr = ceil(max_reach / pitch_y),
    mc = max(0, bc - sc),
    xc = min(SLOT_COLS - 1, bc + sc),
    mr = max(0, br - sr),
    xr = min(SLOT_ROWS - 1, br + sr)
  ) len(
    [
      for (col = [mc:xc], row = [mr:xr]) let (scx = SLOT_X0 + col * pitch_x, scy = SLOT_Y0 + row * pitch_y) if (
        slot_fits_panel(scx, scy) && !slot_overlaps_any_hole(scx, scy) && dist_to_rrect(spx, spy, scx, scy, _shx, _shy, _sr) < b / 2
      ) 1,
    ]
  ) > 0;

// Spike self-collision check
function spike_collides(sx, sy, b, placed) =
  len(
    [
      for (p = placed) if (dist2sq(sx, sy, p[0], p[1]) < (b + p[2]) * (b + p[2]) / 4) 1,
    ]
  ) > 0;

function spike_placeable(sx, sy, b, placed) =
  spike_in_rect(sx, sy, b) && !spike_hits_any_hole(sx, sy, b) && !spike_collides(sx, sy, b, placed) && (spike_priority || !spike_over_slot(sx, sy, b));

// Collect spike candidates
function _collect(pts, i, acc, b, t) =
  i >= len(pts) ? acc
  : let (
    sx = pts[i][0],
    sy = pts[i][1],
    ok = spike_placeable(sx, sy, b, acc)
  ) _collect(pts, i + 1, ok ? concat(acc, [[sx, sy, b, t]]) : acc, b, t);

// Ring of spikes around hole at (hx,hy) with given hole_r, clearance, base, count
function _hole_ring(hx, hy, hole_r, clearance, base, count, t) =
  let (
    ring_r = hole_r + clearance + base / 2 + gtol,
    n = max(1, count),
    a_step = 360 / n,
    pts = [for (i = [0:n - 1]) [hx + ring_r * cos(i * a_step), hy + ring_r * sin(i * a_step)]]
  ) _collect(pts, 0, [], base, t);

// All front hole spikes (type=0)
function _front_spike_acc() =
  !(front_row_enabled && front_spikes_enabled) ? []
  : [
    for (
      i = [0:front_hole_count - 1],
      pt = _hole_ring(
        front_hole_x(i), front_row_y,
        front_hole_radius, front_spike_clearance,
        front_spike_base, front_spike_count, 0
      )
    ) pt,
  ];

// All back hole spikes (type=1)
function _back_spike_acc() =
  !(back_row_enabled && back_spikes_enabled) ? []
  : [
    for (
      i = [0:back_hole_count - 1],
      pt = _hole_ring(
        back_hole_x(i), back_row_y,
        back_hole_radius, back_spike_clearance,
        back_spike_base, back_spike_count, 1
      )
    ) pt,
  ];

// Border spikes — unified CCW perimeter traversal (type=2)
//
// Candidates are generated in a single deterministic counter-clockwise pass
// around the perimeter (bot → right → top-reversed → left-reversed), then
// collected in one _collect() call.  This eliminates the corner-bias that
// arose from concatenating four independent edge batches: every candidate is
// evaluated in a consistent angular order regardless of which edge it sits on.
//
// All four edges use the same (m + b/2) anchor, so the outermost spikes are
// flush with the margin inset on every side
//
// Seeded with hole ring spikes so border placement avoids cross-type collisions.
function _border_spike_acc(hole_acc) =
  !border_spikes_enabled ? []
  : let (
    nl = max(1, border_spikes_on_length_edges),
    nw = max(1, border_spikes_on_width_edges),
    b = border_spike_base,
    m = border_spike_margin,
    // Usable spans — outermost spike sits exactly at margin inset
    x0 = m + b / 2,
    x1 = panel_width - m - b / 2,
    y0 = m + b / 2,
    y1 = panel_length - m - b / 2,
    // CCW traversal: bot (L→R), right (B→T), top (R→L), left (T→B)
    bot = [
      for (i = [0:nl - 1]) [x0 + (nl > 1 ? (x1 - x0) / (nl - 1) * i : (x1 - x0) / 2), m],
    ],
    right = [
      for (i = [0:nw - 1]) [panel_width - m, y0 + (nw > 1 ? (y1 - y0) / (nw - 1) * i : (y1 - y0) / 2)],
    ],
    top = [
      for (i = [0:nl - 1]) [x1 - (nl > 1 ? (x1 - x0) / (nl - 1) * i : (x1 - x0) / 2), panel_length - m],
    ],
    left = [
      for (i = [0:nw - 1]) [m, y1 - (nw > 1 ? (y1 - y0) / (nw - 1) * i : (y1 - y0) / 2)],
    ],
    all = concat(bot, right, top, left),
    full_acc = _collect(all, 0, hole_acc, b, 2),
    n_hole = len(hole_acc)
  ) [for (i = [n_hole:len(full_acc) - 1]) full_acc[i]];

FRONT_ACC = _front_spike_acc();
BACK_ACC = _back_spike_acc();
// Border is seeded with hole ring spikes to prevent cross-type collisions
BORDER_ACC = _border_spike_acc(concat(FRONT_ACC, BACK_ACC));
ALL_SPIKES = concat(FRONT_ACC, BACK_ACC, BORDER_ACC);

// Does a slot physically overlap any spike?
// Uses the same rounded-rect SDF as spike_over_slot so both directions
// of the slot/spike test use matching geometry (no more AABB over-rejection)
function slot_hits_spike(sx, sy) =
  let (_shx = sw / 2, _shy = sl / 2, _sr = min(sw, sl) / 2) len(
    [
      for (p = ALL_SPIKES) if (dist_to_rrect(p[0], p[1], sx, sy, _shx, _shy, _sr) < p[2] / 2) 1,
    ]
  ) > 0;

// ─── Modules 

module rounded_slot(sx, sy) {
  r = min(sw, sl) / 2;
  ox = sw / 2 - r;
  oy = sl / 2 - r;
  translate([sx, sy, -eps])
    linear_extrude(panel_thickness + 2 * eps)
      hull() {
        translate([ox, oy]) circle(r);
        translate([-ox, oy]) circle(r);
        translate([ox, -oy]) circle(r);
        translate([-ox, -oy]) circle(r);
      }
}

module slot_grid() {
  for (col = [0:SLOT_COLS - 1])
    for (row = [0:SLOT_ROWS - 1]) {
      sx = SLOT_X0 + col * pitch_x;
      sy = SLOT_Y0 + row * pitch_y;
      if (
        slot_fits_panel(sx, sy) && !slot_overlaps_any_hole(sx, sy) && (!spike_priority || !slot_hits_spike(sx, sy))
      )
        rounded_slot(sx, sy);
    }
}

module plant_holes() {
  if (front_row_enabled)
    for (i = [0:front_hole_count - 1])
      translate([front_hole_x(i), front_row_y, -eps])
        cylinder(h=panel_thickness + 2 * eps, r=front_hole_radius);
  if (back_row_enabled)
    for (i = [0:back_hole_count - 1])
      translate([back_hole_x(i), back_row_y, -eps])
        cylinder(h=panel_thickness + 2 * eps, r=back_hole_radius);
}

module single_spike(sx, sy, s_height, s_base, s_shape) {
  translate([sx, sy, panel_thickness]) {
    if (s_shape == 0) {
      linear_extrude(height=s_height, scale=0)
        square(s_base, center=true);
    } else if (s_shape == 1) {
      cylinder(h=s_height, r1=s_base / 2, r2=0, $fn=32);
    } else {
      nub_h = s_height * 0.7;
      dome_r = s_base / 2;
      dome_h = s_height - nub_h;
      cylinder(h=nub_h, r=dome_r, $fn=32);
      translate([0, 0, nub_h])
        scale([1, 1, dome_h / dome_r])
          sphere(r=dome_r, $fn=32);
    }
  }
}

module all_spikes() {
  for (p = FRONT_ACC)
    single_spike(p[0], p[1], front_spike_height, front_spike_base, front_spike_shape);
  for (p = BACK_ACC)
    single_spike(p[0], p[1], back_spike_height, back_spike_base, back_spike_shape);
  for (p = BORDER_ACC)
    single_spike(p[0], p[1], border_spike_height, border_spike_base, border_spike_shape);
}

max_spike_height = max(
  front_spikes_enabled && front_row_enabled ? front_spike_height : 0,
  back_spikes_enabled && back_row_enabled ? back_spike_height : 0,
  border_spikes_enabled ? border_spike_height : 0
);

module full_panel() {
  union() {
    difference() {
      cube([panel_width, panel_length, panel_thickness]);
      slot_grid();
      plant_holes();
    }
    all_spikes();
  }
}

// ─── Segmenting 

seg_w = panel_width / segments_x;
seg_l = panel_length / segments_y;

module segment(si_x, si_y) {
  x0 = si_x * seg_w;
  y0 = si_y * seg_l;
  intersection() {
    full_panel();
    translate([x0, y0, 0])
      cube([seg_w, seg_l, panel_thickness + max_spike_height + eps]);
  }
}

// ─── Top-level render 

if (segment_to_print == 0) {
  preview_gap = (segments_x > 1 || segments_y > 1) ? 2 : 0;
  for (si_x = [0:segments_x - 1])
    for (si_y = [0:segments_y - 1])
      translate([si_x * preview_gap, si_y * preview_gap, 0])
        segment(si_x, si_y);
} else {
  idx = segment_to_print - 1;
  si_x = idx % segments_x;
  si_y = floor(idx / segments_x);
  translate([-si_x * seg_w, -si_y * seg_l, 0])
    segment(si_x, si_y);
}

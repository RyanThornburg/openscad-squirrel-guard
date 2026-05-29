/*
 * Squirrel Guard - Circular Parametric Flower Box Cover
 * =====================================================
 * Circular panel with rounded-slot drainage holes,
 * optional centered + satellite plant holes, and
 * optional surface spikes to deter squirrels.
 *
 */

// preview[view:top, tilt:top]

/* [Panel Dimensions] */

// Overall diameter of the circular panel (mm)
panel_diameter = 215; // [100:5:2000]

// Thickness of the panel — 4–6 mm recommended
panel_thickness = 3; // [2:0.5:10]

// Solid border inside the circle edge — no slots within this zone (mm)
border = 2; // [2:1:30]

/* [Slot Holes] */

// Slot width — keep under 18 mm to block a squirrel paw (mm)
slot_width = 6; // [6:1:25]

// Slot length (mm)
slot_length = 12; // [12:2:80]

// Gap between slots (mm)
slot_gap = 2.5; // [2.5:0.5:10]

// Slot orientation
slot_axis = 0; // [0:Along Y, 1:Along X]

/* [Center Plant Hole] */

// Enable the center plant hole
center_hole_enabled = true; // [true:Yes, false:No]

// Radius of the center hole (mm)
center_hole_radius = 25; // [5:1:200]

// Slot-free margin around the center hole (mm)
center_hole_clearance = 1; // [0:1:20]

/* [Satellite Plant Holes] */

// Enable satellite plant holes
satellite_holes_enabled = true; // [true:Yes, false:No]

// Number of satellite holes
satellite_count = 6; // [2:1:12]

// Radius of each satellite hole (mm)
satellite_hole_radius = 20; // [5:1:80]

// Slot-free margin around each satellite hole (mm)
satellite_hole_clearance = 0; // [0:1:20]

// Distance of satellite centres from panel centre (0 = auto midpoint)
satellite_orbit_radius = 0; // [0:5:200]

/* [Center Hole Spikes] */

// Enable spikes around the center hole
center_spikes_enabled = true; // [true:Yes, false:No]

// Center spike shape
center_spike_shape = 0; // [0:Pyramid, 1:Cone, 2:Blunt nub]

// Center spike height (mm)
center_spike_height = 20; // [1:1:60]

// Center spike base width (mm)
center_spike_base = 4; // [1:0.5:20]

// Number of spikes around the center hole
center_spike_count = 6; // [1:1:36]

// Gap between center hole edge and spike base (mm)
center_spike_clearance = 1; // [0:0.5:15]

/* [Satellite Hole Spikes] */

// Enable spikes around satellite holes
satellite_spikes_enabled = true; // [true:Yes, false:No]

// Satellite spike shape
satellite_spike_shape = 0; // [0:Pyramid, 1:Cone, 2:Blunt nub]

// Satellite spike height (mm)
satellite_spike_height = 20; // [1:1:60]

// Satellite spike base width (mm)
satellite_spike_base = 4; // [1:0.5:20]

// Number of spikes around each satellite hole
satellite_spike_count = 6; // [1:1:36]

// Gap between satellite hole edge and spike base (mm)
satellite_spike_clearance = 1; // [0:0.5:15]

/* [Border Spikes] */

// Enable spikes along the outer border
border_spikes_enabled = true; // [true:Yes, false:No]

// Border spike shape
border_spike_shape = 0; // [0:Pyramid, 1:Cone, 2:Blunt nub]

// Border spike height (mm)
border_spike_height = 25; // [25:1:80]

// Border spike base width (mm)
border_spike_base = 8; // [2:0.5:20]

// Number of spikes around the border ring (rounded up to multiple of satellite_count)
border_spike_count = 18; // [1:1:72]

// Margin inward from panel edge where border ring sits (mm)
border_spike_margin = 6; // [4:1:25]

/* [Spike Priority] */

// When a spike and slot overlap, which wins?
spike_priority = true; // [true:Spike wins (skip the slot), false:Slot wins (skip the spike)]

/* [Segments] */

// Number of columns (splits along X)
segments_x = 1; // [1:1:6]

// Number of rows (splits along Y)
segments_y = 1; // [1:1:6]

// Which segment to render — 0 = full preview, 1+ = individual piece
segment_to_print = 0; // [0:Full preview, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

/* [Hidden] */
$fn = 64;
eps = 0.01;
geom_tol = 0.01;

// ─── Derived values ───────────────────────────────────────────────────────────

R = panel_diameter / 2;
cx = R;
cy = R;
inner_r = R - border;

sw = (slot_axis == 0) ? slot_width : slot_length;
sl = (slot_axis == 0) ? slot_length : slot_width;
slot_half_max = max(sw, sl) / 2;

pitch_x = sw + slot_gap;
pitch_y = sl + slot_gap;

// Slot grid dimensions — precomputed once, shared by slot_grid() and spike_over_any_slot()
SLOT_SPAN = 2 * (R - border);
SLOT_COLS = floor((SLOT_SPAN - sw) / pitch_x) + 1;
SLOT_ROWS = floor((SLOT_SPAN - sl) / pitch_y) + 1;
SLOT_GRID_W = (SLOT_COLS - 1) * pitch_x;
SLOT_GRID_L = (SLOT_ROWS - 1) * pitch_y;
SLOT_X0 = R - SLOT_GRID_W / 2; // cx = R
SLOT_Y0 = R - SLOT_GRID_L / 2; // cy = R

// Effective clearances — large enough for each hole's spike ring
// so slots don't cut into the zone where spikes sit
_min_center_clear = center_spikes_enabled ? center_spike_clearance + center_spike_base : 0;
_min_satellite_clear = satellite_spikes_enabled ? satellite_spike_clearance + satellite_spike_base : 0;
_eff_center_clear = max(center_hole_clearance, _min_center_clear);
_eff_satellite_clear = max(satellite_hole_clearance, _min_satellite_clear);

_center_edge =
  center_hole_enabled ? center_hole_radius + _eff_center_clear
  : 0;
_panel_inner = R - border;
_auto_orbit = (_center_edge + _panel_inner) / 2;
orbit = (satellite_orbit_radius > 0) ? satellite_orbit_radius : _auto_orbit;

// dist2 returns SQUARED distance — avoids sqrt() for all threshold comparisons
function dist2(ax, ay, bx, by) = let (dx = ax - bx, dy = ay - by) dx * dx + dy * dy;

function c_thresh(hr, hc, sh) = hr + hc + sh;

function sat_angle(i) = 360 / satellite_count * i;

function overlaps_center(sx, sy) =
  center_hole_enabled ? dist2(sx, sy, cx, cy) < c_thresh(center_hole_radius, _eff_center_clear, slot_half_max) * c_thresh(center_hole_radius, _eff_center_clear, slot_half_max)
  : false;

function overlaps_satellite(sx, sy) =
  !satellite_holes_enabled ? false
  : let (thresh2 = let (t = c_thresh(satellite_hole_radius, _eff_satellite_clear, slot_half_max)) t * t) len(
    [
      for (i = [0:satellite_count - 1]) if (
        dist2(
          sx, sy,
          cx + orbit * cos(sat_angle(i)),
          cy + orbit * sin(sat_angle(i))
        ) < thresh2
      ) 1,
    ]
  ) > 0;

function overlaps_any_hole(sx, sy) =
  overlaps_center(sx, sy) || overlaps_satellite(sx, sy);

function slot_in_circle(sx, sy) =
  let (_r = inner_r - slot_half_max) dist2(sx, sy, cx, cy) <= _r * _r;

// ─── Spike validity helpers ────

function spike_in_panel(sx, sy, b) =
  let (_r = inner_r - b / 2) dist2(sx, sy, cx, cy) <= _r * _r;

function spike_hits_center(sx, sy, c, b) =
  let (_t = center_hole_radius + c + b / 2) center_hole_enabled && dist2(sx, sy, cx, cy) < _t * _t;

function spike_hits_satellite(sx, sy, c, b) =
  !satellite_holes_enabled ? false
  : let (thresh2 = let (_t = satellite_hole_radius + c + b / 2) _t * _t) len(
    [
      for (i = [0:satellite_count - 1]) if (
        dist2(
          sx, sy,
          cx + orbit * cos(sat_angle(i)),
          cy + orbit * sin(sat_angle(i))
        ) < thresh2
      ) 1,
    ]
  ) > 0;

function dist_to_rrect(px, py, rcx, rcy, hx, hy, r) =
  let (
    dx = max(abs(px - rcx) - (hx - r), 0),
    dy = max(abs(py - rcy) - (hy - r), 0)
  ) sqrt(dx * dx + dy * dy) - r;

function spike_over_any_slot(spx, spy, b) =
  let (
    _shx = sw / 2,
    _shy = sl / 2,
    _sr = min(sw, sl) / 2,
    max_reach = b / 2 + max(_shx, _shy),
    base_col = floor((spx - SLOT_X0) / pitch_x),
    base_row = floor((spy - SLOT_Y0) / pitch_y),
    search_cols = ceil(max_reach / pitch_x),
    search_rows = ceil(max_reach / pitch_y),
    min_c = max(0, base_col - search_cols),
    max_c = min(SLOT_COLS - 1, base_col + search_cols),
    min_r = max(0, base_row - search_rows),
    max_r = min(SLOT_ROWS - 1, base_row + search_rows)
  ) len(
    [
      for (col = [min_c:max_c], row = [min_r:max_r]) let (
        scx = SLOT_X0 + col * pitch_x,
        scy = SLOT_Y0 + row * pitch_y
      ) if (
        slot_in_circle(scx, scy) && !overlaps_any_hole(scx, scy) && dist_to_rrect(spx, spy, scx, scy, _shx, _shy, _sr) < b / 2
      ) 1,
    ]
  ) > 0;

// spike_placeable: panel boundary + hole keepouts always checked
// skip_center: pass true when placing the center hole ring itself
// placed = list of [x,y,base,type] quads already accepted
function spike_placeable(sx, sy, c, b, placed = [], skip_center = false) =
  spike_in_panel(sx, sy, b) && (skip_center || !spike_hits_center(sx, sy, c, b)) && !spike_hits_satellite(sx, sy, c, b) && (spike_priority || !spike_over_any_slot(sx, sy, b)) && len([for (p = placed) if (dist2(sx, sy, p[0], p[1]) < (b + p[2]) * (b + p[2]) / 4) 1]) == 0;

// border_spike_placeable: only checks panel boundary and self-collision.
// Border spikes sit on the outer ring — satellite/center keepouts don't apply
// and using border_spike_margin as a hole clearance is semantically wrong.
function border_spike_placeable(sx, sy, b, placed = []) =
  spike_in_panel(sx, sy, b) && (spike_priority || !spike_over_any_slot(sx, sy, b)) && len([for (p = placed) if (dist2(sx, sy, p[0], p[1]) < (b + p[2]) * (b + p[2]) / 4) 1]) == 0;

// ─── Spike position lists ─────────────────────────────────────────────────────

// Walk candidate list, accept each that passes checks.
// acc = [x,y,base,type] quads. Returns full acc including new spikes.
function _collect_spikes(pts, i, acc, c, b, skip_center = false, t = 0) =
  i >= len(pts) ? acc
  : let (
    sx = pts[i][0],
    sy = pts[i][1],
    ok = spike_placeable(sx, sy, c, b, acc, skip_center)
  ) _collect_spikes(pts, i + 1, ok ? concat(acc, [[sx, sy, b, t]]) : acc, c, b, skip_center, t);

// Round n up to nearest multiple of fold to guarantee rotational symmetry.
function _round_to_fold(n, fold) = ceil(max(n, 1) / fold) * fold;

// Spike ring for the center hole — exactly center_spike_count spikes, evenly spaced
function _center_ring_pts() =
  let (
    ring_r = center_hole_radius + center_spike_clearance + center_spike_base / 2 + geom_tol,
    n = max(1, center_spike_count),
    a_step = 360 / n,
    pts = [for (i = [0:n - 1]) [cx + ring_r * cos(i * a_step), cy + ring_r * sin(i * a_step)]]
  ) _collect_spikes(pts, 0, [], center_spike_clearance, center_spike_base, true, 0);

// Spike ring for one satellite hole — exactly satellite_spike_count spikes, evenly spaced
function _sat_ring_pts(hcx, hcy) =
  let (
    ring_r = satellite_hole_radius + satellite_spike_clearance + satellite_spike_base / 2 + geom_tol,
    n = max(1, satellite_spike_count),
    a_step = 360 / n,
    pts = [for (i = [0:n - 1]) [hcx + ring_r * cos(i * a_step), hcy + ring_r * sin(i * a_step)]]
  ) _collect_spikes(pts, 0, [], satellite_spike_clearance, satellite_spike_base, false, 1);

// All hole spike positions: center and satellite rings independent.
// Returns [x,y,base,type] quads — type: 0=center, 1=satellite, 2=border.
function _all_hole_acc() =
  let (
    center_pts = (center_spikes_enabled && center_hole_enabled) ? _center_ring_pts()
    : [],
    sat_pts = (satellite_spikes_enabled && satellite_holes_enabled) ? [
        for (
          i = [0:satellite_count - 1],
          pt = _sat_ring_pts(
            cx + orbit * cos(sat_angle(i)),
            cy + orbit * sin(sat_angle(i))
          )
        ) pt,
      ]
    : []
  ) concat(center_pts, sat_pts);

// Walk border spike candidates — uses border_spike_placeable (no hole keepouts)
function _collect_border_spikes(pts, i, acc, b) =
  i >= len(pts) ? acc
  : let (
    sx = pts[i][0],
    sy = pts[i][1],
    ok = border_spike_placeable(sx, sy, b, acc)
  ) _collect_border_spikes(pts, i + 1, ok ? concat(acc, [[sx, sy, b, 2]]) : acc, b);

// All spike [x,y,base,type] quads — hole spikes then border spikes
// HOLE_ACC contains all hole spikes (center + satellite), each independently controlled
HOLE_ACC = _all_hole_acc();

BORDER_ACC =
  !border_spikes_enabled ? []
  : let (
    ring_r = inner_r - border_spike_margin,
    fold = satellite_holes_enabled ? satellite_count : 1,
    n = _round_to_fold(border_spike_count, fold),
    a_step = 360 / n,
    pts = [
      for (i = [0:n - 1]) [cx + ring_r * cos(i * a_step), cy + ring_r * sin(i * a_step)],
    ]
  )
  // Border ring: independent accumulator, no hole keepouts.
  // Uses border_spike_placeable which only checks panel boundary + self-collision.
  _collect_border_spikes(pts, 0, [], border_spike_base);

// Combined list used by slot priority check
ALL_SPIKES = concat(HOLE_ACC, BORDER_ACC);

// Does slot at (slx,sly) physically overlap any spike?
// Uses dist_to_rrect SDF — matches the rectangular variant and avoids AABB false
// positives that suppress valid drainage slots near spike corners.
function slot_hits_any_spike(slx, sly) =
  let (_shx = sw / 2, _shy = sl / 2, _sr = min(sw, sl) / 2) len(
    [
      for (p = ALL_SPIKES) if (
        dist_to_rrect(p[0], p[1], slx, sly, _shx, _shy, _sr) < p[2] / 2
      ) 1,
    ]
  ) > 0;

// ─── Panel modules ────────────────────────────────────────────────────────────

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
        slot_in_circle(sx, sy) && !overlaps_any_hole(sx, sy) && (!spike_priority || !slot_hits_any_spike(sx, sy))
      )
        rounded_slot(sx, sy);
    }
}

module plant_holes() {
  if (center_hole_enabled)
    translate([cx, cy, -eps])
      cylinder(h=panel_thickness + 2 * eps, r=center_hole_radius);
  if (satellite_holes_enabled)
    for (i = [0:satellite_count - 1])
      translate([cx + orbit * cos(sat_angle(i)), cy + orbit * sin(sat_angle(i)), -eps])
        cylinder(h=panel_thickness + 2 * eps, r=satellite_hole_radius);
}

// ─── Spike modules ────────────────────────────────────────────────────────────

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

module hole_spike_rings() {
  // p[3] == 0 → center spike, p[3] == 1 → satellite spike
  for (p = HOLE_ACC) {
    if (p[3] == 0)
      single_spike(p[0], p[1], center_spike_height, center_spike_base, center_spike_shape);
    else
      single_spike(p[0], p[1], satellite_spike_height, satellite_spike_base, satellite_spike_shape);
  }
}

module border_spike_ring() {
  for (p = BORDER_ACC)
    single_spike(p[0], p[1], border_spike_height, border_spike_base, border_spike_shape);
}

// ─── Full panel ───────────────────────────────────────────────────────────────

max_spike_height = max(
  center_spikes_enabled ? center_spike_height : 0,
  satellite_spikes_enabled ? satellite_spike_height : 0,
  border_spikes_enabled ? border_spike_height : 0
);

module full_panel() {
  union() {
    difference() {
      translate([cx, cy, 0])
        cylinder(h=panel_thickness, r=R);
      slot_grid();
      plant_holes();
    }
    hole_spike_rings();
    border_spike_ring();
  }
}

// ─── Segmenting ───────────────────────────────────────────────────────────────

seg_w = panel_diameter / segments_x;
seg_l = panel_diameter / segments_y;

module segment(si_x, si_y) {
  x0 = si_x * seg_w;
  y0 = si_y * seg_l;
  intersection() {
    full_panel();
    translate([x0, y0, 0])
      cube([seg_w, seg_l, panel_thickness + max_spike_height + eps]);
  }
}

// ─── Top-level render ─────────────────────────────────────────────────────────

if (segment_to_print == 0) {
  preview_gap = (segments_x > 1 || segments_y > 1) ? 2 : 0;
  total_w = panel_diameter + (segments_x - 1) * preview_gap;
  total_l = panel_diameter + (segments_y - 1) * preview_gap;
  translate([-total_w / 2, -total_l / 2, 0])for (si_x = [0:segments_x - 1])
    for (si_y = [0:segments_y - 1])
      translate([si_x * preview_gap, si_y * preview_gap, 0])
        segment(si_x, si_y);
} else {
  idx = segment_to_print - 1;
  si_x = idx % segments_x;
  si_y = floor(idx / segments_x);
  translate([-seg_w / 2, -seg_l / 2, 0])
    segment(si_x, si_y);
}

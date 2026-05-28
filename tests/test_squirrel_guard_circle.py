# type: ignore
"""
Test suite for circular-squirrel-guard.scad
============================================
All placement logic is ported to Python so tests run without OpenSCAD.
Variable names and logic match the .scad file exactly.

Structure
---------
GEOMETRY MIRRORS   — pure functions that replicate the .scad maths
SIMULATION         — full spike/slot build using default parameters
UNIT TESTS         — isolated tests for each geometry primitive
INTEGRATION TESTS  — full-panel checks against the simulation

Run with:  pytest test_squirrel_guard_circle.py -v
"""

import math

import pytest

# =============================================================================
# GEOMETRY MIRRORS  (parameter-explicit; no module-level globals)
# =============================================================================


def dist2sq(ax, ay, bx, by):
    """Squared distance — mirrors the .scad dist2() which returns dx²+dy², not sqrt."""
    dx, dy = ax - bx, ay - by
    return dx * dx + dy * dy


def sat_angle_rad(i, satellite_count):
    return math.radians(360 / satellite_count * i)


def dist_to_rrect(px, py, rcx, rcy, hx, hy, r):
    """
    Signed SDF from point to rounded-rectangle boundary.
    Mirror of dist_to_rrect() in the .scad file.
    Negative = inside, positive = outside.
    """
    dx = max(abs(px - rcx) - (hx - r), 0)
    dy = max(abs(py - rcy) - (hy - r), 0)
    return math.sqrt(dx * dx + dy * dy) - r


def _round_to_fold(n, fold):
    """Mirror of _round_to_fold() in the .scad file."""
    return math.ceil(max(n, 1) / fold) * fold


def slot_grid_dims(panel_diameter, border, sw, sl, slot_gap):
    """
    Mirror of SLOT_COLS/ROWS/GRID_W/GRID_L/SLOT_X0/SLOT_Y0 in the .scad file.
    Returns (cols, rows, grid_w, grid_l, slot_x0, slot_y0).
    Uses math.floor() to match OpenSCAD floor() semantics.
    """
    r = panel_diameter / 2
    pitch_x = sw + slot_gap
    pitch_y = sl + slot_gap
    span = 2 * (r - border)
    cols = max(0, math.floor((span - sw) / pitch_x) + 1)
    rows = max(0, math.floor((span - sl) / pitch_y) + 1)
    grid_w = (cols - 1) * pitch_x if cols > 0 else 0
    grid_l = (rows - 1) * pitch_y if rows > 0 else 0
    slot_x0 = r - grid_w / 2
    slot_y0 = r - grid_l / 2
    return cols, rows, grid_w, grid_l, slot_x0, slot_y0


def eff_clearances(p):
    """
    Compute effective slot clearances around each hole type.
    Mirror of _eff_center_clear / _eff_satellite_clear in the .scad file.
    Returns (eff_center_clear, eff_satellite_clear).
    """
    min_c = (
        (p["center_spike_clearance"] + p["center_spike_base"])
        if p["center_spikes_enabled"]
        else 0
    )
    min_s = (
        (p["satellite_spike_clearance"] + p["satellite_spike_base"])
        if p["satellite_spikes_enabled"]
        else 0
    )
    return max(p["center_hole_clearance"], min_c), max(
        p["satellite_hole_clearance"], min_s
    )


def compute_orbit(p, eff_center_clear):
    """Mirror of the orbit derived value in the .scad file."""
    if p["satellite_orbit_radius"] > 0:
        return p["satellite_orbit_radius"]
    center_edge = (
        (p["center_hole_radius"] + eff_center_clear) if p["center_hole_enabled"] else 0
    )
    panel_inner = p["panel_diameter"] / 2 - p["border"]
    return (center_edge + panel_inner) / 2


def overlaps_center(sx, sy, cx, cy, p, eff_center_clear, slot_half_max):
    if not p["center_hole_enabled"]:
        return False
    thresh = p["center_hole_radius"] + eff_center_clear + slot_half_max
    return dist2sq(sx, sy, cx, cy) < thresh * thresh


def overlaps_satellite(sx, sy, cx, cy, p, eff_satellite_clear, slot_half_max, orbit):
    if not p["satellite_holes_enabled"]:
        return False
    thresh2 = (p["satellite_hole_radius"] + eff_satellite_clear + slot_half_max) ** 2
    for i in range(p["satellite_count"]):
        a = sat_angle_rad(i, p["satellite_count"])
        if (
            dist2sq(sx, sy, cx + orbit * math.cos(a), cy + orbit * math.sin(a))
            < thresh2
        ):
            return True
    return False


def slot_in_circle(sx, sy, cx, cy, inner_r, slot_half_max):
    _r = inner_r - slot_half_max
    return dist2sq(sx, sy, cx, cy) <= _r * _r


def spike_in_panel(sx, sy, cx, cy, inner_r, b):
    _r = inner_r - b / 2
    return dist2sq(sx, sy, cx, cy) <= _r * _r


def spike_hits_center(sx, sy, cx, cy, p, c, b):
    if not p["center_hole_enabled"]:
        return False
    _t = p["center_hole_radius"] + c + b / 2
    return dist2sq(sx, sy, cx, cy) < _t * _t


def spike_hits_satellite(sx, sy, cx, cy, p, c, b, orbit):
    if not p["satellite_holes_enabled"]:
        return False
    thresh2 = (p["satellite_hole_radius"] + c + b / 2) ** 2
    for i in range(p["satellite_count"]):
        a = sat_angle_rad(i, p["satellite_count"])
        if (
            dist2sq(sx, sy, cx + orbit * math.cos(a), cy + orbit * math.sin(a))
            < thresh2
        ):
            return True
    return False


def spike_self_collides(sx, sy, b, placed):
    return any(dist2sq(sx, sy, p[0], p[1]) < (b + p[2]) ** 2 / 4 for p in placed)


def spike_placeable(sx, sy, c, b, placed, cx, cy, inner_r, p, orbit, skip_center=False):
    """
    Mirror of spike_placeable() in the .scad file.
    spike_priority=True (the default) means slots yield to spikes, so the slot
    overlap check is skipped here — only boundary, hole keepouts, and self-collision matter.
    skip_center=True is used when placing the center hole ring itself.
    """
    if not spike_in_panel(sx, sy, cx, cy, inner_r, b):
        return False
    if not skip_center and spike_hits_center(sx, sy, cx, cy, p, c, b):
        return False
    if spike_hits_satellite(sx, sy, cx, cy, p, c, b, orbit):
        return False
    return not spike_self_collides(sx, sy, b, placed)


def border_spike_placeable(sx, sy, b, placed, cx, cy, inner_r):
    """
    Mirror of border_spike_placeable() in the .scad file.
    Border spikes skip hole keepouts — only panel boundary and self-collision checked.
    spike_priority=True (the default) also skips slot overlap, so no slot args needed.
    """
    if not spike_in_panel(sx, sy, cx, cy, inner_r, b):
        return False
    return not spike_self_collides(sx, sy, b, placed)


def slot_hits_spike_sdf(slx, sly, sw, sl, spikes):
    """
    Mirror of slot_hits_any_spike() in the circular .scad file (current version).
    Uses dist_to_rrect SDF — avoids AABB false positives at spike corners.
    """
    shx, shy, sr = sw / 2, sl / 2, min(sw, sl) / 2
    return any(dist_to_rrect(p[0], p[1], slx, sly, shx, shy, sr) < p[2] / 2 for p in spikes)


def slot_hits_spike_aabb(slx, sly, sw, sl, spikes):
    """Pre-SDF AABB version — retained for regression comparisons only."""
    return any(
        abs(slx - sp[0]) < sw / 2 + sp[2] / 2 and abs(sly - sp[1]) < sl / 2 + sp[2] / 2
        for sp in spikes
    )


# =============================================================================
# SIMULATION  (default .scad parameters)
# Runs once at import time; all integration tests read these results.
# =============================================================================

P = dict(
    panel_diameter=215,
    panel_thickness=3,
    border=2,
    slot_width=6,
    slot_length=12,
    slot_gap=2.5,
    slot_axis=0,
    center_hole_enabled=True,
    center_hole_radius=25,
    center_hole_clearance=1,
    satellite_holes_enabled=True,
    satellite_count=6,
    satellite_hole_radius=22,
    satellite_hole_clearance=0,
    satellite_orbit_radius=0,
    center_spikes_enabled=True,
    center_spike_shape=0,
    center_spike_height=20,
    center_spike_base=4,
    center_spike_count=6,
    center_spike_clearance=1,
    satellite_spikes_enabled=True,
    satellite_spike_shape=0,
    satellite_spike_height=20,
    satellite_spike_base=4,
    satellite_spike_count=6,
    satellite_spike_clearance=1,
    border_spikes_enabled=True,
    border_spike_shape=0,
    border_spike_height=25,
    border_spike_base=8,
    border_spike_count=18,
    border_spike_margin=6,
    spike_priority=True,
    gtol=0.01,
)


def _build_simulation(p):
    sw = p["slot_width"] if p["slot_axis"] == 0 else p["slot_length"]
    sl = p["slot_length"] if p["slot_axis"] == 0 else p["slot_width"]
    pitch_x = sw + p["slot_gap"]
    pitch_y = sl + p["slot_gap"]
    slot_half_max = max(sw, sl) / 2

    R = p["panel_diameter"] / 2
    cx = cy = R
    inner_r = R - p["border"]
    gtol = p["gtol"]

    eff_c, eff_s = eff_clearances(p)
    orbit = compute_orbit(p, eff_c)

    cols, rows, grid_w, grid_l, slot_x0, slot_y0 = slot_grid_dims(
        p["panel_diameter"], p["border"], sw, sl, p["slot_gap"]
    )

    # ── center hole spike ring ──
    center_acc = []
    if p["center_spikes_enabled"] and p["center_hole_enabled"]:
        ring_r = (
            p["center_hole_radius"]
            + p["center_spike_clearance"]
            + p["center_spike_base"] / 2
            + gtol
        )
        n = max(1, p["center_spike_count"])
        a_step = 2 * math.pi / n
        for i in range(n):
            sx = cx + ring_r * math.cos(i * a_step)
            sy = cy + ring_r * math.sin(i * a_step)
            if spike_placeable(
                sx,
                sy,
                p["center_spike_clearance"],
                p["center_spike_base"],
                center_acc,
                cx,
                cy,
                inner_r,
                p,
                orbit,
                skip_center=True,
            ):
                center_acc.append((sx, sy, p["center_spike_base"], 0))

    # ── satellite hole spike rings — each ring uses its own accumulator (mirrors .scad) ──
    sat_acc = []
    if p["satellite_spikes_enabled"] and p["satellite_holes_enabled"]:
        for i in range(p["satellite_count"]):
            a = sat_angle_rad(i, p["satellite_count"])
            hcx = cx + orbit * math.cos(a)
            hcy = cy + orbit * math.sin(a)
            ring_r = (
                p["satellite_hole_radius"]
                + p["satellite_spike_clearance"]
                + p["satellite_spike_base"] / 2
                + gtol
            )
            n = max(1, p["satellite_spike_count"])
            a_step_s = 2 * math.pi / n
            ring_acc = []
            for j in range(n):
                sx = hcx + ring_r * math.cos(j * a_step_s)
                sy = hcy + ring_r * math.sin(j * a_step_s)
                if spike_placeable(
                    sx,
                    sy,
                    p["satellite_spike_clearance"],
                    p["satellite_spike_base"],
                    ring_acc,
                    cx,
                    cy,
                    inner_r,
                    p,
                    orbit,
                    skip_center=False,
                ):
                    ring_acc.append((sx, sy, p["satellite_spike_base"], 1))
            sat_acc.extend(ring_acc)

    hole_acc = center_acc + sat_acc

    # ── border spike ring ──
    border_acc = []
    if p["border_spikes_enabled"]:
        fold = p["satellite_count"] if p["satellite_holes_enabled"] else 1
        n_border = _round_to_fold(p["border_spike_count"], fold)
        ring_r = inner_r - p["border_spike_margin"]
        a_step_b = 2 * math.pi / n_border
        for i in range(n_border):
            sx = cx + ring_r * math.cos(i * a_step_b)
            sy = cy + ring_r * math.sin(i * a_step_b)
            if border_spike_placeable(
                sx, sy, p["border_spike_base"], border_acc, cx, cy, inner_r
            ):
                border_acc.append((sx, sy, p["border_spike_base"], 2))

    all_spikes = hole_acc + border_acc

    # ── slot grid ──
    n_slots = skipped = violations = 0
    for c in range(cols):
        for r in range(rows):
            sx = slot_x0 + c * pitch_x
            sy = slot_y0 + r * pitch_y
            if not slot_in_circle(sx, sy, cx, cy, inner_r, slot_half_max):
                continue
            if overlaps_center(
                sx, sy, cx, cy, p, eff_c, slot_half_max
            ) or overlaps_satellite(sx, sy, cx, cy, p, eff_s, slot_half_max, orbit):
                continue
            hits = slot_hits_spike_sdf(sx, sy, sw, sl, all_spikes)
            if p["spike_priority"] and hits:
                skipped += 1
            elif not hits:
                n_slots += 1
            else:
                violations += 1

    return dict(
        sw=sw,
        sl=sl,
        pitch_x=pitch_x,
        pitch_y=pitch_y,
        slot_half_max=slot_half_max,
        R=R,
        cx=cx,
        cy=cy,
        inner_r=inner_r,
        eff_center_clear=eff_c,
        eff_satellite_clear=eff_s,
        orbit=orbit,
        cols=cols,
        rows=rows,
        slot_x0=slot_x0,
        slot_y0=slot_y0,
        center_acc=center_acc,
        sat_acc=sat_acc,
        hole_acc=hole_acc,
        border_acc=border_acc,
        all_spikes=all_spikes,
        n_slots=n_slots,
        skipped=skipped,
        violations=violations,
    )


SIM = _build_simulation(P)


# =============================================================================
# UNIT TESTS — geometry primitives
# =============================================================================


class TestDist2sq:
    def test_pythagorean(self):
        assert abs(dist2sq(0, 0, 3, 4) - 25.0) < 1e-9

    def test_same_point(self):
        assert dist2sq(5, 5, 5, 5) == 0

    def test_symmetry(self):
        assert dist2sq(1, 2, 5, 6) == dist2sq(5, 6, 1, 2)


class TestDistToRrect:
    def test_centre_is_negative(self):
        assert dist_to_rrect(0, 0, 0, 0, 5, 10, 2) < 0

    def test_far_outside_is_positive(self):
        assert dist_to_rrect(100, 100, 0, 0, 5, 10, 2) > 0

    def test_on_flat_long_face_is_zero(self):
        # rrect centred at origin, hx=3, hy=6, r=3 → flat face at x=3
        assert abs(dist_to_rrect(3, 0, 0, 0, 3, 6, 3)) < 1e-9

    def test_on_short_flat_face_is_zero(self):
        assert abs(dist_to_rrect(0, 6, 0, 0, 3, 6, 3)) < 1e-9


class TestRoundToFold:
    def test_already_multiple(self):
        assert _round_to_fold(18, 6) == 18

    def test_rounds_up(self):
        assert _round_to_fold(19, 6) == 24

    def test_zero_becomes_one_fold(self):
        assert _round_to_fold(0, 6) == 6

    def test_fold_one_is_identity(self):
        assert _round_to_fold(7, 1) == 7

    def test_negative_becomes_one_fold(self):
        assert _round_to_fold(-5, 4) == 4


class TestSlotGridDims:
    def test_default_params_positive_cols_rows(self):
        cols, rows, *_ = slot_grid_dims(215, 2, 6, 12, 2.5)
        assert cols > 0 and rows > 0

    def test_expected_cols_rows(self):
        # SLOT_SPAN=211, (211-6)/8.5=24.12→floor=24→+1=25; (211-12)/14.5=13.72→+1=14
        cols, rows, *_ = slot_grid_dims(215, 2, 6, 12, 2.5)
        assert cols == 25 and rows == 14

    def test_panel_too_small_gives_zero_cols(self):
        border, sw, sl, gap = 5, 10, 20, 3
        diam = 2 * (border + sw / 2 - 0.1)  # span < sw → no slots
        cols, *_ = slot_grid_dims(diam, border, sw, sl, gap)
        assert cols == 0

    def test_zero_cols_gives_zero_grid_w(self):
        border, sw, sl, gap = 5, 10, 20, 3
        diam = 2 * (border + sw / 2 - 0.1)
        _, _, grid_w, *_ = slot_grid_dims(diam, border, sw, sl, gap)
        assert grid_w == 0

    def test_cols_rows_never_negative(self):
        for diam in [5, 10, 20]:
            cols, rows, *_ = slot_grid_dims(diam, 3, 8, 14, 2)
            assert cols >= 0 and rows >= 0

    def test_slot_x0_equals_R_minus_half_grid_w(self):
        cols, rows, grid_w, grid_l, slot_x0, slot_y0 = slot_grid_dims(
            215, 2, 6, 12, 2.5
        )
        r = 215 / 2
        assert abs(slot_x0 - (r - grid_w / 2)) < 1e-9
        assert abs(slot_y0 - (r - grid_l / 2)) < 1e-9

    def test_floor_semantics_match_openscad(self):
        """int() truncates toward zero; math.floor() truncates toward -inf (OpenSCAD uses floor)."""
        border, sw, sl, gap = 5, 10, 20, 3
        diam = 2 * (border + sw / 2 - 0.1)
        span = diam - 2 * border
        pitch_x = sw + gap
        cols_floor = math.floor((span - sw) / pitch_x) + 1  # correct: ≤0
        cols_int = int((span - sw) / pitch_x) + 1  # wrong: >0
        assert cols_floor <= 0
        assert cols_int > 0


class TestEffClearances:
    def test_default_uses_spike_ring_dims_for_center(self):
        eff_c, _ = eff_clearances(P)
        # min_c = clearance + base = 1 + 4 = 5; center_hole_clearance = 1 → max(1,5) = 5
        assert eff_c == 5

    def test_default_uses_spike_ring_dims_for_satellite(self):
        _, eff_s = eff_clearances(P)
        # satellite_hole_clearance = 0, min_s = 1 + 4 = 5 → max(0,5) = 5
        assert eff_s == 5

    def test_spikes_disabled_uses_raw_clearance(self):
        params = {
            **P,
            "center_spikes_enabled": False,
            "satellite_spikes_enabled": False,
        }
        eff_c, eff_s = eff_clearances(params)
        assert eff_c == P["center_hole_clearance"]
        assert eff_s == P["satellite_hole_clearance"]


class TestComputeOrbit:
    def test_auto_orbit_is_midpoint(self):
        eff_c, _ = eff_clearances(P)
        orbit = compute_orbit(P, eff_c)
        # center_edge = 25+5=30; panel_inner = 107.5-2 = 105.5; midpoint = 67.75
        assert abs(orbit - 67.75) < 1e-9

    def test_explicit_orbit_overrides_auto(self):
        params = {**P, "satellite_orbit_radius": 50}
        eff_c, _ = eff_clearances(params)
        assert compute_orbit(params, eff_c) == 50

    def test_orbit_between_center_edge_and_panel_inner(self):
        eff_c, _ = eff_clearances(P)
        orbit = compute_orbit(P, eff_c)
        center_edge = P["center_hole_radius"] + eff_c
        panel_inner = P["panel_diameter"] / 2 - P["border"]
        assert center_edge < orbit < panel_inner


class TestSlotInCircle:
    cx = cy = 107.5
    inner_r = 105.5
    slot_half_max = 6  # max(sw=6, sl=12) / 2

    def test_centre_fits(self):
        assert slot_in_circle(
            self.cx, self.cy, self.cx, self.cy, self.inner_r, self.slot_half_max
        )

    def test_at_edge_rejected(self):
        assert not slot_in_circle(
            self.cx + self.inner_r,
            self.cy,
            self.cx,
            self.cy,
            self.inner_r,
            self.slot_half_max,
        )

    def test_just_inside_boundary(self):
        sx = self.cx + self.inner_r - self.slot_half_max - 0.1
        assert slot_in_circle(
            sx, self.cy, self.cx, self.cy, self.inner_r, self.slot_half_max
        )

    def test_just_outside_boundary(self):
        sx = self.cx + self.inner_r - self.slot_half_max + 0.1
        assert not slot_in_circle(
            sx, self.cy, self.cx, self.cy, self.inner_r, self.slot_half_max
        )


class TestSpikeInPanel:
    cx = cy = 107.5
    inner_r = 105.5

    def test_at_panel_centre(self):
        assert spike_in_panel(self.cx, self.cy, self.cx, self.cy, self.inner_r, 4)

    def test_outside_panel(self):
        assert not spike_in_panel(
            self.cx + self.inner_r, self.cy, self.cx, self.cy, self.inner_r, 4
        )

    def test_just_within_boundary(self):
        b = 4
        sx = self.cx + self.inner_r - b / 2 - 0.1
        assert spike_in_panel(sx, self.cy, self.cx, self.cy, self.inner_r, b)

    def test_just_outside_boundary(self):
        b = 4
        sx = self.cx + self.inner_r - b / 2 + 0.1
        assert not spike_in_panel(sx, self.cy, self.cx, self.cy, self.inner_r, b)


class TestSpikeHitsCenter:
    cx = cy = 107.5

    def test_at_centre_hits(self):
        assert spike_hits_center(self.cx, self.cy, self.cx, self.cy, P, 1, 4)

    def test_far_misses(self):
        assert not spike_hits_center(self.cx + 100, self.cy, self.cx, self.cy, P, 1, 4)

    def test_just_inside_threshold_hits(self):
        c, b = 1, 4
        thresh = P["center_hole_radius"] + c + b / 2  # 25 + 1 + 2 = 28
        sx = self.cx + thresh - 1
        assert spike_hits_center(sx, self.cy, self.cx, self.cy, P, c, b)

    def test_just_outside_threshold_misses(self):
        c, b = 1, 4
        thresh = P["center_hole_radius"] + c + b / 2
        sx = self.cx + thresh + 1
        assert not spike_hits_center(sx, self.cy, self.cx, self.cy, P, c, b)

    def test_disabled_always_misses(self):
        params = {**P, "center_hole_enabled": False}
        assert not spike_hits_center(self.cx, self.cy, self.cx, self.cy, params, 1, 4)


class TestSpikeSelfCollides:
    def test_no_placed_no_collision(self):
        assert not spike_self_collides(0, 0, 4, [])

    def test_same_position_collides(self):
        assert spike_self_collides(0, 0, 4, [(0, 0, 4, 0)])

    def test_far_enough_no_collision(self):
        assert not spike_self_collides(10, 0, 4, [(0, 0, 4, 0)])

    def test_threshold_is_sum_of_bases_halved(self):
        # dist2sq < (b + p[2])^2 / 4 → collision when dist < (4+4)/2 = 4
        placed = [(0, 0, 4, 0)]
        assert spike_self_collides(3.9, 0, 4, placed)
        assert not spike_self_collides(4.1, 0, 4, placed)


class TestSlotHitsSpikeSDF:
    """
    Documents the SDF vs AABB difference and confirms the SDF fix is correct.
    With default panel params both give the same slot count, but AABB still
    fires false positives at spike corners — suppressing valid slots in those zones.
    """

    SW, SL, B = 6, 12, 6

    def _sp(self, x, y, b=None):
        return [(x, y, b or self.B, 0)]

    def test_centre_hit_both_agree(self):
        sp = self._sp(50, 50)
        assert slot_hits_spike_sdf(50, 50, self.SW, self.SL, sp)
        assert slot_hits_spike_aabb(50, 50, self.SW, self.SL, sp)

    def test_far_miss_both_agree(self):
        sp = self._sp(500, 500)
        assert not slot_hits_spike_sdf(10, 10, self.SW, self.SL, sp)
        assert not slot_hits_spike_aabb(10, 10, self.SW, self.SL, sp)

    def test_diagonal_corner_aabb_false_positive(self):
        """AABB fires at a spike diagonally past the slot corner; SDF correctly rejects it."""
        sx, sy, b = 50, 50, self.B
        sp = [(sx + self.SW / 2 + b / 2 - 0.1, sy + self.SL / 2 + b / 2 - 0.1, b, 0)]
        assert slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp), "AABB must flag corner"
        assert not slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp), "SDF must reject corner"

    def test_flat_face_both_agree_hit(self):
        sx, sy, b = 50, 50, self.B
        sr = min(self.SW, self.SL) / 2
        sp = [(sx + self.SW / 2 - sr + b / 2 - 0.5, sy, b, 0)]
        assert slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp)
        assert slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp)

    def test_sdf_never_false_negative_on_cardinal_axes(self):
        """On-axis hits accepted by AABB must also be accepted by SDF."""
        sx, sy, b = 100, 100, self.B
        for offset in [0, self.SW / 4, self.SW / 2 + b / 2 - 1]:
            sp = [(sx + offset, sy, b, 0)]
            if slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp):
                assert slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp), (
                    f"SDF false negative at x-offset={offset}"
                )

    def test_sdf_strictly_tighter_at_corners(self):
        """SDF must never produce more hits than AABB; corners show at least one AABB over-fire."""
        sx, sy, b = 50, 50, self.B
        fn = fp = 0
        for dx in [-self.SW / 2 - b / 2 + 0.1, 0, self.SW / 2 + b / 2 - 0.1]:
            for dy in [-self.SL / 2 - b / 2 + 0.1, 0, self.SL / 2 + b / 2 - 0.1]:
                sp = [(sx + dx, sy + dy, b, 0)]
                sdf = slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp)
                aabb = slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp)
                if aabb and not sdf:
                    fp += 1
                if sdf and not aabb:
                    fn += 1
        assert fn == 0, "SDF must not fire without AABB"
        assert fp > 0, "Expected at least one AABB false positive at corners"


# =============================================================================
# INTEGRATION TESTS — full default-parameter simulation
# =============================================================================


class TestDerivedValues:
    def test_R_and_centre(self):
        assert SIM["R"] == 107.5
        assert SIM["cx"] == SIM["cy"] == 107.5

    def test_inner_r(self):
        assert abs(SIM["inner_r"] - 105.5) < 1e-9

    def test_orbit_value(self):
        assert abs(SIM["orbit"] - 67.75) < 1e-9

    def test_eff_center_clear(self):
        assert SIM["eff_center_clear"] == 5

    def test_eff_satellite_clear(self):
        assert SIM["eff_satellite_clear"] == 5

    def test_orbit_between_center_edge_and_inner_r(self):
        center_edge = P["center_hole_radius"] + SIM["eff_center_clear"]
        assert center_edge < SIM["orbit"] < SIM["inner_r"]


class TestSlotGridIntegration:
    def test_positive_cols_rows(self):
        assert SIM["cols"] > 0 and SIM["rows"] > 0

    def test_expected_cols_rows(self):
        assert SIM["cols"] == 25
        assert SIM["rows"] == 14

    def test_slot_x0_y0_within_panel(self):
        r = SIM["R"]
        assert 0 < SIM["slot_x0"] < r
        assert 0 < SIM["slot_y0"] < r

    def test_slots_rendered(self):
        assert SIM["n_slots"] > 0

    def test_expected_slot_count(self):
        assert SIM["n_slots"] == 66

    def test_no_slot_spike_violations(self):
        assert SIM["violations"] == 0


class TestSpikeCounts:
    def test_center_spike_count_expected(self):
        # ring_r=28.01, n=6, all fit within panel and clear satellite keepouts
        assert len(SIM["center_acc"]) == 6

    def test_sat_spike_count_expected(self):
        # 6 satellites × 6 spikes each, all fit (orbit±ring_r within inner_r)
        assert len(SIM["sat_acc"]) == 36

    def test_border_spike_count_expected(self):
        # _round_to_fold(18, 6)=18, ring_r=99.5, all within panel, no self-collisions
        assert len(SIM["border_acc"]) == 18

    def test_total_spike_count(self):
        assert len(SIM["all_spikes"]) == 60

    def test_center_spike_count_at_most_requested(self):
        assert len(SIM["center_acc"]) <= P["center_spike_count"]

    def test_sat_spike_count_at_most_requested(self):
        assert len(SIM["sat_acc"]) <= P["satellite_spike_count"] * P["satellite_count"]

    def test_center_spikes_type_0(self):
        assert all(p[3] == 0 for p in SIM["center_acc"])

    def test_sat_spikes_type_1(self):
        assert all(p[3] == 1 for p in SIM["sat_acc"])

    def test_border_spikes_type_2(self):
        assert all(p[3] == 2 for p in SIM["border_acc"])


class TestSpikePlacement:
    def test_all_spikes_within_panel(self):
        r, inner_r = SIM["R"], SIM["inner_r"]
        bad = [
            p
            for p in SIM["all_spikes"]
            if not spike_in_panel(p[0], p[1], r, r, inner_r, p[2])
        ]
        assert not bad, f"{len(bad)} spikes outside panel"

    def test_no_spike_inside_center_hole(self):
        cx = SIM["R"]
        hole_r = P["center_hole_radius"]
        bad = [p for p in SIM["all_spikes"] if dist2sq(p[0], p[1], cx, cx) < hole_r * hole_r]
        assert not bad, f"{len(bad)} spikes inside center hole"

    def test_no_spike_inside_any_satellite_hole(self):
        cx = SIM["R"]
        orbit = SIM["orbit"]
        hole_r = P["satellite_hole_radius"]
        bad = []
        for sp in SIM["all_spikes"]:
            for i in range(P["satellite_count"]):
                a = sat_angle_rad(i, P["satellite_count"])
                if dist2sq(sp[0], sp[1], cx + orbit * math.cos(a), cx + orbit * math.sin(a)) < hole_r * hole_r:
                    bad.append(sp)
        assert not bad, f"{len(bad)} spikes inside satellite holes"

    def test_center_ring_no_self_collision(self):
        spikes = SIM["center_acc"]
        pairs = [
            (i, j)
            for i in range(len(spikes))
            for j in range(i + 1, len(spikes))
            if dist2sq(*spikes[i][:2], *spikes[j][:2])
            < (spikes[i][2] + spikes[j][2]) ** 2 / 4
        ]
        assert not pairs, f"{len(pairs)} center spike collisions"

    def test_border_ring_no_self_collision(self):
        spikes = SIM["border_acc"]
        pairs = [
            (i, j)
            for i in range(len(spikes))
            for j in range(i + 1, len(spikes))
            if dist2sq(*spikes[i][:2], *spikes[j][:2])
            < (spikes[i][2] + spikes[j][2]) ** 2 / 4
        ]
        assert not pairs, f"{len(pairs)} border spike collisions"


class TestrotationalSymmetry:
    """Border spike ring must have satellite_count-fold rotational symmetry."""

    def test_border_ring_6fold_symmetry(self):
        spikes = [(p[0], p[1]) for p in SIM["border_acc"]]
        r = SIM["R"]
        if not spikes:
            pytest.skip("no border spikes")
        fold = P["satellite_count"]
        a_step = 2 * math.pi / fold
        p0 = spikes[0]
        for k in range(1, fold):
            dx, dy = p0[0] - r, p0[1] - r
            rx = r + dx * math.cos(k * a_step) - dy * math.sin(k * a_step)
            ry = r + dx * math.sin(k * a_step) + dy * math.cos(k * a_step)
            nearest_d = min(math.sqrt(dist2sq(rx, ry, s[0], s[1])) for s in spikes)
            assert nearest_d < 2.0, (
                f"No counterpart within 2mm at {k}×{math.degrees(a_step):.0f}°"
            )

    def test_center_ring_6fold_symmetry(self):
        spikes = [(p[0], p[1]) for p in SIM["center_acc"]]
        r = SIM["R"]
        if not spikes:
            pytest.skip("no center spikes")
        fold = P["center_spike_count"]
        a_step = 2 * math.pi / fold
        p0 = spikes[0]
        for k in range(1, fold):
            dx, dy = p0[0] - r, p0[1] - r
            rx = r + dx * math.cos(k * a_step) - dy * math.sin(k * a_step)
            ry = r + dx * math.sin(k * a_step) + dy * math.cos(k * a_step)
            nearest_d = min(math.sqrt(dist2sq(rx, ry, s[0], s[1])) for s in spikes)
            assert nearest_d < 2.0, (
                f"No counterpart within 2mm at {k}×{math.degrees(a_step):.0f}°"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

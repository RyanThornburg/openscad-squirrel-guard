# type: ignore
"""
Test suite for squirrel_guard_rect_6.scad
==========================================
All placement logic is ported to Python so tests run without OpenSCAD.
Variable names and logic match the .scad file exactly.

Structure
---------
GEOMETRY MIRRORS   — pure functions that replicate the .scad maths
SIMULATION         — full spike/slot build using default parameters
UNIT TESTS         — isolated tests for each geometry primitive / fix
INTEGRATION TESTS  — full-panel checks against the simulation

Run with:  pytest test_squirrel_guard_rect_6.py -v
"""

import math
from collections import Counter

import pytest

# =============================================================================
# GEOMETRY MIRRORS  (all parameter-explicit; no module-level globals)
# =============================================================================

# ── Basic maths ───────────────────────────────────────────────────────────────


def dist2sq(ax, ay, bx, by):
    dx, dy = ax - bx, ay - by
    return dx * dx + dy * dy


def hole_x(idx, count, r, panel_width):
    """
    X position of hole [idx] in a row of [count] holes of radius r,
    spaced so the gap between hole EDGES is equal on all sides.
    equal_gap = (panel_width - 2*count*r) / (count+1)
    centre_x  = r + equal_gap*(idx+1) + 2*r*idx
    When r=0 reduces to the old panel_width/(count+1)*(idx+1).
    """
    gap = (panel_width - 2 * count * r) / (count + 1)
    return r + gap * (idx + 1) + 2 * r * idx


def front_hole_x(idx, params):
    return hole_x(
        idx,
        params["front_hole_count"],
        params["front_hole_radius"],
        params["panel_width"],
    )


def back_hole_x(idx, params):
    return hole_x(
        idx,
        params["back_hole_count"],
        params["back_hole_radius"],
        params["panel_width"],
    )


def dist_to_rrect(px, py, rcx, rcy, hx, hy, r):
    """
    Signed distance from point (px,py) to rounded-rectangle boundary.
    Centre (rcx,rcy), half-extents (hx,hy), corner radius r.
    Negative = inside, positive = outside.
    Mirror of dist_to_rrect() in the .scad file.
    """
    dx = max(abs(px - rcx) - (hx - r), 0)
    dy = max(abs(py - rcy) - (hy - r), 0)
    return math.sqrt(dx * dx + dy * dy) - r


# ── Slot grid (v6: underflow-guarded) ────────────────────────────────────────


def slot_grid_dims(panel_width, panel_length, border, sw, sl, slot_gap):
    """
    Mirror of _cols/_rows/_grid_w/_grid_l/SLOT_X0/SLOT_Y0 in v6.
    Uses math.floor (not int()) to match OpenSCAD's floor() semantics.
    Returns (cols, rows, grid_w, grid_l, slot_x0, slot_y0).
    """
    pitch_x = sw + slot_gap
    pitch_y = sl + slot_gap
    interior_w = panel_width - 2 * border
    interior_l = panel_length - 2 * border
    cols = max(0, math.floor((interior_w - sw) / pitch_x) + 1)
    rows = max(0, math.floor((interior_l - sl) / pitch_y) + 1)
    grid_w = (cols - 1) * pitch_x if cols > 0 else 0
    grid_l = (rows - 1) * pitch_y if rows > 0 else 0
    slot_x0 = border + (interior_w - grid_w) / 2
    slot_y0 = border + (interior_l - grid_l) / 2
    return cols, rows, grid_w, grid_l, slot_x0, slot_y0


# ── Slot collision tests ──────────────────────────────────────────────────────


def slot_overlaps_hole(
    sx, sy, sw, sl, hole_radius, eff_clearance, hole_count, hole_row_y, panel_width
):
    thresh2 = (hole_radius + eff_clearance + max(sw, sl) / 2) ** 2
    return any(
        dist2sq(sx, sy, hole_x(i, hole_count, hole_radius, panel_width), hole_row_y)
        < thresh2
        for i in range(hole_count)
    )


def slot_fits_panel(sx, sy, sw, sl, border, panel_width, panel_length):
    return (
        sx - sw / 2 >= border
        and sx + sw / 2 <= panel_width - border
        and sy - sl / 2 >= border
        and sy + sl / 2 <= panel_length - border
    )


# ── Spike placement tests ─────────────────────────────────────────────────────


def spike_in_rect(sx, sy, b, panel_width, panel_length):
    return (
        sx - b / 2 >= 0
        and sx + b / 2 <= panel_width
        and sy - b / 2 >= 0
        and sy + b / 2 <= panel_length
    )


def spike_hits_hole(sx, sy, b, hole_radius, hole_count, hole_row_y, panel_width):
    """True if spike base overlaps hole circle. Mirror of spike_hits_front/back_hole."""
    thresh2 = (hole_radius + b / 2) ** 2
    return any(
        dist2sq(sx, sy, hole_x(i, hole_count, hole_radius, panel_width), hole_row_y)
        < thresh2
        for i in range(hole_count)
    )


def spike_collides(sx, sy, b, placed):
    return any(dist2sq(sx, sy, p[0], p[1]) < (b + p[2]) ** 2 / 4 for p in placed)


def spike_placeable(
    sx,
    sy,
    b,
    placed,
    panel_width,
    panel_length,
    front_row_enabled,
    front_hole_count,
    front_hole_radius,
    front_row_y,
    back_row_enabled,
    back_hole_count,
    back_hole_radius,
    back_row_y,
):
    if not spike_in_rect(sx, sy, b, panel_width, panel_length):
        return False
    if front_row_enabled and spike_hits_hole(
        sx, sy, b, front_hole_radius, front_hole_count, front_row_y, panel_width
    ):
        return False
    if back_row_enabled and spike_hits_hole(
        sx, sy, b, back_hole_radius, back_hole_count, back_row_y, panel_width
    ):
        return False
    return not spike_collides(sx, sy, b, placed)


# ── Spike ring builder ────────────────────────────────────────────────────────


def _collect(
    pts,
    acc,
    b,
    t,
    panel_width,
    panel_length,
    front_row_enabled,
    front_hole_count,
    front_hole_radius,
    front_row_y,
    back_row_enabled,
    back_hole_count,
    back_hole_radius,
    back_row_y,
):
    for pt in pts:
        if spike_placeable(
            pt[0],
            pt[1],
            b,
            acc,
            panel_width,
            panel_length,
            front_row_enabled,
            front_hole_count,
            front_hole_radius,
            front_row_y,
            back_row_enabled,
            back_hole_count,
            back_hole_radius,
            back_row_y,
        ):
            acc = acc + [(pt[0], pt[1], b, t)]
    return acc


def hole_ring(
    hx,
    hy,
    hole_r,
    clearance,
    base,
    count,
    spike_type,
    panel_width,
    panel_length,
    front_row_enabled,
    front_hole_count,
    front_hole_radius,
    front_row_y,
    back_row_enabled,
    back_hole_count,
    back_hole_radius,
    back_row_y,
    gtol=0.01,
):
    ring_r = hole_r + clearance + base / 2 + gtol
    n = max(1, count)
    a_step = 2 * math.pi / n
    pts = [
        (hx + ring_r * math.cos(i * a_step), hy + ring_r * math.sin(i * a_step))
        for i in range(n)
    ]
    return _collect(
        pts,
        [],
        base,
        spike_type,
        panel_width,
        panel_length,
        front_row_enabled,
        front_hole_count,
        front_hole_radius,
        front_row_y,
        back_row_enabled,
        back_hole_count,
        back_hole_radius,
        back_row_y,
    )


# ── Border spike candidate generator (v6: CCW, anchored at m+b/2) ─────────────


def border_spike_candidates(
    panel_width,
    panel_length,
    border_spikes_on_length_edges,
    border_spikes_on_width_edges,
    border_spike_margin,
    border_spike_base,
):
    """
    Returns (bot, right, top, left) candidate lists in CCW order.
    Mirrors v6 _border_spike_acc candidate generation (pre-_collect).
    """
    nl = max(1, border_spikes_on_length_edges)
    nw = max(1, border_spikes_on_width_edges)
    b = border_spike_base
    m = border_spike_margin
    x0 = m + b / 2
    x1 = panel_width - m - b / 2
    y0 = m + b / 2
    y1 = panel_length - m - b / 2

    bot = [
        (x0 + (x1 - x0) / (nl - 1) * i if nl > 1 else (x0 + x1) / 2, m)
        for i in range(nl)
    ]
    right = [
        (panel_width - m, y0 + (y1 - y0) / (nw - 1) * i if nw > 1 else (y0 + y1) / 2)
        for i in range(nw)
    ]
    top = [
        (x1 - (x1 - x0) / (nl - 1) * i if nl > 1 else (x0 + x1) / 2, panel_length - m)
        for i in range(nl)
    ]
    left = [
        (m, y1 - (y1 - y0) / (nw - 1) * i if nw > 1 else (y0 + y1) / 2)
        for i in range(nw)
    ]
    return bot, right, top, left


# ── v4 spacing (regression reference only) ───────────────────────────────────


def border_spike_candidates_v4(
    panel_width,
    panel_length,
    border_spikes_on_length_edges,
    border_spikes_on_width_edges,
    border_spike_margin,
):
    nl = max(1, border_spikes_on_length_edges)
    nw = max(1, border_spikes_on_width_edges)
    m = border_spike_margin
    bot = [(panel_width / (nl + 1) * (i + 1), m) for i in range(nl)]
    top = [(panel_width / (nl + 1) * (i + 1), panel_length - m) for i in range(nl)]
    left = [(m, panel_length / (nw + 1) * (i + 1)) for i in range(nw)]
    right = [(panel_width - m, panel_length / (nw + 1) * (i + 1)) for i in range(nw)]
    return bot, top, left, right


# ── v6 slot_hits_spike (SDF) and v4/v5 AABB version ──────────────────────────


def slot_hits_spike_sdf(sx, sy, sw, sl, spikes):
    """Mirror of v6 slot_hits_spike — uses dist_to_rrect."""
    shx, shy, sr = sw / 2, sl / 2, min(sw, sl) / 2
    return any(
        dist_to_rrect(p[0], p[1], sx, sy, shx, shy, sr) < p[2] / 2 for p in spikes
    )


def slot_hits_spike_aabb(sx, sy, sw, sl, spikes):
    """Pre-v6 AABB version — retained for regression comparisons."""
    return any(
        abs(sx - p[0]) < sw / 2 + p[2] / 2 and abs(sy - p[1]) < sl / 2 + p[2] / 2
        for p in spikes
    )


# =============================================================================
# SIMULATION  (default .scad parameters, v6 logic)
# Runs once at import time; all integration tests read these results.
# =============================================================================

# ── Default parameters (match squirrel_guard_rect_6.scad) ────────────────────
P = dict(
    panel_width=350,
    panel_length=200,
    panel_thickness=3,
    border=2,
    slot_width=6,
    slot_length=12,
    slot_gap=2.5,
    slot_axis=1,  # 1 = across width (X)
    front_row_enabled=True,
    front_hole_count=5,
    front_hole_radius=20,
    front_hole_clearance=2,
    front_row_offset=-45,
    back_row_enabled=True,
    back_hole_count=1,
    back_hole_radius=40,
    back_hole_clearance=2,
    back_row_offset=20,
    front_spikes_enabled=True,
    front_spike_base=5,
    front_spike_count=8,
    front_spike_clearance=3,
    front_spike_height=12,
    front_spike_shape=0,
    back_spikes_enabled=True,
    back_spike_base=5,
    back_spike_count=8,
    back_spike_clearance=3,
    back_spike_height=12,
    back_spike_shape=0,
    border_spikes_enabled=True,
    border_spike_base=6,
    border_spike_margin=8,
    border_spike_height=15,
    border_spikes_on_length_edges=12,
    border_spikes_on_width_edges=6,
    spike_priority=True,
    gtol=0.01,
)


def _build_simulation(p):
    """Run full spike+slot simulation. Returns a dict of results."""
    sw = p["slot_length"] if p["slot_axis"] == 1 else p["slot_width"]
    sl = p["slot_width"] if p["slot_axis"] == 1 else p["slot_length"]
    pitch_x = sw + p["slot_gap"]
    pitch_y = sl + p["slot_gap"]
    pw, pl = p["panel_width"], p["panel_length"]
    panel_cy = pl / 2
    front_row_y = panel_cy + p["front_row_offset"]
    back_row_y = panel_cy + p["back_row_offset"]

    _eff_fc = max(
        p["front_hole_clearance"],
        p["front_spike_clearance"] + p["front_spike_base"]
        if p["front_spikes_enabled"]
        else p["front_hole_clearance"],
    )
    _eff_bc = max(
        p["back_hole_clearance"],
        p["back_spike_clearance"] + p["back_spike_base"]
        if p["back_spikes_enabled"]
        else p["back_hole_clearance"],
    )

    cols, rows, grid_w, grid_l, slot_x0, slot_y0 = slot_grid_dims(
        pw, pl, p["border"], sw, sl, p["slot_gap"]
    )

    # ── shared _collect kwargs ──
    ck = dict(
        panel_width=pw,
        panel_length=pl,
        front_row_enabled=p["front_row_enabled"],
        front_hole_count=p["front_hole_count"],
        front_hole_radius=p["front_hole_radius"],
        front_row_y=front_row_y,
        back_row_enabled=p["back_row_enabled"],
        back_hole_count=p["back_hole_count"],
        back_hole_radius=p["back_hole_radius"],
        back_row_y=back_row_y,
    )

    # ── hole ring spikes ──
    front_acc = []
    if p["front_row_enabled"] and p["front_spikes_enabled"]:
        for i in range(p["front_hole_count"]):
            front_acc += hole_ring(
                hole_x(i, p["front_hole_count"], p["front_hole_radius"], pw),
                front_row_y,
                p["front_hole_radius"],
                p["front_spike_clearance"],
                p["front_spike_base"],
                p["front_spike_count"],
                0,
                gtol=p["gtol"],
                **ck,
            )

    back_acc = []
    if p["back_row_enabled"] and p["back_spikes_enabled"]:
        for i in range(p["back_hole_count"]):
            back_acc += hole_ring(
                hole_x(i, p["back_hole_count"], p["back_hole_radius"], pw),
                back_row_y,
                p["back_hole_radius"],
                p["back_spike_clearance"],
                p["back_spike_base"],
                p["back_spike_count"],
                1,
                gtol=p["gtol"],
                **ck,
            )

    # ── border spikes (v6: CCW, anchored) ──
    border_acc = []
    if p["border_spikes_enabled"]:
        nl = max(1, p["border_spikes_on_length_edges"])
        nw = max(1, p["border_spikes_on_width_edges"])
        b = p["border_spike_base"]
        m = p["border_spike_margin"]
        x0 = m + b / 2
        x1 = pw - m - b / 2
        y0 = m + b / 2
        y1 = pl - m - b / 2
        bot = [
            (x0 + (x1 - x0) / (nl - 1) * i if nl > 1 else (x0 + x1) / 2, m)
            for i in range(nl)
        ]
        right = [
            (pw - m, y0 + (y1 - y0) / (nw - 1) * i if nw > 1 else (y0 + y1) / 2)
            for i in range(nw)
        ]
        top = [
            (x1 - (x1 - x0) / (nl - 1) * i if nl > 1 else (x0 + x1) / 2, pl - m)
            for i in range(nl)
        ]
        left = [
            (m, y1 - (y1 - y0) / (nw - 1) * i if nw > 1 else (y0 + y1) / 2)
            for i in range(nw)
        ]
        seed = front_acc + back_acc
        n_h = len(seed)
        full = _collect(bot + right + top + left, seed, b, 2, **ck)
        border_acc = full[n_h:]

    all_spikes = front_acc + back_acc + border_acc

    # ── slot grid (v6: SDF collision) ──
    n_slots = 0
    skipped = 0
    violations = 0
    shx, shy, sr = sw / 2, sl / 2, min(sw, sl) / 2
    for c in range(cols):
        for r in range(rows):
            sx = slot_x0 + c * pitch_x
            sy = slot_y0 + r * pitch_y
            if not slot_fits_panel(sx, sy, sw, sl, p["border"], pw, pl):
                continue
            if slot_overlaps_hole(
                sx,
                sy,
                sw,
                sl,
                p["front_hole_radius"],
                _eff_fc,
                p["front_hole_count"],
                front_row_y,
                pw,
            ) or slot_overlaps_hole(
                sx,
                sy,
                sw,
                sl,
                p["back_hole_radius"],
                _eff_bc,
                p["back_hole_count"],
                back_row_y,
                pw,
            ):
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
        front_row_y=front_row_y,
        back_row_y=back_row_y,
        _eff_fc=_eff_fc,
        _eff_bc=_eff_bc,
        cols=cols,
        rows=rows,
        slot_x0=slot_x0,
        slot_y0=slot_y0,
        front_acc=front_acc,
        back_acc=back_acc,
        border_acc=border_acc,
        all_spikes=all_spikes,
        n_slots=n_slots,
        skipped=skipped,
        violations=violations,
    )


SIM = _build_simulation(P)  # run once at import


# =============================================================================
# UNIT TESTS — geometry primitives and per-fix behaviour
# =============================================================================

# ── hole_x edge-gap spacing (v7) ─────────────────────────────────────────────


class TestHoleXSpacing:
    """
    v7 fix: hole_x now distributes by hole EDGE gap rather than centre-to-centre.
    With r=0 it must reduce to the old formula.
    With r>0 the gaps between hole edges must all be equal.
    """

    W = 350

    def test_r_zero_matches_old_formula(self):
        """r=0: new formula == panel_width/(count+1)*(idx+1)."""
        for count in [1, 2, 3, 5]:
            for idx in range(count):
                new = hole_x(idx, count, 0, self.W)
                old = self.W / (count + 1) * (idx + 1)
                assert abs(new - old) < 1e-9, (
                    f"count={count} idx={idx}: new={new:.4f} old={old:.4f}"
                )

    def test_edge_gaps_equal_two_holes(self):
        """Two holes: gap_left == gap_mid == gap_right."""
        r = 40
        for count in [2, 3, 4]:
            positions = [hole_x(i, count, r, self.W) for i in range(count)]
            edge_gaps = (
                [positions[0] - r]
                + [positions[i + 1] - positions[i] - 2 * r for i in range(count - 1)]
                + [self.W - positions[-1] - r]
            )
            assert max(edge_gaps) - min(edge_gaps) < 1e-9, (
                f"count={count} r={r}: unequal edge gaps {[f'{g:.2f}' for g in edge_gaps]}"
            )

    def test_old_formula_produces_unequal_edge_gaps(self):
        """Confirm the v4/v6 formula gave unequal edge gaps (regression proof)."""
        r, count = 40, 2
        positions_old = [self.W / (count + 1) * (i + 1) for i in range(count)]
        edge_gaps_old = (
            [positions_old[0] - r]
            + [
                positions_old[i + 1] - positions_old[i] - 2 * r
                for i in range(count - 1)
            ]
            + [self.W - positions_old[-1] - r]
        )
        assert max(edge_gaps_old) - min(edge_gaps_old) > 1.0, (
            "Old formula should have unequal edge gaps"
        )

    def test_single_hole_centred(self):
        """count=1: hole should be centred in the panel regardless of radius."""
        for r in [10, 20, 40, 60]:
            x = hole_x(0, 1, r, self.W)
            assert abs(x - self.W / 2) < 1e-9, (
                f"r={r}: expected centre {self.W / 2}, got {x:.4f}"
            )

    def test_first_hole_edge_at_equal_gap_from_panel_edge(self):
        """First hole edge (x - r) == last hole edge from right (W - x_last - r)."""
        for count in [2, 3, 5]:
            for r in [10, 20, 40]:
                x0 = hole_x(0, count, r, self.W)
                xlast = hole_x(count - 1, count, r, self.W)
                left_gap = x0 - r
                right_gap = self.W - xlast - r
                assert abs(left_gap - right_gap) < 1e-9, (
                    f"count={count} r={r}: left={left_gap:.2f} right={right_gap:.2f}"
                )

    def test_all_holes_within_panel(self):
        """No hole should extend outside panel bounds when geometry is feasible."""
        for count in [1, 2, 3, 5]:
            for r in [10, 20, 40]:
                if 2 * count * r >= self.W:
                    continue  # geometrically impossible — skip
                for idx in range(count):
                    x = hole_x(idx, count, r, self.W)
                    assert x - r >= 0, (
                        f"count={count} r={r} idx={idx}: left edge {x - r:.1f} < 0"
                    )
                    assert x + r <= self.W, (
                        f"count={count} r={r} idx={idx}: right edge {x + r:.1f} > {self.W}"
                    )

    def test_large_radius_holes_still_fit(self):
        """Even a single large hole should stay inside the panel."""
        r = 80
        x = hole_x(0, 1, r, self.W)
        assert x - r >= 0
        assert x + r <= self.W


# ── dist_to_rrect ─────────────────────────────────────────────────────────────


class TestDistToRrect:
    """Basic SDF sanity checks — centre, inside, outside, on-boundary."""

    def test_centre_is_negative(self):
        assert dist_to_rrect(0, 0, 0, 0, 5, 10, 2) < 0

    def test_far_outside_is_positive(self):
        assert dist_to_rrect(100, 100, 0, 0, 5, 10, 2) > 0

    def test_on_flat_long_face_is_zero(self):
        # rrect centred at origin, hx=3, hy=6, r=3  → flat portion on X face at x=3
        d = dist_to_rrect(3, 0, 0, 0, 3, 6, 3)
        assert abs(d) < 1e-9

    def test_on_short_flat_face_is_zero(self):
        d = dist_to_rrect(0, 6, 0, 0, 3, 6, 3)
        assert abs(d) < 1e-9

    def test_corner_distance_matches_geometry(self):
        # Corner of rrect at (hx-r, hy-r) + circle of radius r
        hx, hy, r = 5, 10, 2
        # Point diagonally 1mm outside the corner arc
        cx, cy = hx - r, hy - r
        d = math.sqrt(2) * (r + 1)
        px = cx + (r + 1) / math.sqrt(2)
        py = cy + (r + 1) / math.sqrt(2)
        assert abs(dist_to_rrect(px, py, 0, 0, hx, hy, r) - 1.0) < 1e-6


# ── Fix 1: slot grid underflow guard ─────────────────────────────────────────


class TestSlotGridUnderflow:
    def test_default_params_positive_cols_rows(self):
        cols, rows, *_ = slot_grid_dims(350, 200, 2, 12, 6, 2.5)
        assert cols > 0 and rows > 0

    def test_panel_too_narrow_gives_zero_cols(self):
        border, sw, sl, gap = 5, 10, 20, 3
        pw = 2 * border + sw - 1  # interior_w = sw - 1  →  floor < 0
        cols, *_ = slot_grid_dims(pw, 200, border, sw, sl, gap)
        assert cols == 0

    def test_panel_too_short_gives_zero_rows(self):
        border, sw, sl, gap = 5, 10, 20, 3
        pl = 2 * border + sl - 1
        _, rows, *_ = slot_grid_dims(350, pl, border, sw, sl, gap)
        assert rows == 0

    def test_zero_cols_gives_zero_grid_w(self):
        border, sw, sl, gap = 5, 10, 20, 3
        pw = 2 * border + sw - 1
        _, _, grid_w, *_ = slot_grid_dims(pw, 200, border, sw, sl, gap)
        assert grid_w == 0

    def test_zero_rows_gives_zero_grid_l(self):
        border, sw, sl, gap = 5, 10, 20, 3
        pl = 2 * border + sl - 1
        _, _, _, grid_l, *_ = slot_grid_dims(350, pl, border, sw, sl, gap)
        assert grid_l == 0

    def test_slot_x0_finite_when_cols_zero(self):
        """SLOT_X0 must not blow up — with grid_w=0 it centres in the interior."""
        border, sw, sl, gap = 5, 10, 20, 3
        pw = 2 * border + sw - 1
        interior_w = pw - 2 * border
        _, _, _, _, x0, _ = slot_grid_dims(pw, 200, border, sw, sl, gap)
        assert abs(x0 - (border + interior_w / 2)) < 1e-9

    def test_cols_rows_never_negative(self):
        for pw in [1, 5, 10, 15]:
            cols, rows, *_ = slot_grid_dims(pw, pw, 3, 8, 14, 2)
            assert cols >= 0 and rows >= 0

    def test_floor_semantics_match_openscad(self):
        """
        Python int() truncates toward zero; math.floor() truncates toward -inf.
        OpenSCAD uses floor(). This test confirms we use floor() so the guard
        works correctly for sub-slot panel widths.
        """
        border, sw, sl, gap = 5, 10, 20, 3
        pw = 2 * border + sw - 1
        interior_w = pw - 2 * border
        pitch_x = sw + gap
        cols_floor = math.floor((interior_w - sw) / pitch_x) + 1  # correct: -1+1=0
        cols_int = int((interior_w - sw) / pitch_x) + 1  # wrong:    0+1=1
        assert cols_floor <= 0, "floor() should give ≤0 for sub-slot width"
        assert cols_int > 0, "int() would give >0 — this is the bug the fix avoids"


# ── Fix 2: slot_hits_spike SDF vs AABB ───────────────────────────────────────


class TestSlotHitsSpikeSDF:
    SW, SL, B = 6, 12, 6  # default slot/spike dims

    def _sp(self, x, y, b=None):
        return [(x, y, b or self.B)]

    def test_centre_hit_both_agree(self):
        sp = self._sp(50, 50)
        assert slot_hits_spike_sdf(50, 50, self.SW, self.SL, sp)
        assert slot_hits_spike_aabb(50, 50, self.SW, self.SL, sp)

    def test_far_miss_both_agree(self):
        sp = self._sp(500, 500)
        assert not slot_hits_spike_sdf(10, 10, self.SW, self.SL, sp)
        assert not slot_hits_spike_aabb(10, 10, self.SW, self.SL, sp)

    def test_diagonal_corner_aabb_false_positive(self):
        """
        Spike at AABB corner but outside rounded slot: AABB says hit, SDF says miss.
        This is the false positive that was suppressing valid slots before v6.
        """
        sx, sy, b = 50, 50, self.B
        sp = [(sx + self.SW / 2 + b / 2 - 0.1, sy + self.SL / 2 + b / 2 - 0.1, b)]
        assert slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp), (
            "AABB must flag corner"
        )
        assert not slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp), (
            "SDF must reject corner"
        )

    def test_flat_face_both_agree_hit(self):
        """On the straight face of the slot the two methods must agree."""
        sx, sy, b = 50, 50, self.B
        sr = min(self.SW, self.SL) / 2
        # Spike just inside the flat short-axis face
        sp = [(sx + self.SW / 2 - sr + b / 2 - 0.5, sy, b)]
        assert slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp)
        assert slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp)

    def test_sdf_never_false_negative_on_cardinal_axes(self):
        """SDF ⊆ AABB — on-axis hits accepted by AABB must also be accepted by SDF."""
        sx, sy, b = 100, 100, self.B
        for offset in [0, self.SW / 4, self.SW / 2 + b / 2 - 1]:
            sp = [(sx + offset, sy, b)]
            if slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp):
                assert slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp), (
                    f"SDF false negative at x-offset={offset}"
                )

    def test_sdf_strictly_tighter_sample(self):
        """At corner samples: SDF must never produce more hits than AABB."""
        sx, sy, b = 50, 50, self.B
        fn = fp = 0
        for dx in [-self.SW / 2 - b / 2 + 0.1, 0, self.SW / 2 + b / 2 - 0.1]:
            for dy in [-self.SL / 2 - b / 2 + 0.1, 0, self.SL / 2 + b / 2 - 0.1]:
                sp = [(sx + dx, sy + dy, b)]
                sdf = slot_hits_spike_sdf(sx, sy, self.SW, self.SL, sp)
                aabb = slot_hits_spike_aabb(sx, sy, self.SW, self.SL, sp)
                if aabb and not sdf:
                    fp += 1  # expected: AABB over-fires at corners
                if sdf and not aabb:
                    fn += 1  # forbidden: SDF must not fire alone
        assert fn == 0, "SDF produced false negatives vs AABB"
        assert fp > 0, "Expected at least one AABB false positive at corners"


# ── Fix 3: border spike spacing (v5: usable-range anchored) ──────────────────


class TestBorderSpikeSpacing:
    W, L = 350, 200
    NL, NW = 12, 6
    M, B = 8, 6

    def pos(self, **kw):
        return border_spike_candidates(
            kw.get("w", self.W),
            kw.get("l", self.L),
            kw.get("nl", self.NL),
            kw.get("nw", self.NW),
            kw.get("m", self.M),
            kw.get("b", self.B),
        )

    def test_outermost_bot_spikes_at_anchor(self):
        bot, *_ = self.pos()
        x0 = self.M + self.B / 2
        x1 = self.W - self.M - self.B / 2
        assert abs(bot[0][0] - x0) < 1e-9
        assert abs(bot[-1][0] - x1) < 1e-9

    def test_outermost_top_spikes_at_anchor(self):
        # top runs R→L so first point is x1, last is x0
        _, _, top, _ = self.pos()
        x0 = self.M + self.B / 2
        x1 = self.W - self.M - self.B / 2
        assert abs(top[0][0] - x1) < 1e-9
        assert abs(top[-1][0] - x0) < 1e-9

    def test_outermost_left_right_spikes_at_anchor(self):
        _, right, _, left = self.pos()
        y0 = self.M + self.B / 2
        y1 = self.L - self.M - self.B / 2
        assert abs(right[0][1] - y0) < 1e-9
        assert abs(right[-1][1] - y1) < 1e-9
        assert abs(left[0][1] - y1) < 1e-9  # left runs T→B
        assert abs(left[-1][1] - y0) < 1e-9

    def test_bot_evenly_spaced(self):
        bot, *_ = self.pos()
        xs = [p[0] for p in bot]
        gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
        assert max(gaps) - min(gaps) < 1e-9, f"Uneven gaps: {gaps}"

    def test_right_evenly_spaced(self):
        _, right, *_ = self.pos()
        ys = [p[1] for p in right]
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        assert max(gaps) - min(gaps) < 1e-9

    def test_nonsquare_bot_symmetric(self):
        bot, *_ = self.pos(w=500, l=150, nl=10, nw=4, m=10, b=8)
        xs = [p[0] for p in bot]
        for x in xs:
            assert any(abs(500 - x - ox) < 1e-6 for ox in xs), (
                f"x={x:.2f} has no mirror in {[round(v, 2) for v in xs]}"
            )

    def test_v4_anchor_differs_from_v6(self):
        """v4 placed first spike at panel_width/(nl+1); v6 places it at m+b/2."""
        W, NL, M, B = 500, 10, 10, 8
        bot_v4, *_ = border_spike_candidates_v4(W, 150, NL, 4, M)
        bot_v6, *_ = border_spike_candidates(W, 150, NL, 4, M, B)
        x_v4 = bot_v4[0][0]  # ≈ 45.45
        x_v6 = bot_v6[0][0]  # = m + b/2 = 14.0
        assert abs(x_v6 - (M + B / 2)) < 1e-9, f"v6 anchor wrong: {x_v6}"
        assert abs(x_v4 - x_v6) > 1.0, "v4 and v6 anchors unexpectedly equal"

    def test_single_spike_centred(self):
        bot, right, top, left = self.pos(nl=1, nw=1)
        xmid = self.W / 2
        ymid = self.L / 2
        assert abs(bot[0][0] - xmid) < 1e-9
        assert abs(right[0][1] - ymid) < 1e-9

    def test_count_matches_requested(self):
        bot, right, top, left = self.pos()
        assert len(bot) == len(top) == self.NL
        assert len(right) == len(left) == self.NW

    def test_all_candidates_within_panel(self):
        bot, right, top, left = self.pos()
        for pts in (bot, right, top, left):
            for x, y in pts:
                assert 0 <= x <= self.W
                assert 0 <= y <= self.L

    def test_large_base_stays_inside(self):
        bot, *_ = self.pos(b=30)
        for x, y in bot:
            assert 0 <= x <= self.W


# ── Fix 3b: CCW traversal order ──────────────────────────────────────────────


class TestCCWTraversalOrder:
    W, L = 350, 200
    NL, NW = 4, 4
    M, B = 8, 6

    def pos(self, **kw):
        return border_spike_candidates(
            kw.get("w", self.W),
            kw.get("l", self.L),
            kw.get("nl", self.NL),
            kw.get("nw", self.NW),
            kw.get("m", self.M),
            kw.get("b", self.B),
        )

    def test_bot_left_to_right(self):
        bot, *_ = self.pos()
        xs = [p[0] for p in bot]
        assert xs == sorted(xs)

    def test_right_bottom_to_top(self):
        _, right, *_ = self.pos()
        ys = [p[1] for p in right]
        assert ys == sorted(ys)

    def test_top_right_to_left(self):
        _, _, top, _ = self.pos()
        xs = [p[0] for p in top]
        assert xs == sorted(xs, reverse=True)

    def test_left_top_to_bottom(self):
        _, _, _, left = self.pos()
        ys = [p[1] for p in left]
        assert ys == sorted(ys, reverse=True)

    def test_no_duplicate_candidates(self):
        bot, right, top, left = self.pos()
        pts = [(round(x, 6), round(y, 6)) for x, y in bot + right + top + left]
        dupes = {p: c for p, c in Counter(pts).items() if c > 1}
        assert not dupes, f"Duplicate CCW candidates: {dupes}"

    def test_four_fold_symmetry_on_square_panel(self):
        S = 200
        bot, right, top, left = border_spike_candidates(S, S, 4, 4, 10, 6)
        all_pts = set((round(x, 4), round(y, 4)) for x, y in bot + right + top + left)
        for x, y in list(all_pts):
            rotated = (round(S - y, 4), round(x, 4))
            assert rotated in all_pts, (
                f"({x},{y}) missing 90°-rotated counterpart {rotated}"
            )

    def test_same_point_set_as_v5_batched(self):
        """CCW reorders, not repoints — membership must be identical to v5 batched."""
        bot_c, right_c, top_c, left_c = self.pos()
        ccw_set = set(
            (round(x, 4), round(y, 4)) for x, y in bot_c + right_c + top_c + left_c
        )

        # v5 batched (bot/top L→R, left/right B→T — same anchors, different order)
        x0 = self.M + self.B / 2
        x1 = self.W - self.M - self.B / 2
        y0 = self.M + self.B / 2
        y1 = self.L - self.M - self.B / 2
        nl, nw = self.NL, self.NW
        bot_v5 = [
            (x0 + (x1 - x0) / (nl - 1) * i if nl > 1 else (x0 + x1) / 2, self.M)
            for i in range(nl)
        ]
        top_v5 = [
            (
                x0 + (x1 - x0) / (nl - 1) * i if nl > 1 else (x0 + x1) / 2,
                self.L - self.M,
            )
            for i in range(nl)
        ]
        left_v5 = [
            (self.M, y0 + (y1 - y0) / (nw - 1) * i if nw > 1 else (y0 + y1) / 2)
            for i in range(nw)
        ]
        right_v5 = [
            (
                self.W - self.M,
                y0 + (y1 - y0) / (nw - 1) * i if nw > 1 else (y0 + y1) / 2,
            )
            for i in range(nw)
        ]
        v5_set = set(
            (round(x, 4), round(y, 4)) for x, y in bot_v5 + top_v5 + left_v5 + right_v5
        )

        assert ccw_set == v5_set, (
            f"CCW≠v5 batched.\nOnly CCW: {ccw_set - v5_set}\nOnly v5: {v5_set - ccw_set}"
        )


# ── Spike hole-hit threshold (thresh2 precompute) ─────────────────────────────


class TestSpikeHitsHole:
    W = 350
    FR, FY, FN = 20, 55.0, 5  # front radius / row_y / count
    BR, BY, BN = 40, 120.0, 1  # back radius  / row_y / count
    B = 6

    def _front(self, sx, sy, b=None, enabled=True):
        b = b or self.B
        if not enabled:
            return False
        return spike_hits_hole(sx, sy, b, self.FR, self.FN, self.FY, self.W)

    def _back(self, sx, sy, b=None, enabled=True):
        b = b or self.B
        if not enabled:
            return False
        return spike_hits_hole(sx, sy, b, self.BR, self.BN, self.BY, self.W)

    def test_front_centre_hits(self):
        assert self._front(hole_x(0, self.FN, self.FR, self.W), self.FY)

    def test_front_far_misses(self):
        assert not self._front(1, 1)

    def test_front_just_inside_threshold_hits(self):
        cx = hole_x(2, self.FN, self.FR, self.W)
        thresh = self.FR + self.B / 2
        assert self._front(cx + thresh - 1, self.FY)

    def test_front_just_outside_threshold_misses(self):
        cx = hole_x(2, self.FN, self.FR, self.W)
        thresh = self.FR + self.B / 2
        assert not self._front(cx + thresh + 1, self.FY)

    def test_front_disabled_always_misses(self):
        assert not self._front(
            hole_x(0, self.FN, self.FR, self.W), self.FY, enabled=False
        )

    def test_front_last_hole_hits(self):
        assert self._front(hole_x(self.FN - 1, self.FN, self.FR, self.W), self.FY)

    def test_back_centre_hits(self):
        assert self._back(hole_x(0, self.BN, self.BR, self.W), self.BY)

    def test_back_just_inside_threshold_hits(self):
        cx = hole_x(0, self.BN, self.BR, self.W)
        thresh = self.BR + self.B / 2
        assert self._back(cx + thresh - 1, self.BY)

    def test_back_just_outside_threshold_misses(self):
        cx = hole_x(0, self.BN, self.BR, self.W)
        thresh = self.BR + self.B / 2
        assert not self._back(cx + thresh + 1, self.BY)

    def test_back_disabled_always_misses(self):
        assert not self._back(
            hole_x(0, self.BN, self.BR, self.W), self.BY, enabled=False
        )

    def test_precomputed_thresh2_equals_inline(self):
        """thresh2 = (r+b/2)² — both formulations must produce identical floats."""
        for r in [20, 40]:
            for b in [5, 6, 10]:
                assert (r + b / 2) ** 2 == (r + b / 2) * (r + b / 2)


# =============================================================================
# INTEGRATION TESTS — full default-parameter simulation
# =============================================================================


class TestPanelAndRowGeometry:
    def test_front_row_y_inside_panel(self):
        fr = P["front_hole_radius"]
        assert fr < SIM["front_row_y"] < P["panel_length"] - fr

    def test_back_row_y_inside_panel(self):
        br = P["back_hole_radius"]
        assert br < SIM["back_row_y"] < P["panel_length"] - br

    def test_rows_overlap_but_spikes_still_valid(self):
        """
        The default parameters place the rows closer together than the combined
        clearance zones (gap=65mm, combined radii+clearances=76mm), so some ring
        spikes from each row are geometrically rejected by _collect.  That is the
        correct behaviour — the overlap test is a diagnostic, not an invariant.
        What we assert here is that any spike that *was* placed satisfies all
        placement rules despite the tight geometry.
        """
        row_gap = abs(SIM["front_row_y"] - SIM["back_row_y"])
        row_need = (
            P["front_hole_radius"]
            + P["back_hole_radius"]
            + SIM["_eff_fc"]
            + SIM["_eff_bc"]
        )
        # rows are tight — this is expected with default params
        assert row_gap < row_need, (
            "Default params should have overlapping clearance zones"
        )
        # all placed spikes must still be inside the panel and outside both holes
        for p in SIM["all_spikes"]:
            assert spike_in_rect(p[0], p[1], p[2], P["panel_width"], P["panel_length"])
            assert not spike_hits_hole(
                p[0],
                p[1],
                p[2],
                P["front_hole_radius"],
                P["front_hole_count"],
                SIM["front_row_y"],
                P["panel_width"],
            )
            assert not spike_hits_hole(
                p[0],
                p[1],
                p[2],
                P["back_hole_radius"],
                P["back_hole_count"],
                SIM["back_row_y"],
                P["panel_width"],
            )

    def test_all_front_holes_fit_panel_width(self):
        r = P["front_hole_radius"]
        for i in range(P["front_hole_count"]):
            hx = front_hole_x(i, P)
            assert r < hx < P["panel_width"] - r, f"Front hole {i} at x={hx:.1f}"

    def test_all_back_holes_fit_panel_width(self):
        r = P["back_hole_radius"]
        for i in range(P["back_hole_count"]):
            hx = back_hole_x(i, P)
            assert r < hx < P["panel_width"] - r, f"Back hole {i} at x={hx:.1f}"

    def test_adjacent_front_holes_clear(self):
        for i in range(P["front_hole_count"] - 1):
            gap = front_hole_x(i + 1, P) - front_hole_x(i, P)
            need = 2 * (P["front_hole_radius"] + SIM["_eff_fc"])
            assert gap > need, f"Front holes {i}/{i + 1}: gap={gap:.1f} need>{need:.1f}"


class TestSpikeCounts:
    def test_front_spike_count_in_range(self):
        max_f = P["front_spike_count"] * P["front_hole_count"]
        assert 0 < len(SIM["front_acc"]) <= max_f, (
            f"front={len(SIM['front_acc'])} not in (0,{max_f}]"
        )

    def test_back_spike_count_in_range(self):
        max_b = P["back_spike_count"] * P["back_hole_count"]
        assert 0 < len(SIM["back_acc"]) <= max_b, (
            f"back={len(SIM['back_acc'])} not in (0,{max_b}]"
        )

    def test_border_spike_count_in_range(self):
        max_brd = (
            P["border_spikes_on_length_edges"] * 2
            + P["border_spikes_on_width_edges"] * 2
        )
        assert 0 < len(SIM["border_acc"]) <= max_brd, (
            f"border={len(SIM['border_acc'])} not in (0,{max_brd}]"
        )

    def test_expected_front_count(self):
        # 5 holes × 8 spikes each, some rejected by geometry → expect 39 with defaults
        assert len(SIM["front_acc"]) == 39

    def test_expected_back_count(self):
        assert len(SIM["back_acc"]) == 7

    def test_expected_border_count(self):
        assert len(SIM["border_acc"]) == 32

    def test_expected_total_count(self):
        assert len(SIM["all_spikes"]) == 78


class TestSpikePlacement:
    def test_no_spike_inside_any_hole(self):
        bad = [
            p
            for p in SIM["all_spikes"]
            if spike_hits_hole(
                p[0],
                p[1],
                p[2],
                P["front_hole_radius"],
                P["front_hole_count"],
                SIM["front_row_y"],
                P["panel_width"],
            )
            or spike_hits_hole(
                p[0],
                p[1],
                p[2],
                P["back_hole_radius"],
                P["back_hole_count"],
                SIM["back_row_y"],
                P["panel_width"],
            )
        ]
        assert not bad, f"{len(bad)} spikes inside holes"

    def test_all_spikes_within_panel(self):
        bad = [
            p
            for p in SIM["all_spikes"]
            if not spike_in_rect(p[0], p[1], p[2], P["panel_width"], P["panel_length"])
        ]
        assert not bad, f"{len(bad)} spikes outside panel"

    def test_no_spike_spike_collisions(self):
        spikes = SIM["all_spikes"]
        pairs = [
            (i, j)
            for i in range(len(spikes))
            for j in range(i + 1, len(spikes))
            if dist2sq(*spikes[i][:2], *spikes[j][:2])
            < ((spikes[i][2] + spikes[j][2]) / 2) ** 2
        ]
        assert not pairs, f"{len(pairs)} colliding spike pairs"

    def test_front_spikes_type_0(self):
        assert all(p[3] == 0 for p in SIM["front_acc"])

    def test_back_spikes_type_1(self):
        assert all(p[3] == 1 for p in SIM["back_acc"])

    def test_border_spikes_type_2(self):
        assert all(p[3] == 2 for p in SIM["border_acc"])


class TestSlotGrid:
    def test_slots_rendered(self):
        assert SIM["n_slots"] > 0, "No slots rendered"

    def test_expected_slot_count(self):
        # Verified against full simulation with v6 SDF collision logic
        assert SIM["n_slots"] == 297

    def test_no_rendered_slot_overlaps_spike(self):
        assert SIM["violations"] == 0

    def test_cols_rows_positive(self):
        assert SIM["cols"] > 0 and SIM["rows"] > 0

    def test_expected_cols_rows(self):
        assert SIM["cols"] == 24
        assert SIM["rows"] == 23

    def test_slot_x0_y0_reasonable(self):
        assert P["border"] <= SIM["slot_x0"] <= P["panel_width"] / 2
        assert P["border"] <= SIM["slot_y0"] <= P["panel_length"] / 2


class TestMaxSpikeHeight:
    def test_max_spike_height_positive(self):
        max_h = max(
            P["front_spike_height"]
            if P["front_spikes_enabled"] and P["front_row_enabled"]
            else 0,
            P["back_spike_height"]
            if P["back_spikes_enabled"] and P["back_row_enabled"]
            else 0,
            P["border_spike_height"] if P["border_spikes_enabled"] else 0,
        )
        assert max_h > 0

    def test_max_spike_height_value(self):
        max_h = max(
            P["front_spike_height"], P["back_spike_height"], P["border_spike_height"]
        )
        assert max_h == 15  # border_spike_height dominates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

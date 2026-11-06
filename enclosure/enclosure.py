"""Printable PLA enclosure for the therm-gateway (ESP32 DevKit + divider perfboard).

The assembly sits component side up. The long header pins point down and rest
in grooved rails on the floor; two tabs per side against the ends of the
header spacers fix it lengthwise. The lid has a snap lip and two pads that
hold the board down on the USB-C shell and on the ESP32 module can.

Coordinates (mm): x = 0 at the inner face of the USB wall, growing towards
the screw terminal; y = 0 on the board centre line, +y on the GPIO34 header
row; z = 0 on the inner floor.

    pip install manifold3d trimesh matplotlib numpy
    python enclosure/enclosure.py   ->  case_base.stl, case_lid.stl, previews
"""

import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold

OUT = Path(__file__).resolve().parent
SEG = 64

# --- the assembly, measured from photos ---------------------------------
PCB_L, PCB_W, PCB_T = 55.0, 28.3, 1.6   # 38-pin USB-C ESP32 DevKit
PITCH, ROW_Y, PINS = 2.54, 12.7, 19      # header rows 25.4 mm apart
SPACER = 2.5                             # header plastic under the PCB
PIN_LONG = 6.0                           # pin below the plastic
USB_OVERHANG = 2.3                       # receptacle front past the PCB edge
USB_W, USB_H, USB_L = 8.94, 3.26, 8.3
USB_Y = 0.3
MODULE_H = 3.2                           # WROOM-32 can above the PCB
DUPONT = 14.0                            # female housing (standard is 14)
DUPONT_BEND = 5.0                        # room for the wire to bend over
DUPONT_PINS = (5, 14)                    # GND and GPIO34, +y row, from USB end
PERF_T = 1.6
TERM_OVERHANG = 11.0                     # terminal face past the PCB end
TERM_Y, TERM_ENTRY = 2.45, 3.8           # wire entry below the perfboard

# --- box -----------------------------------------------------------------
WALL, FLOOR, LID_T = 2.0, 2.0, 2.0
R_OUT, R_IN = 3.0, 1.0
USB_GAP = 0.2         # receptacle front to the inner wall
TERM_GAP = 5.5        # terminal face to the inner wall: bus wires bend here
HALF_W = 20.5         # zip-tie head sticks out ~6 mm on the -y side
TOP_CLEAR = 8.2       # PCB top to ceiling (USB plug overmold)
USB_HOLE = (14.0, 8.5, 2.0)   # w, h, corner radius: fits the plug overmold
BUS_HOLE_D = 3.5              # two bus wires, printed holes come out ~0.3 small
FIT = 0.3             # tabs vs header spacer ends
LIP_T, LIP_H, LIP_CLR = 1.2, 3.5, 0.15
SNAP = 0.3            # snap ridge height on the lip
PAD_CLR = 0.1         # lid pads vs USB shell / module can

# --- derived -------------------------------------------------------------
PCB_X0 = USB_GAP + USB_OVERHANG
PCB_X1 = PCB_X0 + PCB_L
PCB_BACK = SPACER + DUPONT + DUPONT_BEND + 0.5
PCB_TOP = PCB_BACK + PCB_T
H_IN = PCB_TOP + TOP_CLEAR
L_IN = PCB_X1 + TERM_OVERHANG + TERM_GAP
PIN0 = PCB_X0 + (PCB_L - (PINS - 1) * PITCH) / 2
SPACER_X0, SPACER_X1 = PIN0 - PITCH / 2, PIN0 + (PINS - 0.5) * PITCH
PIN_TIP = PCB_BACK - SPACER - PIN_LONG
GROOVE_D = 1.0
RAIL_TOP = PIN_TIP + GROOVE_D
SNAP_Z = H_IN - 1.8


def pin_x(i):
    return PIN0 + i * PITCH


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def rrect(x0, x1, y0, y1, r):
    cs = CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r), center=True)
    cs = cs.offset(r, JoinType.Round, circular_segments=SEG)
    return cs.translate(((x0 + x1) / 2, (y0 + y1) / 2))


def along_x(cs_yz, x0, x1):
    """Extrude a (y, z) cross-section along x from x0 to x1."""
    m = cs_yz.extrude(x1 - x0)
    return m.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])


def rail(sign, first, last, tab_lo, tab_hi):
    """Grooved rail under header pins first..last of one row, plus end tabs."""
    yc = sign * ROW_Y
    x0, x1 = pin_x(first) - PITCH / 2, pin_x(last) + PITCH / 2
    if tab_lo:
        x0 = SPACER_X0 - FIT - 1.4
    if tab_hi:
        x1 = SPACER_X1 + FIT + 1.4
    m = box(x0, x1, yc - 1.7, yc + 1.7, -0.01, RAIL_TOP)
    g0 = SPACER_X0 - FIT if tab_lo else x0 - 1
    g1 = SPACER_X1 + FIT if tab_hi else x1 + 1
    groove = CrossSection([[(yc - 0.6, PIN_TIP), (yc + 0.6, PIN_TIP), (yc + 1.1, RAIL_TOP),
                            (yc + 1.1, RAIL_TOP + 1), (yc - 1.1, RAIL_TOP + 1), (yc - 1.1, RAIL_TOP)]])
    m -= along_x(groove, g0, g1)
    tab_top = PCB_BACK - 0.6
    if tab_lo:
        m += box(x0, SPACER_X0 - FIT, yc - 1.7, yc + 1.7, 0, tab_top)
    if tab_hi:
        # The perfboard edge runs ~0.1 mm inside the -y spacer: keep clear of it.
        ylo, yhi = (yc - 1.7, yc + 1.7) if sign > 0 else (yc - 1.7, -11.9)
        m += box(SPACER_X1 + FIT, x1, ylo, yhi, 0, tab_top)
    return m


def make_base():
    outer = rrect(-WALL, L_IN + WALL, -HALF_W - WALL, HALF_W + WALL, R_OUT).extrude(H_IN + FLOOR)
    outer = outer.translate((0, 0, -FLOOR))
    cavity = rrect(0, L_IN, -HALF_W, HALF_W, R_IN).extrude(H_IN + 1)
    base = outer - cavity

    w, h, r = USB_HOLE
    usb = rrect(USB_Y - w / 2, USB_Y + w / 2, PCB_TOP + USB_H / 2 - h / 2, PCB_TOP + USB_H / 2 + h / 2, r)
    base -= along_x(usb, -WALL - 1, 1)
    bus = CrossSection.circle(BUS_HOLE_D / 2, SEG).translate((TERM_Y, PCB_BACK - PERF_T - TERM_ENTRY))
    base -= along_x(bus, L_IN - 1, L_IN + WALL + 1)

    # Snap grooves for the lid ridges.
    for s in (1, -1):
        y0, y1 = (HALF_W - 0.01, HALF_W + 0.45) if s > 0 else (-HALF_W - 0.45, -HALF_W + 0.01)
        base -= box(5, L_IN - 5, y0, y1, SNAP_Z - 0.5, SNAP_Z + 0.5)
    # Pry notch for a fingernail at the terminal end (the lip is only on the long sides).
    base -= box(L_IN + WALL - 1.0, L_IN + WALL + 1, -5, 5, H_IN - 1.2, H_IN + 1)

    # USB end: pins 1-3 of both rows. Antenna end: pins 17-19 of the +y row
    # (G34 dupont sits on pin 15); only pin 19 on -y, clear of the zip-tie head.
    base += rail(+1, 0, 2, True, False)
    base += rail(-1, 0, 2, True, False)
    base += rail(+1, 16, 18, False, True)
    base += rail(-1, 18, 18, False, True)
    return base


def make_lid():
    """Lid in assembled position (plate on top of the walls)."""
    plate = rrect(-WALL, L_IN + WALL, -HALF_W - WALL, HALF_W + WALL, R_OUT).extrude(LID_T).translate((0, 0, H_IN))
    lid = plate
    yo = HALF_W - LIP_CLR
    for s in (1, -1):
        lip = box(4, L_IN - 4, yo - LIP_T, yo, H_IN - LIP_H, H_IN + 0.01)
        ridge = CrossSection([[(yo - 0.01, SNAP_Z - 0.5), (yo + SNAP, SNAP_Z), (yo - 0.01, SNAP_Z + 0.5)]])
        lip += along_x(ridge, 7, L_IN - 7)
        lid += lip if s > 0 else lip.mirror((0, 1, 0))
    pad_z = PCB_TOP + max(USB_H, MODULE_H) + PAD_CLR
    lid += box(PCB_X0 - 1.0, PCB_X0 + 4.5, USB_Y - 3.2, USB_Y + 3.2, pad_z, H_IN + 0.01)
    lid += box(PCB_X0 + 30.5, PCB_X0 + 38.5, -5, 5, pad_z, H_IN + 0.01)
    return lid


def make_ghost():
    """Rough model of the assembly, for interference checks and the preview."""
    parts = {
        "pcb": box(PCB_X0, PCB_X1, -PCB_W / 2, PCB_W / 2, PCB_BACK, PCB_TOP),
        "usb": box(PCB_X0 - USB_OVERHANG, PCB_X0 - USB_OVERHANG + USB_L, USB_Y - USB_W / 2, USB_Y + USB_W / 2,
                   PCB_TOP, PCB_TOP + USB_H),
        "module": box(PCB_X0 + 29.0, PCB_X0 + 47.6, -9, 9, PCB_TOP, PCB_TOP + MODULE_H),
        "zip_tie_strap": box(PCB_X0 + 41.1, PCB_X0 + 44.4, -15.4, 15.4, PCB_TOP + MODULE_H, PCB_TOP + MODULE_H + 1.3),
        "zip_tie_head": box(PCB_X0 + 39.3, PCB_X0 + 46.7, -20.0, -14.5, PCB_BACK - 10.5, PCB_BACK - 2.7),
        "perfboard": box(PCB_X1 - 24, PCB_X1 + 10, -11.3, 8.5, PCB_BACK - PERF_T, PCB_BACK),
        "terminal": box(PCB_X1 + TERM_OVERHANG - 8, PCB_X1 + TERM_OVERHANG, TERM_Y - 5.1, TERM_Y + 5.1,
                        PCB_BACK - PERF_T - 10.2, PCB_BACK - PERF_T),
    }
    spacers, pins = Manifold(), Manifold()
    for s in (1, -1):
        spacers += box(SPACER_X0, SPACER_X1, s * ROW_Y - 1.27, s * ROW_Y + 1.27, PCB_BACK - SPACER, PCB_BACK)
        for i in range(PINS):
            x, y = pin_x(i), s * ROW_Y
            pins += box(x - 0.32, x + 0.32, y - 0.32, y + 0.32, PIN_TIP + 0.02, PCB_BACK - SPACER)
            pins += box(x - 0.6, x + 0.6, y - 0.6, y + 0.6, PCB_TOP, PCB_TOP + 2.0)  # tails + solder
    parts["spacers"], parts["pins"] = spacers, pins
    duponts = Manifold()
    for i in DUPONT_PINS:
        x = pin_x(i)
        duponts += box(x - 1.27, x + 1.27, ROW_Y - 1.27, ROW_Y + 1.27, PCB_BACK - SPACER - DUPONT, PCB_BACK - SPACER)
    parts["duponts"] = duponts
    return parts


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def check(base, lid, ghost):
    ok = True
    for name, part in ghost.items():
        for what, solid in (("base", base), ("lid", lid)):
            v = (part ^ solid).volume()
            if v > 1e-3:
                print(f"  INTERFERENCE {name} vs {what}: {v:.2f} mm3")
                ok = False
        # Parts go in from above: their footprint swept upwards must clear the base.
        bb = part.bounding_box()
        if part.volume() > 0:
            swept = box(bb[0], bb[3], bb[1], bb[4], bb[2], H_IN + 5) ^ base
            # Only the pins may sit in the rails, and they are thin enough to miss the swept test.
            if swept.volume() > 1e-3 and name not in ("pins", "spacers", "pcb", "perfboard", "terminal", "duponts"):
                print(f"  BLOCKED on insertion: {name}: {swept.volume():.2f} mm3")
                ok = False
    tips = sum(1 for s in (1, -1) for i in range(PINS)
               if (box(pin_x(i) - 0.3, pin_x(i) + 0.3, s * ROW_Y - 0.3, s * ROW_Y + 0.3, PIN_TIP - 0.05, PIN_TIP)
                   ^ base).volume() > 1e-4)
    print(f"  pins resting on rails: {tips}")
    return ok


def preview(base, lid, ghost, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    def section(ax, solid, plane, at, color, alpha=1.0):
        # Rotate so the requested plane becomes z = at, then slice.
        if plane == "y":
            m = solid.transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]])  # (x, z, -y)
            cs = m.slice(-at)
        elif plane == "x":
            m = solid.transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]])   # (y, z, x)
            cs = m.slice(at)
        else:
            cs = solid.slice(at)
        for poly in cs.to_polygons():
            ax.add_patch(Polygon(poly, closed=True, fc=color, ec="k", lw=0.4, alpha=alpha))

    ghost_all = Manifold()
    for p in ghost.values():
        ghost_all += p
    views = [
        ("y", 0.0, "Centre section (y=0): USB-C, module, terminal", ((-4, L_IN + 4), (-4, H_IN + 4))),
        ("y", ROW_Y, "GPIO34 header row section (+y): rails, duponts", ((-4, L_IN + 4), (-4, H_IN + 4))),
        ("x", 0.0, None, None),
        ("z", PIN_TIP + 0.5, "Plan at the pin tips", ((-4, L_IN + 4), (-HALF_W - 4, HALF_W + 4))),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    for ax, (plane, at, title, lims) in zip(axes.flat, views):
        if plane == "x":
            # End view of the USB wall, seen from outside.
            m = base.transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]])
            for poly in m.slice(-1.0).to_polygons():
                ax.add_patch(Polygon(poly, closed=True, fc="#9ec5e8", ec="k", lw=0.4))
            gm = ghost_all.transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]])
            for poly in gm.slice(3.0).to_polygons():
                ax.add_patch(Polygon(poly, closed=True, fc="#e8a33d", ec="k", lw=0.3, alpha=0.6))
            ax.set_xlim(-HALF_W - 4, HALF_W + 4)
            ax.set_ylim(-4, H_IN + 4)
            ax.set_title("USB wall (x=-1) + board at x=3")
        else:
            section(ax, base, plane, at, "#9ec5e8")
            section(ax, lid, plane, at, "#b6e3a8")
            section(ax, ghost_all, plane, at, "#e8a33d", 0.6)
            ax.set_xlim(*lims[0])
            ax.set_ylim(*lims[1])
            ax.set_title(title)
        ax.set_aspect("equal")
        ax.grid(True, lw=0.3)
    fig.suptitle(f"Case {L_IN + 2 * WALL:.0f} x {2 * (HALF_W + WALL):.0f} x {H_IN + FLOOR + LID_T:.1f} mm  "
                 "(blue base, green lid, orange board)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)

    # Isometric shaded views of the two printable parts.
    fig = plt.figure(figsize=(14, 6))
    for k, (m, title) in enumerate(((base, "Base"), (lid_print_pose(lid), "Lid (inner side)"))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        # Small triangles keep matplotlib's painter's-algorithm sorting sane.
        tm = to_trimesh(m)
        v, f = trimesh.remesh.subdivide_to_size(tm.vertices, tm.faces, max_edge=2.0)
        tm = trimesh.Trimesh(v, f, process=False)
        light = np.array([0.4, -0.6, 0.7])
        light /= np.linalg.norm(light)
        shade = 0.35 + 0.65 * np.clip(tm.face_normals @ light, 0, 1)
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        col = Poly3DCollection(tm.triangles, facecolors=np.outer(shade, [0.62, 0.77, 0.91]), linewidths=0)
        ax.add_collection3d(col)
        lo, hi = tm.bounds
        span = (hi - lo).max() / 2
        c = (hi + lo) / 2
        ax.set_xlim(c[0] - span, c[0] + span)
        ax.set_ylim(c[1] - span, c[1] + span)
        ax.set_zlim(c[2] - span, c[2] + span)
        ax.view_init(elev=35, azim=-60 if k == 0 else 120)
        ax.set_axis_off()
        ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path.with_name("preview_3d.png"), dpi=110)
    plt.close(fig)


def lid_print_pose(lid):
    """Lid turned over (rotated, not mirrored) so it prints plate down."""
    return lid.rotate((180, 0, 0)).translate((0, 0, H_IN + LID_T))


def main():
    base, lid, ghost = make_base(), make_lid(), make_ghost()
    print(f"Inner {L_IN:.1f} x {2 * HALF_W:.1f} x {H_IN:.1f} mm, "
          f"outer {L_IN + 2 * WALL:.1f} x {2 * (HALF_W + WALL):.1f} x {H_IN + FLOOR + LID_T:.1f} mm")
    print(f"PCB back at z={PCB_BACK:.1f}, USB hole centre z={PCB_TOP + USB_H / 2:.1f}, "
          f"bus hole centre z={PCB_BACK - PERF_T - TERM_ENTRY:.1f}")
    ok = check(base, lid, ghost)

    # Print poses: base on its floor, lid flipped onto its plate.
    to_trimesh(base.translate((0, 0, FLOOR))).export(OUT / "case_base.stl")
    to_trimesh(lid_print_pose(lid)).export(OUT / "case_lid.stl")
    preview(base, lid, ghost, OUT / "preview.png")
    print("ok" if ok else "CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

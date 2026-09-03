from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--glyph-json", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bg", choices=("black", "white", "gray", "midtone", "checker"), required=True)
    p.add_argument("--container", choices=("on", "off"), default="on")
    p.add_argument("--glyph", choices=("on", "off"), default="on")
    p.add_argument("--studio", choices=("on", "off"), default="on")
    return p.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def point_at(obj, target=(0.0, 0.0, 0.0)) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_glass(name: str, *, ior: float, roughness: float, absorption_density: float, transmission_luma: float):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")

    glass = nt.nodes.new("ShaderNodeBsdfGlass")
    glass.inputs["Color"].default_value = (transmission_luma, transmission_luma, transmission_luma, 1.0)
    glass.inputs["Roughness"].default_value = roughness
    glass.inputs["IOR"].default_value = ior
    nt.links.new(glass.outputs["BSDF"], out.inputs["Surface"])

    volume = nt.nodes.new("ShaderNodeVolumeAbsorption")
    volume.inputs["Color"].default_value = (0.72, 0.72, 0.72, 1.0)
    volume.inputs["Density"].default_value = absorption_density
    nt.links.new(volume.outputs["Volume"], out.inputs["Volume"])
    return mat


def superellipse_points(a: float = 1.30, n: float = 4.7, count: int = 224):
    pts = []
    e = 2.0 / n
    for i in range(count):
        t = 2.0 * math.pi * i / count
        ct, st = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(ct) ** e, ct)
        y = a * math.copysign(abs(st) ** e, st)
        pts.append((x, y))
    return pts


def make_filled_curve(name: str, points, *, extrude: float, bevel: float, bevel_resolution: int, z: float, material):
    curve = bpy.data.curves.new(name=name, type="CURVE")
    curve.dimensions = "2D"
    curve.fill_mode = "BOTH"
    curve.extrude = extrude
    curve.bevel_depth = bevel
    curve.bevel_resolution = bevel_resolution
    curve.resolution_u = 2
    curve.render_resolution_u = 2

    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, (x, y) in zip(spline.points, points):
        p.co = (float(x), float(y), 0.0, 1.0)
    spline.use_cyclic_u = True

    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location.z = z
    obj.data.materials.append(material)
    return obj


def make_background(kind: str):
    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0.0, 0.0, -1.25))
    plane = bpy.context.object
    plane.name = "Background"

    mat = bpy.data.materials.new("BackgroundMaterial")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emission = nt.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0

    if kind == "checker":
        checker = nt.nodes.new("ShaderNodeTexChecker")
        checker.inputs["Color1"].default_value = (0.015, 0.015, 0.015, 1.0)
        checker.inputs["Color2"].default_value = (0.94, 0.94, 0.94, 1.0)
        checker.inputs["Scale"].default_value = 17.0
        nt.links.new(checker.outputs["Color"], emission.inputs["Color"])
    else:
        colors = {
            "black": (0.0, 0.0, 0.0, 1.0),
            "white": (1.0, 1.0, 1.0, 1.0),
            "gray": (0.5, 0.5, 0.5, 1.0),
            "midtone": (0.40, 0.32, 0.43, 1.0),
        }
        emission.inputs["Color"].default_value = colors[kind]
    nt.links.new(emission.outputs["Emission"], out.inputs["Surface"])
    plane.data.materials.append(mat)

    # Exact camera/transmission target. It must not become part of the studio
    # environment, otherwise black/white inverse solving would be contaminated.
    for attr, value in (
        ("visible_camera", True),
        ("visible_transmission", True),
        ("visible_diffuse", False),
        ("visible_glossy", False),
        ("visible_shadow", False),
        ("visible_volume_scatter", False),
    ):
        if hasattr(plane, attr):
            setattr(plane, attr, value)
    return plane


def add_area(name: str, location, energy: float, size: float):
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    point_at(obj)
    return obj


def configure_render(scene) -> None:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 36
    # Ubuntu's distro Blender is built without OpenImageDenoiser. Denoising is
    # not part of the material model anyway, so keep the ray-traced reference
    # deterministic and render raw Cycles samples instead of failing the job.
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 8
    scene.cycles.transmission_bounces = 8
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.glossy_bounces = 5
    scene.cycles.diffuse_bounces = 2

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    try:
        scene.view_settings.look = "None"
    except Exception:
        pass
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def main() -> None:
    args = parse_args()
    reset_scene()

    scene = bpy.context.scene
    configure_render(scene)

    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.018, 0.018, 0.018, 1.0)
    bg.inputs["Strength"].default_value = 0.34 if args.studio == "on" else 0.065

    container_mat = make_glass(
        "ContainerGlass",
        ior=1.48,
        roughness=0.050,
        absorption_density=0.038,
        transmission_luma=0.992,
    )
    glyph_mat = make_glass(
        "GlyphGlass",
        ior=1.52,
        roughness=0.035,
        absorption_density=0.34,
        transmission_luma=0.945,
    )

    if args.container == "on":
        make_filled_curve(
            "Container",
            superellipse_points(),
            extrude=0.150,
            bevel=0.160,
            bevel_resolution=9,
            z=0.0,
            material=container_mat,
        )

    if args.glyph == "on":
        payload = json.loads(Path(args.glyph_json).read_text(encoding="utf-8"))
        glyph_pts = [(p[0] * 1.055, p[1] * 1.055) for p in payload["points"]]
        make_filled_curve(
            "Glyph",
            glyph_pts,
            extrude=0.072,
            bevel=0.052,
            bevel_resolution=7,
            z=0.278 if args.container == "on" else 0.0,
            material=glyph_mat,
        )

    make_background(args.bg)

    if args.studio == "on":
        # Large asymmetric studio sources. These are actual scene lights, not a
        # painted streak in the RGBA asset.
        add_area("Key", (-3.5, -4.2, 5.6), 920.0, 4.4)
        add_area("Fill", (3.8, -1.8, 4.8), 430.0, 3.0)
        add_area("Top", (0.2, 4.4, 4.0), 250.0, 2.7)

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0.0, 0.0, 5.6)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 4.05
    point_at(cam)
    scene.camera = cam

    scene.render.filepath = str(Path(args.out))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()

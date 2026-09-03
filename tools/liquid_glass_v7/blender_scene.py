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
    return p.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.curves, bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass


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
    volume.inputs["Color"].default_value = (0.74, 0.74, 0.74, 1.0)
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
    curve.resolution_u = 1
    curve.render_resolution_u = 1
    curve.extrude = extrude
    curve.bevel_depth = bevel
    curve.bevel_resolution = bevel_resolution
    curve.resolution_u = 2

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

    # The backdrop is an exact camera/transmission target, not part of the
    # environment lighting. Reflections remain identical for black/white/gray,
    # which makes inverse compositing mathematically meaningful.
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


def main() -> None:
    args = parse_args()
    reset_scene()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 96
        scene.eevee.use_gtao = True
        scene.eevee.gtao_distance = 3.0
        scene.eevee.gtao_factor = 0.65
        scene.eevee.use_soft_shadows = True
        if hasattr(scene.eevee, "use_ssr"):
            scene.eevee.use_ssr = True
        if hasattr(scene.eevee, "use_ssr_refraction"):
            scene.eevee.use_ssr_refraction = True

    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.018, 0.018, 0.018, 1.0)
    bg.inputs["Strength"].default_value = 0.34

    container_mat = make_glass(
        "ContainerGlass",
        ior=1.48,
        roughness=0.055,
        absorption_density=0.045,
        transmission_luma=0.985,
    )
    glyph_mat = make_glass(
        "GlyphGlass",
        ior=1.52,
        roughness=0.040,
        absorption_density=0.36,
        transmission_luma=0.93,
    )

    container = make_filled_curve(
        "Container",
        superellipse_points(),
        extrude=0.145,
        bevel=0.155,
        bevel_resolution=8,
        z=0.0,
        material=container_mat,
    )
    if hasattr(container.data.materials[0], "use_screen_refraction"):
        container.data.materials[0].use_screen_refraction = True

    payload = json.loads(Path(args.glyph_json).read_text(encoding="utf-8"))
    glyph_pts = [(p[0] * 1.055, p[1] * 1.055) for p in payload["points"]]
    glyph = make_filled_curve(
        "Glyph",
        glyph_pts,
        extrude=0.070,
        bevel=0.050,
        bevel_resolution=6,
        z=0.275,
        material=glyph_mat,
    )
    if hasattr(glyph.data.materials[0], "use_screen_refraction"):
        glyph.data.materials[0].use_screen_refraction = True

    make_background(args.bg)

    # Large asymmetric studio sources. They define material curvature without a
    # painted highlight streak and stay constant across all inverse-bake passes.
    add_area("Key", (-3.5, -4.2, 5.6), 920.0, 4.4)
    add_area("Fill", (3.8, -1.8, 4.8), 430.0, 3.0)
    add_area("Top", (0.2, 4.4, 4.0), 250.0, 2.7)

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0.0, 0.0, 5.6)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 4.05
    cam.data.lens = 50
    point_at(cam)
    scene.camera = cam

    scene.render.filepath = str(Path(args.out))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()

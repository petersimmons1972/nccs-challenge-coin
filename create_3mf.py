#!/usr/bin/env python3
"""
Package NCCS Challenge Coin STLs into a Bambu Studio-native 3MF.

Matches the exact format Bambu Studio 02.05.00.66 produces:
  - All 4 color meshes in a single sub-model: 3D/Objects/object_1.model
  - Root 3dmodel.model contains only the assembly wrapper with p:path components
  - model_settings.config with <part> extruder assignments + plate/assemble sections
  - project_settings.config with correct NCCS filament colors

Colors / AMS Slots:
  1: Navy Blue   (#1B3B60)
  2: Dark Gray   (#999DA2)
  3: Carolina    (#8BD1EE)
  4: White       (#FFFFFF)
"""

import json
import struct
import zipfile
import os
import uuid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(SCRIPT_DIR, "build")

SIDES = [
    {
        "name": "Obverse",
        "output": "NCCS_Coin_Obverse.3mf",
        "colors": [
            {"name": "Navy Blue",     "hex": "#1B3B60", "stl": "obverse_navy",     "extruder": 1},
            {"name": "Dark Gray",     "hex": "#999DA2", "stl": "obverse_gray",     "extruder": 2},
            {"name": "Carolina Blue", "hex": "#8BD1EE", "stl": "obverse_carolina", "extruder": 3},
            {"name": "White",         "hex": "#FFFFFF", "stl": "obverse_white",    "extruder": 4},
        ],
    },
    {
        "name": "Reverse",
        "output": "NCCS_Coin_Reverse.3mf",
        "colors": [
            {"name": "Navy Blue",     "hex": "#1B3B60", "stl": "reverse_navy",     "extruder": 1},
            {"name": "Dark Gray",     "hex": "#999DA2", "stl": "reverse_gray",     "extruder": 2},
            {"name": "Carolina Blue", "hex": "#8BD1EE", "stl": "reverse_carolina", "extruder": 3},
            {"name": "White",         "hex": "#FFFFFF", "stl": "reverse_white",    "extruder": 4},
        ],
    },
    {
        "name": "Double-Sided Coin",
        "output": "NCCS_Challenge_Coin.3mf",
        "colors": [
            {"name": "Navy Blue",     "hex": "#1B3B60", "stl": "coin_navy",     "extruder": 1},
            {"name": "Dark Gray",     "hex": "#999DA2", "stl": "coin_gray",     "extruder": 2},
            {"name": "Carolina Blue", "hex": "#8BD1EE", "stl": "coin_carolina", "extruder": 3},
            {"name": "White",         "hex": "#FFFFFF", "stl": "coin_white",    "extruder": 4},
        ],
    },
]


def parse_stl(filepath):
    """Parse binary or ASCII STL, return list of (normal, v1, v2, v3) tuples."""
    with open(filepath, "rb") as f:
        header = f.read(80)
        num_tri = struct.unpack("<I", f.read(4))[0]
        f.seek(0, 2)
        expected = 84 + num_tri * 50
        if f.tell() == expected and num_tri > 0:
            f.seek(84)
            tris = []
            for _ in range(num_tri):
                data = struct.unpack("<12fH", f.read(50))
                tris.append((data[0:3], data[3:6], data[6:9], data[9:12]))
            return tris
    # ASCII STL fallback
    tris = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("facet normal"):
                p = line.split()
                normal = (float(p[2]), float(p[3]), float(p[4]))
                verts = []
            elif line.startswith("vertex"):
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("endfacet"):
                if len(verts) == 3:
                    tris.append((normal, verts[0], verts[1], verts[2]))
    return tris


def make_mesh_xml(obj_id, obj_uuid, triangles):
    """Create <object> XML fragment for the sub-model file."""
    vert_map = {}
    vert_list = []
    tri_indices = []

    for normal, v1, v2, v3 in triangles:
        indices = []
        for v in [v1, v2, v3]:
            key = (round(v[0], 6), round(v[1], 6), round(v[2], 6))
            if key not in vert_map:
                vert_map[key] = len(vert_list)
                vert_list.append(key)
            indices.append(vert_map[key])
        tri_indices.append(tuple(indices))

    verts_xml = "\n".join(
        f'     <vertex x="{v[0]}" y="{v[1]}" z="{v[2]}"/>'
        for v in vert_list
    )
    tris_xml = "\n".join(
        f'     <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>'
        for t in tri_indices
    )

    return f"""  <object id="{obj_id}" p:UUID="{obj_uuid}" type="model">
   <mesh>
    <vertices>
{verts_xml}
    </vertices>
    <triangles>
{tris_xml}
    </triangles>
   </mesh>
  </object>""", len(tri_indices)


def create_bambu_3mf(output_path, colors):
    """Create a Bambu Studio-native 3MF matching the exact export format."""

    # Parse each color STL
    parts = []
    for color_def in colors:
        stl_path = os.path.join(BUILD_DIR, f"{color_def['stl']}.stl")
        if not os.path.exists(stl_path):
            print(f"  WARNING: {stl_path} not found, skipping")
            continue
        triangles = parse_stl(stl_path)
        print(f"  {color_def['name']}: {len(triangles)} triangles")
        parts.append((color_def, triangles))

    if not parts:
        print("  ERROR: No STL files found")
        return False

    # Build mesh objects for sub-model (id=1..N)
    mesh_objects = []
    for i, (color_def, triangles) in enumerate(parts):
        obj_id = i + 1
        obj_uuid = str(uuid.uuid4())
        mesh_xml, face_count = make_mesh_xml(obj_id, obj_uuid, triangles)
        mesh_objects.append({
            "id": obj_id,
            "uuid": obj_uuid,
            "color": color_def,
            "face_count": face_count,
            "mesh_xml": mesh_xml,
        })

    # Sub-model file: all 4 meshes in one file (Bambu native format)
    sub_model_objects_xml = "\n".join(mo["mesh_xml"] for mo in mesh_objects)
    sub_model = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
{sub_model_objects_xml}
 </resources>
</model>"""

    # Assembly object in root model — references sub-model via p:path
    assembly_id = len(mesh_objects) + 1
    assembly_uuid = str(uuid.uuid4())
    build_uuid = str(uuid.uuid4())
    item_uuid = str(uuid.uuid4())

    components_xml = "\n".join(
        f'    <component p:path="/3D/Objects/object_1.model" objectid="{mo["id"]}" '
        f'p:UUID="{mo["uuid"]}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
        for mo in mesh_objects
    )

    root_model = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">BambuStudio-02.05.00.66</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">NCCS Challenge Coin</metadata>
 <resources>
  <object id="{assembly_id}" p:UUID="{assembly_uuid}" type="model">
   <components>
{components_xml}
   </components>
  </object>
 </resources>
 <build p:UUID="{build_uuid}">
  <item objectid="{assembly_id}" p:UUID="{item_uuid}" transform="1 0 0 0 1 0 0 0 1 128 128 0" printable="1"/>
 </build>
</model>"""

    # 3D/_rels/3dmodel.model.rels — links root model to sub-model
    model_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""

    # model_settings.config — <part> per color mesh with extruder assignment
    total_faces = sum(mo["face_count"] for mo in mesh_objects)
    parts_xml = "\n".join(
        f"""    <part id="{mo['id']}" subtype="normal_part">
      <metadata key="name" value="{mo['color']['name']}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="extruder" value="{mo['color']['extruder']}"/>
      <metadata key="source_object_id" value="{mo['id'] - 1}"/>
      <metadata key="source_volume_id" value="0"/>
      <mesh_stat face_count="{mo['face_count']}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>"""
        for mo in mesh_objects
    )

    model_settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="{assembly_id}">
    <metadata key="name" value="NCCS Challenge Coin"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{total_faces}"/>
{parts_xml}
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
    <model_instance>
      <metadata key="object_id" value="{assembly_id}"/>
      <metadata key="instance_id" value="0"/>
    </model_instance>
  </plate>
  <assemble>
   <assemble_item object_id="{assembly_id}" instance_id="0" transform="1 0 0 0 1 0 0 0 1 128 128 0" offset="0 0 0"/>
  </assemble>
</config>"""

    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="config" ContentType="text/xml"/>
 <Default Extension="png" ContentType="image/png"/>
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""

    slice_info = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <header>
    <header_item key="X-BBL-Client-Type" value="slicer"/>
    <header_item key="X-BBL-Client-Version" value="02.05.00.66"/>
  </header>
</config>"""

    # project_settings.config — configures AMS filament colors and profiles
    filament_hex = [mo["color"]["hex"] for mo in mesh_objects]
    n = len(filament_hex)
    project_settings = json.dumps({
        "filament_colour": filament_hex,
        "filament_type": ["PLA"] * n,
        "filament_settings_id": ["Generic PLA @BBL X1C"] * n,
        "filament_vendor": ["Generic"] * n,
        "nozzle_temperature": ["220"] * n,
        "nozzle_temperature_initial_layer": ["220"] * n,
        "single_extruder_multi_material": "1",
        "enable_prime_tower": "1",
    }, indent=2)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', root_rels)
        zf.writestr('3D/3dmodel.model', root_model)
        zf.writestr('3D/_rels/3dmodel.model.rels', model_rels)
        zf.writestr('3D/Objects/object_1.model', sub_model)
        zf.writestr('Metadata/model_settings.config', model_settings)
        zf.writestr('Metadata/project_settings.config', project_settings)
        zf.writestr('Metadata/slice_info.config', slice_info)

    file_size = os.path.getsize(output_path)
    print(f"\n  Created: {output_path} ({file_size:,} bytes)")
    return True


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)

    print("=== Packaging NCCS Challenge Coin (4-Part Multi-Color) ===")
    print()

    for side in SIDES:
        print(f"--- {side['name']} ---")
        output = os.path.join(BUILD_DIR, side["output"])
        success = create_bambu_3mf(output, side["colors"])
        if success:
            print(f"  Filament assignments:")
            for c in side["colors"]:
                print(f"    Filament {c['extruder']}: {c['name']} ({c['hex']})")
        print()


if __name__ == "__main__":
    main()

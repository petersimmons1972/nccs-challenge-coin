#!/usr/bin/env python3
"""
TDD tests for the 3MF builder.

Verifies the Bambu Studio-native 3MF structure:
  - Root 3dmodel.model contains only the assembly wrapper (no inline meshes)
  - All 4 color meshes live in 3D/Objects/object_1.model (single sub-model)
  - Assembly components reference the sub-model via p:path
  - model_settings.config has 4 <part> elements with correct extruder slots
  - project_settings.config has correct NCCS filament colors
"""
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from create_3mf import parse_stl, make_mesh_xml, create_bambu_3mf

BUILD_DIR = os.path.join(os.path.dirname(__file__), "build")

NS = {
    "m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
    "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06",
}

TEST_3MF = os.path.join(BUILD_DIR, "test_output.3mf")
TEST_COLORS = [
    {"name": "Navy Blue",     "hex": "#1B3B60", "stl": "coin_navy",     "extruder": 1},
    {"name": "Dark Gray",     "hex": "#999DA2", "stl": "coin_gray",     "extruder": 2},
    {"name": "Carolina Blue", "hex": "#8BD1EE", "stl": "coin_carolina", "extruder": 3},
    {"name": "White",         "hex": "#FFFFFF", "stl": "coin_white",    "extruder": 4},
]


def setUpModule():
    create_bambu_3mf(TEST_3MF, TEST_COLORS)


def tearDownModule():
    if os.path.exists(TEST_3MF):
        os.remove(TEST_3MF)


class TestArchiveStructure(unittest.TestCase):
    """Required files present; sub-model file exists."""

    def setUp(self):
        self.zf = zipfile.ZipFile(TEST_3MF)

    def tearDown(self):
        self.zf.close()

    def test_required_files_present(self):
        names = self.zf.namelist()
        self.assertIn("[Content_Types].xml", names)
        self.assertIn("_rels/.rels", names)
        self.assertIn("3D/3dmodel.model", names)
        self.assertIn("3D/Objects/object_1.model", names)
        self.assertIn("3D/_rels/3dmodel.model.rels", names)
        self.assertIn("Metadata/model_settings.config", names)
        self.assertIn("Metadata/project_settings.config", names)

    def test_sub_model_file_exists(self):
        """All 4 meshes must be in the sub-model file (Bambu native format)."""
        names = self.zf.namelist()
        self.assertIn("3D/Objects/object_1.model", names,
            "Sub-model file missing — Bambu Studio expects meshes in 3D/Objects/")


class TestRootModelStructure(unittest.TestCase):
    """Root model contains only the assembly wrapper, no inline meshes."""

    def setUp(self):
        with zipfile.ZipFile(TEST_3MF) as zf:
            self.root = ET.fromstring(zf.read("3D/3dmodel.model"))

    def _objects(self):
        return self.root.findall(".//m:object", NS)

    def test_no_inline_mesh_objects_in_root(self):
        """Root model must not contain any mesh objects — they live in the sub-model."""
        mesh_objects = [
            o for o in self._objects()
            if o.find("m:mesh", NS) is not None
        ]
        self.assertEqual(len(mesh_objects), 0,
            f"Root model has {len(mesh_objects)} inline mesh objects — should be 0")

    def test_assembly_object_with_four_components(self):
        """One assembly object with 4 p:path component references."""
        assembly_objects = [
            o for o in self._objects()
            if o.find("m:components", NS) is not None
        ]
        self.assertEqual(len(assembly_objects), 1,
            f"Expected 1 assembly object, got {len(assembly_objects)}")
        components = assembly_objects[0].findall("m:components/m:component", NS)
        self.assertEqual(len(components), 4,
            f"Expected 4 components, got {len(components)}")

    def test_components_reference_sub_model_via_path(self):
        """Components must use p:path to reference the sub-model file."""
        assembly = [
            o for o in self._objects()
            if o.find("m:components", NS) is not None
        ][0]
        for comp in assembly.findall("m:components/m:component", NS):
            path = comp.get("{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}path")
            self.assertEqual(path, "/3D/Objects/object_1.model",
                f"Component p:path should be /3D/Objects/object_1.model, got {path}")

    def test_single_build_item_references_assembly(self):
        build_items = self.root.findall(".//m:build/m:item", NS)
        self.assertEqual(len(build_items), 1,
            f"Expected 1 build item (the assembly), got {len(build_items)}")


class TestSubModelStructure(unittest.TestCase):
    """Sub-model must contain 4 mesh objects."""

    def setUp(self):
        with zipfile.ZipFile(TEST_3MF) as zf:
            self.sub = ET.fromstring(zf.read("3D/Objects/object_1.model"))

    def _objects(self):
        return self.sub.findall(".//m:object", NS)

    def test_four_mesh_objects_in_sub_model(self):
        mesh_objects = [
            o for o in self._objects()
            if o.find("m:mesh", NS) is not None
        ]
        self.assertEqual(len(mesh_objects), 4,
            f"Expected 4 mesh objects in sub-model, got {len(mesh_objects)}")

    def test_each_mesh_has_vertices_and_triangles(self):
        for obj in self._objects():
            mesh = obj.find("m:mesh", NS)
            if mesh is None:
                continue
            self.assertIsNotNone(mesh.find("m:vertices", NS))
            self.assertIsNotNone(mesh.find("m:triangles", NS))


class TestExtruderAssignments(unittest.TestCase):
    """model_settings.config must have 4 parts with correct extruder slots."""

    def setUp(self):
        with zipfile.ZipFile(TEST_3MF) as zf:
            self.config = ET.fromstring(zf.read("Metadata/model_settings.config"))

    def _parts(self):
        return self.config.findall(".//part")

    def test_four_parts_defined(self):
        parts = self._parts()
        self.assertEqual(len(parts), 4,
            f"Expected 4 parts in model_settings.config, got {len(parts)}")

    def test_extruder_slots_are_1_through_4(self):
        extruders = sorted(
            int(p.find("metadata[@key='extruder']").get("value"))
            for p in self._parts()
        )
        self.assertEqual(extruders, [1, 2, 3, 4],
            f"Expected extruder slots [1,2,3,4], got {extruders}")

    def test_each_color_has_correct_extruder(self):
        assignments = {
            p.find("metadata[@key='name']").get("value"):
            int(p.find("metadata[@key='extruder']").get("value"))
            for p in self._parts()
        }
        self.assertEqual(assignments["Navy Blue"], 1)
        self.assertEqual(assignments["Dark Gray"], 2)
        self.assertEqual(assignments["Carolina Blue"], 3)
        self.assertEqual(assignments["White"], 4)


class TestFilamentColors(unittest.TestCase):
    """project_settings.config must have correct NCCS colors."""

    def setUp(self):
        with zipfile.ZipFile(TEST_3MF) as zf:
            self.config = json.loads(zf.read("Metadata/project_settings.config"))

    def test_four_filament_colors_defined(self):
        self.assertEqual(len(self.config["filament_colour"]), 4)

    def test_navy_blue_is_slot_1(self):
        self.assertEqual(self.config["filament_colour"][0], "#1B3B60")

    def test_dark_gray_is_slot_2(self):
        self.assertEqual(self.config["filament_colour"][1], "#999DA2")

    def test_carolina_blue_is_slot_3(self):
        self.assertEqual(self.config["filament_colour"][2], "#8BD1EE")

    def test_white_is_slot_4(self):
        self.assertEqual(self.config["filament_colour"][3], "#FFFFFF")


class TestMeshGeneration(unittest.TestCase):
    """make_mesh_xml must produce valid, non-empty mesh XML."""

    def test_mesh_xml_has_vertices_and_triangles(self):
        tris = parse_stl(os.path.join(BUILD_DIR, "coin_navy.stl"))
        xml_str, face_count = make_mesh_xml(1, "test-uuid", tris)
        wrapped = (
            '<root xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'
            ' xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06">'
            + xml_str + '</root>'
        )
        root = ET.fromstring(wrapped)
        obj = root.find("m:object", NS)
        self.assertIsNotNone(obj.find("m:mesh/m:vertices", NS))
        self.assertIsNotNone(obj.find("m:mesh/m:triangles", NS))
        self.assertGreater(face_count, 0)

    def test_face_count_matches_triangle_count(self):
        tris = parse_stl(os.path.join(BUILD_DIR, "coin_navy.stl"))
        _, face_count = make_mesh_xml(1, "test-uuid", tris)
        self.assertEqual(face_count, len(tris))


if __name__ == "__main__":
    unittest.main(verbosity=2)

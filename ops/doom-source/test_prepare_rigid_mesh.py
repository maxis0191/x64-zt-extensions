import unittest
import xml.etree.ElementTree as ET
from prepare_rigid_mesh import convert, NS


def fixture():
    return b'''<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<asset><unit meter="0.01"/><up_axis>Y_UP</up_axis></asset>
<library_images><image id="image"><init_from>helmet.png</init_from></image></library_images>
<library_effects><effect id="effect"><profile_COMMON>
<newparam sid="surface"><surface type="2D"><init_from>image</init_from></surface></newparam>
<newparam sid="sampler"><sampler2D><source>surface</source></sampler2D></newparam>
<technique><blinn><diffuse><texture texture="sampler" texcoord="UV0"/></diffuse></blinn></technique>
</profile_COMMON></effect></library_effects>
<library_materials><material id="material" name="helmet"><instance_effect url="#effect"/></material></library_materials>
<library_geometries><geometry id="geometry"><mesh>
<source id="positions"><float_array id="pa" count="9">0 0 0 100 0 0 0 100 0</float_array><technique_common><accessor source="#pa" count="3" stride="3"/></technique_common></source>
<source id="normals"><float_array id="na" count="3">0 0 1</float_array><technique_common><accessor source="#na" count="1" stride="3"/></technique_common></source>
<source id="uv"><float_array id="ua" count="6">0 0 1 0 0 1</float_array><technique_common><accessor source="#ua" count="3" stride="2"/></technique_common></source>
<vertices id="vertices"><input semantic="POSITION" source="#positions"/></vertices>
<triangles count="1" material="symbol"><input semantic="VERTEX" source="#vertices" offset="0"/><input semantic="NORMAL" source="#normals" offset="1"/><input semantic="TEXCOORD" source="#uv" offset="2" set="0"/><p>0 0 0 1 0 1 2 0 2</p></triangles>
</mesh></geometry></library_geometries>
<library_controllers><controller id="controller"><skin source="#geometry"><bind_shape_matrix>1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1</bind_shape_matrix></skin></controller></library_controllers>
<library_visual_scenes><visual_scene id="scene"><node id="node" name="realHelmetNode"><translate>1 2 3</translate><rotate>1 0 0 0</rotate><scale>1 1 1</scale><instance_controller url="#controller"><bind_material><technique_common><instance_material symbol="symbol" target="#material"><bind_vertex_input semantic="UV0" input_semantic="TEXCOORD" input_set="0"/></instance_material></technique_common></bind_material></instance_controller></node></visual_scene></library_visual_scenes>
</COLLADA>'''


def change(xpath, text=None, attribute=None):
    root=ET.fromstring(fixture());node=root.find(xpath,NS)
    if text is not None:node.text=text
    if attribute is not None:node.set(*attribute)
    return ET.tostring(root)


class RigidSourceTests(unittest.TestCase):
    def test_material_selection_metres_pivot_axes(self):
        result=convert(fixture(),"helmet")
        self.assertFalse(result["ready"])
        self.assertEqual(result["selection"]["node_name"],"realHelmetNode")
        self.assertEqual(result["selection"]["texture_basename"],"helmet.png")
        self.assertEqual(result["triangle_indices"],[0,1,2])
        self.assertEqual(result["vertices"][0]["position_m"],[-0.5,0.0,-0.5])
        self.assertEqual(result["vertices"][0]["normal"],[0.0,-1.0,0.0])
        self.assertEqual(result["transform"]["pivot_world_m"],[0.51,-0.03,0.52])

    def test_indices_and_nonfinite(self):
        for data in (change(".//c:triangles/c:p","0 0 0 1 0 1 3 0 2"),change(".//c:source[@id='positions']/c:float_array","0 0 0 nan 0 0 0 100 0")):
            with self.assertRaises(ValueError):convert(data,"helmet")

    def test_degenerate_and_winding(self):
        for data in (change(".//c:source[@id='positions']/c:float_array","0 0 0 100 0 0 200 0 0"),change(".//c:triangles/c:p","0 0 0 2 0 2 1 0 1")):
            with self.assertRaises(ValueError):convert(data,"helmet")

    def test_uv_preserved_no_clamp(self):
        data=change(".//c:source[@id='uv']/c:float_array","0 0 2 0 0 1")
        result=convert(data,"helmet")
        self.assertEqual(result["vertices"][1]["uv"],[2.0,0.0])
        self.assertEqual(result["metrics"]["uv_outside_0_1"],1)
        with self.assertRaises(ValueError):convert(change(".//c:source[@id='uv']/c:float_array","0 0 17 0 0 1"),"helmet")

    def test_transform_and_selection_refused(self):
        for data in (change(".//c:node/c:rotate","1 0 0 90"),change(".//c:node/c:scale","-1 1 1"),change(".//c:instance_material",attribute=("target","#missing"))):
            with self.assertRaises(ValueError):convert(data,"helmet")
        with self.assertRaises(ValueError):convert(fixture(),"unknownHelmet")


if __name__=="__main__":unittest.main()

import copy
import unittest
import tempfile
import json
from pathlib import Path
from prepare_writer import geometry_header
from verify_prepared import verify


def fixture():
    return {"schema":"iw7.doom-rigid-source/1","ready":False,"mode":"rigid_source_bind_geometry_not_evaluated_pose","transform":{"output_up":"Z_UP","determinant_sign":1,"uv_policy":"preserved_no_V_flip"},"vertices":[{"position_m":p,"normal":[0,-1,0],"uv":u} for p,u in (([-.5,0,-.5],[0,0]),([.5,0,-.5],[1,0]),([-.5,0,.5],[0,1]))],"triangle_indices":[0,1,2]}


class WriterSourceTests(unittest.TestCase):
    def build(self,value=None,**args):
        return geometry_header(value or fixture(),args.get("name","paris_doom_helmet_rigid_a"),args.get("material","mopw/character_park_clown_zombie_shoes"),args.get("height",16))

    def test_scale_counts_bounds(self):
        header,metrics=self.build()
        self.assertEqual(metrics["engine_units_per_metre"],16)
        self.assertEqual(metrics["bounds_half_engine"],[8,0,8])
        self.assertEqual(metrics["vertices"],3)
        self.assertIn("probe_model_name=\"paris_doom_helmet_rigid_a\"",header)
        self.assertIn("probe_vertex_count=3",header)
        self.assertIn("-8.0f",header)

    def test_refuse_scope_and_scale(self):
        for args in ({"name":"paris_model_probe"},{"material":"missing"},{"height":.3},{"height":float("nan")}):
            with self.assertRaises(ValueError):self.build(**args)

    def test_bad_index_and_degenerate_uv(self):
        data=fixture();data["triangle_indices"]=[0,1,3]
        with self.assertRaises(ValueError):self.build(data)
        data=fixture();data["vertices"][2]["uv"]=[1,0]
        with self.assertRaises(ValueError):self.build(data)

    def test_material_stage1_only_and_nonfinite(self):
        data=fixture();data["vertices"][0]["normal"]=[1e300,0,0]
        with self.assertRaises(ValueError):self.build(data)

    def test_exact_prepared_header_and_metrics(self):
        data=fixture();header,metrics=self.build(data)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            manifest={"candidate_name":"paris_doom_helmet_rigid_a","material_reference":"mopw/character_park_clown_zombie_shoes","metrics":metrics}
            (root/"writer-source.json").write_text(json.dumps(manifest),encoding="utf-8")
            (root/"geometry.source.json").write_text(json.dumps(data),encoding="utf-8")
            (root/"rigid_geometry.hpp").write_bytes(header.encode())
            self.assertEqual(verify(root),metrics)
            (root/"rigid_geometry.hpp").write_bytes((header+"\n").encode())
            with self.assertRaises(ValueError):verify(root)
            (root/"rigid_geometry.hpp").write_bytes(header.encode())
            manifest["metrics"]["vertices"]=4
            (root/"writer-source.json").write_text(json.dumps(manifest),encoding="utf-8")
            with self.assertRaises(ValueError):verify(root)
        data=copy.deepcopy(fixture());data["vertices"][0]["position_m"][0]=float("inf")
        with self.assertRaises(ValueError):self.build(data)


if __name__=="__main__":unittest.main()

import copy
import unittest
import builder as b
from test_builder import fixtures
from builder_modules.m3_tasks import module as tasks
from builder_modules.m5_quality import module as quality


def audit():
    return dict(geometry_inputs='Two positions in angstrom',
                without_geometry='Distance cannot be calculated; units remain known.',
                dependent_score_items='Euclidean separation is the numerical score.',
                scale_basis='Span of the two participating sites, not file size.',
                claim_limits='Only distance, no stability or bonding conclusion.',
                template_family='specified_pair_distance',
                geometry_dependency='necessary', scale_consistent=True, claims_supported=True)


class AuditContractTests(unittest.TestCase):
    def setUp(self):
        self.bundle, self.stages = fixtures()
        # Validator-level test data only, never exported as a real scientific run.
        self.bundle['synthetic'] = False

    def test_real_task_cannot_omit_dependency_record(self):
        with self.assertRaisesRegex(ValueError, 'requires geometry_audit'):
            tasks.validate(b, self.stages['tasks'], self.bundle, self.stages, {})

    def test_real_review_cannot_omit_dependency_record(self):
        with self.assertRaisesRegex(ValueError, 'requires geometry_audit'):
            quality.validate(b, self.stages['review'], self.bundle, self.stages, {})

    def test_decorative_geometry_cannot_be_eligible(self):
        t=self.stages['tasks']['tasks'][0]; t['geometry_audit']=audit()
        t['geometry_audit'].update(geometry_dependency='none', geometry_inputs='Unneeded XYZ',
            without_geometry='Supplied HOMO and LUMO still give the full scored gap.')
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            tasks.validate(b, self.stages['tasks'], self.bundle, self.stages, {})
        t['eligible']=False; t['unmet_requirements']=['Molecular geometry is not needed.']
        tasks.validate(b, self.stages['tasks'], self.bundle, self.stages, {})

    def test_scalar_geometry_is_valid(self):
        t=self.stages['tasks']['tasks'][0];t['validation_route']='evidence_review'
        t['geometry_audit']=audit();t['geometry_audit'].update(
            geometry_inputs='Cell parameter a and Miller indices',
            dependent_score_items='Plane spacing calculated from geometric a and indices.')
        tasks.validate(b,self.stages['tasks'],self.bundle,self.stages,{})
        b.validate(self.stages['tasks'],b.SCHEMAS['tasks'])

    def test_review_rejects_false_pass_for_each_failure(self):
        for key,value,flags in [('geometry_dependency','none',['geometry_required']),
                                ('geometry_dependency','uncertain',['geometry_required']),
                                ('scale_consistent',False,['single_scale_focus']),
                                ('claims_supported',False,['evidence_support','rubric_scorable'])]:
            with self.subTest(key=key,value=value):
                d=copy.deepcopy(self.stages['review']);r=d['reviews'][0]
                r['geometry_audit']=audit();r['geometry_audit'][key]=value
                with self.assertRaisesRegex(ValueError,'contradict'):
                    quality.validate(b,d,self.bundle,self.stages,{})
                for f in flags:r['checks'][f]=False
                with self.assertRaisesRegex(ValueError,'record failure'):
                    quality.validate(b,d,self.bundle,self.stages,{})
                r['issues']=['Specific unsupported scoring claim or scope; requires revision.']
                quality.validate(b,d,self.bundle,self.stages,{})

    def test_empty_explanation_not_a_pass(self):
        r=self.stages['review']['reviews'][0];r['geometry_audit']=audit()
        r['geometry_audit']['without_geometry']='  '
        with self.assertRaisesRegex(ValueError,'concrete reasons'):
            quality.validate(b,self.stages['review'],self.bundle,self.stages,{})

    def test_optional_legacy_field_does_not_allow_unknown_keys(self):
        b.validate(self.stages['review'],b.SCHEMAS['review'])
        self.stages['review']['reviews'][0]['unknown_field']=True
        with self.assertRaises(ValueError):b.validate(self.stages['review'],b.SCHEMAS['review'])

    def test_snapshot_schema_matches_module_schema(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        for folder,stage,key in [('m3_tasks','tasks','tasks'),('m5_quality','review','reviews')]:
            s=b.read(root/'builder_modules'/folder/'schema.json')
            self.assertEqual(s['properties'][key]['items']['properties']['geometry_audit'],b.GEOMETRY_AUDIT)

"""Reusable task families. Each family id maps to one build function and one
ability; the engine never dispatches by question ID."""
from . import local_geometry, force_path, extinction, conformer_design, extent_choice

FAMILIES = {
    'named_bond_angle': dict(build=local_geometry.build_bond_angle, ability='perception',
                             output='choice+numeric', version=local_geometry.VERSION, module='task_families/local_geometry.py'),
    'backbone_torsion': dict(build=local_geometry.build_backbone_torsion, ability='perception',
                             output='choice+numeric', version=local_geometry.VERSION, module='task_families/local_geometry.py'),
    'extent_choice_v2': dict(build=extent_choice.build, ability='perception',
                             output='choice+numeric', version=extent_choice.VERSION, module='task_families/extent_choice.py'),
    'force_path_derivative': dict(build=force_path.build, ability='inference',
                                  output='choice+numeric', version=force_path.VERSION, module='task_families/force_path.py'),
    'kinematic_extinction': dict(build=extinction.build, ability='inference',
                                 output='choice', version=extinction.VERSION, module='task_families/extinction.py'),
    'conformer_target_selection': dict(build=conformer_design.build, ability='design',
                                       output='choice', version=conformer_design.VERSION, module='task_families/conformer_design.py'),
}

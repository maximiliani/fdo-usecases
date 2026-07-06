#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Simple test script to verify Creep FDO design components."""

import asyncio
import json
from pathlib import Path

from fdo_usecases.designs.creep.constants import CREEP_EXPERIMENT_PROFILE, MATERIAL_PROFILE
from fdo_usecases.designs.creep.models.exchange import CreepExperimentData, MaterialData
from fdo_usecases.designs.creep.orchestrator import CreepFDOOrchestrator


async def test_models():
    """Test exchange models."""
    print("Testing exchange models...")
    
    experiment_data = CreepExperimentData(
        test_id="Vh5205_C-78",
        applicable_standard="DIN EN ISO 204:2019-4",
        specified_temperature=980.0,
        initial_stress=230.0,
        test_duration="P3DT6H42M",
        single_crystal_orientation=6.9,
        test_job_details={
            "dateOfTestStart": "2023-02-08T09:06:15",
            "dateOfTestEnd": "2023-02-11T15:48:15",
            "project": "Vh 5205",
            "testID": "Vh5205_C-78",
        },
        has_data=["md5:abc123"],
        has_metadata=["md5:def456"],
        uses_material="CMSX-6_md5:chem123",
        percentage_creep_extension=0.015,
        creators=["https://orcid.org/0000-0000-0000-0000"],
        keywords=["CMSX-6", "creep test"],
    )
    
    material_data = MaterialData(
        material_id="CMSX-6",
        pid_composition="CMSX-6_md5:chem123",
        has_chemical_composition="md5:chem123",
        has_heat_treatment="md5:heat456",
        descriptions=[
            "As-manufactured: Vacuum Induction Refined",
            "As-tested: Single Crystal Investment Cast",
        ],
        preview_images=["https://example.com/image.jpg"],
        creators=["https://orcid.org/0000-0000-0000-0000"],
        keywords=["CMSX-6", "Ni-based superalloy"],
    )
    
    print(f"✓ Created CreepExperimentData: {experiment_data.test_id}")
    print(f"✓ Created MaterialData: {material_data.material_id}")
    return True


async def test_orchestrator_with_mock_graph():
    """Test orchestrator with mock graph."""
    print("\nTesting orchestrator with mock graph...")
    
    # Create minimal mock graph
    mock_graph = {}
    
    orchestrator = CreepFDOOrchestrator(mock_graph)
    
    # Create test data
    material_data = MaterialData(
        material_id="CMSX-6",
        pid_composition="CMSX-6_md5:chem123",
        has_chemical_composition="md5:chem123",
        has_heat_treatment="md5:heat456",
        descriptions=["Test description"],
        creators=["https://orcid.org/0000-0000-0000-0000"],
    )
    
    experiment_data = CreepExperimentData(
        test_id="Vh5205_C-78",
        applicable_standard="DIN EN ISO 204:2019-4",
        specified_temperature=980.0,
        initial_stress=230.0,
        test_duration="P3DT6H42M",
        single_crystal_orientation=6.9,
        test_job_details={
            "dateOfTestStart": "2023-02-08T09:06:15",
            "dateOfTestEnd": "2023-02-11T15:48:15",
            "project": "Vh 5205",
            "testID": "Vh5205_C-78",
        },
        has_data=["md5:abc123"],
        has_metadata=["md5:def456"],
        uses_material="CMSX-6_md5:chem123",
    )
    
    # Create FDOs
    await orchestrator.material_design.create_fdo(material_data)
    await orchestrator.experiment_design.create_fdo(experiment_data)
    
    # Verify graph
    assert len(orchestrator._record_graph) == 2, f"Expected 2 records, got {len(orchestrator._record_graph)}"
    assert "CMSX-6_md5:chem123" in orchestrator._record_graph
    assert "Vh5205_C-78" in orchestrator._record_graph
    
    # Check profiles
    material_record = orchestrator._record_graph["CMSX-6_md5:chem123"]
    experiment_record = orchestrator._record_graph["Vh5205_C-78"]
    
    print(f"✓ Created Material FDO: CMSX-6_md5:chem123")
    print(f"✓ Created Experiment FDO: Vh5205_C-78")
    print(f"✓ Graph contains {len(orchestrator._record_graph)} records")
    
    # Export to JSON
    output_path = Path(__file__).parent / "test_creep_graph.json"
    graph_dict = {k: v.toSimpleJSON() for k, v in orchestrator._record_graph.items()}
    
    with open(output_path, 'w') as f:
        json.dump(graph_dict, f, indent=2)
    
    print(f"✓ Exported test graph to {output_path}")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Creep FDO Design System - Component Tests")
    print("=" * 60)
    
    try:
        await test_models()
        await test_orchestrator_with_mock_graph()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

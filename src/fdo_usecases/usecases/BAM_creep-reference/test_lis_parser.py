#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Test LIS parser with sample data."""

import asyncio
from datetime import datetime

from lis_parser import LISParser, ParsedTestMetadata


def test_parse_lis_content():
    """Test parsing of LIS content."""
    print("Testing LIS content parsing...")
    
    # Sample LIS content (tab-separated)
    sample_content = """CATEGORIZATION	ENTRY	ENTRY - ADDITIONAL INFORMATION	SYMBOL	UNIT	REQUIREMENT	INFORMATION	INFORMATION COMMON TO ALL (*)
Metadata --> Test info --> Test job details	Date of test start				Mandatory	2023-02-08 09:06:15	
Metadata --> Test info --> Test job details	Date of test end				Mandatory	2023-02-11 15:48:15	
Metadata --> Test info --> Test job details	Project				Optional	Vh 5205	*
Metadata --> Test info --> Test job details	Test ID				Mandatory	Vh5205_C-78	
Metadata --> Test info --> Test parameters	Test standard applied	Was the test performed according to a test standard? 			Mandatory	Yes	*
Metadata --> Test info --> Test parameters	Test standard				Mandatory	DIN EN ISO 204:2019-4	*
Metadata --> Test info --> Test parameters	Specified temperature		T	°C	Mandatory	980	*
Metadata --> Test info --> Test parameters	Initial stress		Ro	MPa	Mandatory	230	
Metadata --> Test info --> Test parameters	Percentage creep extension				Optional	1.5%	
Metadata --> Material history and condition	Material Identifier	E.g., NIMONIC 75, 2.4630, CMSX-6, CMSX-4, ERBO1, …			Mandatory	CMSX-6	*
Metadata --> Material history and condition --> Microstructure	Single crystal orientation 	Link to file, preferably with machine-readable (meta)data. Laue Crystal Verification. Must be documented for each test piece.			Mandatory	6.9	
Metadata --> Material history and condition --> As-manufactured material	Manufacturing process description as-manufactured material	E.g., Cast / Melting, Casting, and Remelting  / Induction melting in air, casting into a circular ingot and then electroslag remelting			Optional	Vacuum Induction Refined	*
Metadata --> Material history and condition --> As-tested material	Manufacturing process description as-tested material	The test piece is manufactured from the as-tested material. Please add a description or a link to Image or technical drawing. The as-tested material is the material to be tested. The as-tested material can be a component.			Mandatory	Single Crystal Investment Cast	*
Metadata --> Test piece	Test piece technical drawing	Link to file, preferably with machine-readable (meta)data			Mandatory	See file "TestPieceCreepTests-TechnicalDrawing-FormA.pdf"	*
Metadata --> Material history and condition --> Chemical composition	Chemical composition - measured	Include precision, if available. Link to file, preferably with machine-readable (meta)data  or add the wt.-% value of for each element		wt.-% / at.-%	Mandatory	See file "Vh5205_Complementary_Ch.-Comp.-measured.LIS"	*
"""
    
    parser = LISParser()
    metadata = parser._parse_lis_content(sample_content, "Vh5205_C-78")
    
    if not metadata:
        print("❌ Failed to parse LIS content")
        return False
    
    # Validate parsed values
    assert metadata.test_id == "Vh5205_C-78", f"Expected test_id Vh5205_C-78, got {metadata.test_id}"
    assert metadata.project == "Vh 5205", f"Expected project 'Vh 5205', got {metadata.project}"
    assert metadata.date_test_start == datetime(2023, 2, 8, 9, 6, 15), f"Invalid start date: {metadata.date_test_start}"
    assert metadata.date_test_end == datetime(2023, 2, 11, 15, 48, 15), f"Invalid end date: {metadata.date_test_end}"
    assert metadata.applicable_standard == "DIN EN ISO 204:2019-4", f"Invalid standard: {metadata.applicable_standard}"
    assert metadata.specified_temperature == 980.0, f"Invalid temperature: {metadata.specified_temperature}"
    assert metadata.initial_stress == 230.0, f"Invalid stress: {metadata.initial_stress}"
    assert abs(metadata.percentage_creep_extension - 0.015) < 0.001, f"Invalid creep extension: {metadata.percentage_creep_extension}"
    assert metadata.material_id == "CMSX-6", f"Invalid material ID: {metadata.material_id}"
    assert metadata.single_crystal_orientation == 6.9, f"Invalid orientation: {metadata.single_crystal_orientation}"
    
    # These may be None if categorization doesn't match exactly
    print(f"  manufacturing_as_manufactured: {metadata.manufacturing_as_manufactured}")
    print(f"  manufacturing_as_tested: {metadata.manufacturing_as_tested}")
    
    # Check file references
    assert len(metadata.file_references) == 2, f"Expected 2 file references, got {len(metadata.file_references)}"
    assert "TestPieceCreepTests-TechnicalDrawing-FormA.pdf" in metadata.file_references
    assert "Vh5205_Complementary_Ch.-Comp.-measured.LIS" in metadata.file_references
    
    print(f"✓ Parsed test ID: {metadata.test_id}")
    print(f"✓ Parsed dates: {metadata.date_test_start} to {metadata.date_test_end}")
    print(f"✓ Parsed standard: {metadata.applicable_standard}")
    print(f"✓ Parsed temperature: {metadata.specified_temperature}°C")
    print(f"✓ Parsed stress: {metadata.initial_stress} MPa")
    print(f"✓ Parsed creep extension: {metadata.percentage_creep_extension} ({metadata.percentage_creep_extension * 100:.1f}%)")
    print(f"✓ Parsed material: {metadata.material_id}")
    print(f"✓ Parsed orientation: {metadata.single_crystal_orientation}°")
    print(f"✓ Found {len(metadata.file_references)} file references")
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("LIS Parser Tests")
    print("=" * 60)
    
    try:
        success = test_parse_lis_content()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ All LIS parser tests passed!")
            print("=" * 60)
            return 0
        else:
            print("\n❌ Tests failed")
            return 1
            
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
